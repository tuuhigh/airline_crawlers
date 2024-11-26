import asyncio
import datetime
import json
import logging
import random
import re
import os
import traceback
import shutil
import uuid
import time
from typing import Dict, Iterator, List, Tuple, TypedDict, Optional
from collections import namedtuple
from undetected_playwright.sync_api import sync_playwright
from undetected_playwright.async_api import async_playwright
from zenrows import ZenRowsClient

import requests
from aiohttp import ClientSession
from curl_cffi import requests as crequests
from bs4 import BeautifulSoup
from isodate import duration_isoformat

from src import constants as c
from src.base import RequestsBasedAirlineCrawler, MultiLoginAirlineCrawler
from src.dl.constants import AirlineCabinClassCodeMapping, CabinClassCodeMappingForHybrid, AirCraftIATACode
from src.exceptions import ZenRowFailed, CrawlerException
from src.schema import CashFee, Flight, FlightSegment
from src.db import get_target_headers, update_target_headers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_RTC_PATH = os.path.join(BASE_DIR, "webrtc_addon")
logger = logging.getLogger(__name__)

GeoLocationConfiguration = namedtuple("GeoLocationConfiguration", ("proxy_host", "proxy_port", "home_page_url"))
GeoLocationConfigurations = [
    GeoLocationConfiguration(
        proxy_host="us.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com"
    ),
    GeoLocationConfiguration(
        proxy_host="ca.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/ca/en"
    ),
    GeoLocationConfiguration(
        proxy_host="gb.smartproxy.com", proxy_port="30001", home_page_url="https://www.delta.com/gb/en"
    ),
    GeoLocationConfiguration(
        proxy_host="nl.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com/eu/en"
    ),
    GeoLocationConfiguration(
        proxy_host="de.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/eu/en"
    ),
    GeoLocationConfiguration(
        proxy_host="fr.smartproxy.com", proxy_port="40001", home_page_url="https://www.delta.com/fr/en"
    ),
    GeoLocationConfiguration(
        proxy_host="mx.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/mx/en"
    ),
    GeoLocationConfiguration(
        proxy_host="br.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com/br/en"
    ),
]

# block pages by resource type. e.g. image, stylesheet
BLOCK_RESOURCE_TYPES = [
    'beacon',
    'csp_report',
    'font',
    'image',
    'imageset',
    'media',
    'object',
    'texttrack',
    #  we can even block stylsheets and scripts though it's not recommended:
    # 'stylesheet',
    # 'script',
    # 'xhr',
]


# we can also block popular 3rd party resources like tracking and advertisements.
BLOCK_RESOURCE_NAMES = [
    'adzerk',
    'analytics',
    'cdn.api.twitter',
    'doubleclick',
    'exelator',
    'facebook',
    'fontawesome',
    'google',
    'google-analytics',
    'googletagmanager',
]


FETCHED_COOKIES = []
class CookieFetcher(MultiLoginAirlineCrawler):
    TARGET = 'delta'
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.smart_proxy_host, self.smart_proxy_port, self.home_page_url = random.choice(GeoLocationConfigurations)
        
    def get_proxy(self):
        proxy = {
            "ip": self.smart_proxy_host,
            "port": self.smart_proxy_port,
            "user": "spyc5m5gbs",
            "pwd": "puFNdLvkx6Wcn6h6p8",
        }
        return proxy
    
    def get_user_dir(self):
        utc_now = datetime.datetime.utcnow().isoformat().replace(":", "_")
        self._user_data_dir = os.path.join(BASE_DIR, f"_user_data_dir_{utc_now}")

    def remove_user_dir(self):
        if self._user_data_dir:
            logger.info(f"Removing _user_data_dir {self._user_data_dir}...")
            shutil.rmtree(self._user_data_dir, ignore_errors=True)
      

    @staticmethod
    def block_resouces(route):
        """intercept all requests and abort blocked ones"""
        if route.request.resource_type in BLOCK_RESOURCE_TYPES:
            # print(f'blocking background resource {route.request} blocked type "{route.request.resource_type}"')
            return route.abort()
        if any(key in route.request.url for key in BLOCK_RESOURCE_NAMES):
            # print(f"blocking background resource {route.request} blocked name {route.request.url}")
            return route.abort()
        return route.continue_()
    
    async def request_handler(self, request):
        headers = await request.all_headers()
        self.headers = headers
        # print(">>>>>>>>>>.. headers:", headers)
    
    async def fetch_cookie_multilogin(self, last_cookie=""):
        driver = self.setup_driver()
        url = "https://www.delta.com/flightsearch/book-a-flight"
        # url = "https://www.delta.com/flightsearch/search-results?cacheKeySuffix=92f0cca8-b1a7-4df3-9332-ffe02079b155"
        driver.get(url)
        time.sleep(10)
        cookies = []
        for cookie in driver.get_cookies():
            cookie_text = f'{cookie["name"]}={cookie["value"]}'
            cookies.append(cookie_text)
        cookies_text = '; '.join(cookies)
        print(f">>>>>>>>>>>>>. cookies_text:", cookies_text)
        driver.quit()
        return cookies_text

    async def fetch_headers_from_db(self):
        headers_rec = get_target_headers(self.TARGET)
        print(f">>>>>>>>>>>>> fetch_cookie_from_db {headers_rec}")
        return headers_rec
    
    def get_private_proxy(self):
        response = requests.get(c.PROXY_SERVICE_URL)
        if response.status_code == 200:
            res = response.json()
            proxy = res.get('proxy')
            return proxy
        return {}

    def setup_proxy_str(self):
        # proxy_user = "spyc5m5gbs"
        # proxy_pass = "puFNdLvkx6Wcn6h6p8"
        # proxy_host = "us.smartproxy.com"
        # proxy_port = "10001"
        
        proxy = self.get_private_proxy()
        proxy_host = proxy.get('ip')  # rotating proxy or host
        proxy_port = int(proxy.get('port'))  # port
        proxy_user = proxy.get('user')  # username
        proxy_pass = proxy.get('pwd')  # password
        
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        return proxy_attr


    async def fetch_cookie_playright(self, last_cookie=""):
        try:
        
            print(1)
            proxy_vals = self.get_private_proxy()
            options = {}
            if proxy_vals:
                print(2)
                PROXY_HOST = proxy_vals.get('ip')
                PROXY_PORT = proxy_vals.get('port')
                PROXY_USER = proxy_vals.get('user')
                PROXY_PASS = proxy_vals.get('pwd')
                options = {
                    "proxy": {"server": f"{PROXY_HOST}:{PROXY_PORT}", "username": PROXY_USER, "password": PROXY_PASS},
                }
            print(3)
            async with async_playwright() as playwright:
                print(4)
                self.get_user_dir()
                logger.info(f">>>>>>>> options: {options}")
                # browser = random.choice(['firefox', 'msedge'])
                args = [
                    "--disable-blink-features=AutomationControlled",
                    f"--disable-extensions-except={WEB_RTC_PATH}",
                    f"--load-extension={WEB_RTC_PATH}",
                ]
                browser = await playwright.chromium.launch_persistent_context(
                    args=args,
                    user_data_dir=self._user_data_dir,
                    headless=False,
                    timeout=200 * 1000,
                    slow_mo=100,  # slow down step as human behavior
                    **options
                )
                print(5)
                page = await browser.new_page()
                # page.route("**", lambda route, request: self.intercept_request(route, request))
                # await page.route("**", self.block_resouces)

                url = "https://www.delta.com/flightsearch/book-a-flight"
                # url = "https://www.delta.com/flightsearch/search-results"
                page.on("request", self.request_handler)
                await page.goto(url, timeout=3 * 60000)
                cookie_array = await browser.cookies()
                cookies = []
                for cookie in cookie_array:
                    if cookie.get('name') and cookie.get('value'):
                        cookie_text = f'{cookie["name"]}={cookie["value"]}'
                        cookies.append(cookie_text)
                cookies_text = '; '.join(cookies)
                # logger.info(cookie_array)
                logger.info(cookies_text)
                await browser.close()
                self.remove_user_dir()
                # FETCHED_COOKIES.append(cookie_text)
                # print(">>>>>>>>. return cookie:", cookie_text)
                return cookies_text
        except Exception as e:
            print(f">>>>>>>>>..error: ", e)
            traceback.print_exc()
            

class DeltaAirlineRequestsCrawler(RequestsBasedAirlineCrawler):
    TARGET = 'delta'
    AIRLINE = c.Airline.DeltaAirline

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smart_proxy_host, self.smart_proxy_port, self.home_page_url = random.choice(GeoLocationConfigurations)
        self.fare_codes: Dict[str, str] = {}
        self.cookie = ""
        self.headers = {}
        self.all_headers = []
        self.proxy_attr = self.setup_proxy_str()
    
    def get_private_proxy(self):
        response = requests.get(c.PROXY_SERVICE_URL)
        if response.status_code == 200:
            res = response.json()
            proxy = res.get('proxy')
            return proxy
        return {}

        
    def get_proxy(self):
        proxy = {
            "ip": self.smart_proxy_host,
            "port": self.smart_proxy_port,
            "user": "spyc5m5gbs",
            "pwd": "puFNdLvkx6Wcn6h6p8",
        }
        return proxy
    
    def setup_proxy_str(self):
        # proxy_user = "spyc5m5gbs"
        # proxy_pass = "puFNdLvkx6Wcn6h6p8"
        # proxy_host = "us.smartproxy.com"
        # proxy_port = "10001"
        
        proxy = self.get_proxy()
        proxy_host = proxy.get('ip')  # rotating proxy or host
        proxy_port = int(proxy.get('port'))  # port
        proxy_user = proxy.get('user')  # username
        proxy_pass = proxy.get('pwd')  # password
        
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        return proxy_attr

    def convert_to_seconds(self, days=0, hours=0, minutes=0):
        return (3600 * 24 * days) + (3600 * hours) + (60 * minutes)

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["trips"][0]["flightSegment"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                if segment_element.get("layover", {}):
                    connection_time_hours = segment_element.get("layover", {}).get("layoverDuration", {}).get("hourCnt", 0)
                    connection_time_minutes = segment_element.get("layover", {}).get("layoverDuration", {}).get("minuteCnt", 0)
                    connection_time = self.convert_to_seconds(0, connection_time_hours, connection_time_minutes)
                else:
                    connection_time = 0

                segment_origin = segment_element["originAirportCode"]
                segment_destination = segment_element["destinationAirportCode"]
                segment_departure_time = segment_element["scheduledDepartureLocalTs"]
                segment_arrival_time = segment_element["scheduledArrivalLocalTs"]
                aircraft_id = segment_element["aircraftTypeCode"]
                segment_aircraft = AirCraftIATACode.get(aircraft_id, "")
                segment_carrier = segment_element.get('marketingCarrier', {}).get('carrierCode', None)
                if not segment_carrier:
                    segment_carrier = segment_element.get('operatingCarrier', {}).get('carrierCode', None)
                segment_flight_number = segment_element.get('marketingCarrier', {}).get('carrierNum', None)
                if not segment_flight_number:
                    segment_flight_number = segment_element.get('operatingCarrier', {}).get('carrierNum', None)

                flight_leg = segment_element["flightLeg"][0]
                segment_duration_hours = flight_leg["duration"]["hourCnt"]
                segment_duration_minutes = flight_leg["duration"]["minuteCnt"]
                segment_duration = self.convert_to_seconds(0, segment_duration_hours, segment_duration_minutes)

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_time and segment_departure_time.split("T")[0],
                        departure_time=segment_departure_time
                        and segment_departure_time.split("T")[1].split(".")[0],
                        departure_timezone=segment_departure_time and segment_departure_time.split(".000")[-1],
                        arrival_date=segment_arrival_time and segment_arrival_time.split("T")[0],
                        arrival_time=segment_arrival_time and segment_arrival_time.split("T")[1].split(".")[0],
                        arrival_timezone=segment_arrival_time and segment_arrival_time.split(".000")[-1],
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=duration_isoformat(datetime.timedelta(seconds=segment_duration)),
                        layover_time=duration_isoformat(datetime.timedelta(seconds=connection_time))
                        if connection_time
                        else None,
                    )
                )
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def extract_sub_classes_points(
        self, flight_data, currency, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Extracting Sub Sub Classes points...")
        cabin_class_codes = CabinClassCodeMappingForHybrid[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        for offer in flight_data["offers"]:
            fare_code = offer["additionalOfferProperties"]["dominantSegmentBrandId"]
            if fare_code not in cabin_class_codes:
                continue

            try:
                fare_name = AirlineCabinClassCodeMapping[fare_code]
                if not offer["offerId"]:
                    points = -1
                    amount = 0
                else:
                    points = offer["offerItems"][0]["retailItems"][0]["retailItemMetaData"]["fareInformation"][0]["farePrice"][0]["totalFarePrice"]["milesEquivalentPrice"]["mileCnt"]
                    amount = offer["offerItems"][0]["retailItems"][0]["retailItemMetaData"]["fareInformation"][0]["farePrice"][0]["totalFarePrice"]["currencyEquivalentPrice"]["roundedCurrencyAmt"]

                points_by_fare_names[fare_name] = {
                    "points": points,
                    "cash_fee": CashFee(
                        amount=amount,
                        currency=currency,
                    ),
                }
            except Exception as e:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return points_by_fare_names

    def extract_sub_classes_cash(
        self, flight_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Extracting Sub Sub Classes Cash...")
        cabin_class_codes = CabinClassCodeMappingForHybrid[cabin_class]
        cash_by_fare_names: Dict[str, dict] = {}

        for offer in flight_data["offers"]:
            fare_code = offer["additionalOfferProperties"]["dominantSegmentBrandId"]
            if fare_code not in cabin_class_codes:
                continue

            try:
                fare_name = AirlineCabinClassCodeMapping[fare_code]
                if not offer["offerId"]:
                    amount = -1
                else:
                    amount = offer["offerItems"][0]["retailItems"][0]["retailItemMetaData"]["fareInformation"][0]["farePrice"][0]["totalFarePrice"]["currencyEquivalentPrice"]["roundedCurrencyAmt"]

                cash_by_fare_names[fare_name] = amount
            except Exception as e:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return cash_by_fare_names

    def parse_points_flights(
        self, flights_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flights = list()
        flight_search_results = flights_data.get("data", {}).get("gqlSearchOffers", {}) or {}
        flight_search_results = flight_search_results.get("gqlOffersSets", [])
        currency = flights_data["data"]["gqlSearchOffers"]["offerDataList"]["pricingOptions"][0]["pricingOptionDetail"]["currencyCode"]
        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} Points Flights...")
        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Retrieving the detail of search item => index: {index}...")

            points_by_fare_names = self.extract_sub_classes_points(flight_search_result, currency, cabin_class)
            if not points_by_fare_names:
                continue

            try:
                segments = self.extract_flight_detail(flight_search_result)
            except Exception as e:
                raise e
            total_trip_time = flight_search_result["trips"][0]["totalTripTime"]
            total_trip_time_hours = total_trip_time["hourCnt"]
            total_trip_time_minutes = total_trip_time["minuteCnt"]
            duration = self.convert_to_seconds(0, total_trip_time_hours, total_trip_time_minutes)
            for fare_name, points_and_cash in points_by_fare_names.items():
                if not segments:
                    continue
                flight = Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=str(cabin_class.value),
                    airline_cabin_class=fare_name,
                    fare_brand_name=fare_name,
                    points=points_and_cash["points"],
                    cash_fee=points_and_cash["cash_fee"],
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                )
                flights.append(flight)
        return flights

    def parse_cash_flights(
        self, flights_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flights = list()
        flight_search_results = flights_data.get("data", {}).get("gqlSearchOffers", {}) or {}
        flight_search_results = flight_search_results.get("gqlOffersSets", [])
        currency = flights_data["data"]["gqlSearchOffers"]["offerDataList"]["pricingOptions"][0]["pricingOptionDetail"]["currencyCode"]
        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} Cash Flights...")
        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Retrieving the detail of search item => index: {index}...")

            cash_by_fare_names = self.extract_sub_classes_cash(flight_search_result, cabin_class)
            if not cash_by_fare_names:
                continue

            try:
                segments = self.extract_flight_detail(flight_search_result)
            except Exception as e:
                raise e
            total_trip_time = flight_search_result["trips"][0]["totalTripTime"]
            total_trip_time_hours = total_trip_time["hourCnt"]
            total_trip_time_minutes = total_trip_time["minuteCnt"]
            duration = self.convert_to_seconds(0, total_trip_time_hours, total_trip_time_minutes)
            for fare_name, cash_amount in cash_by_fare_names.items():
                if not segments:
                    continue
                flight = Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=str(cabin_class.value),
                    airline_cabin_class=fare_name,
                    fare_brand_name=fare_name,
                    amount=cash_amount,
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                )
                flights.append(flight)
        return flights

    def match_flights(self, cash_flights: List[Flight], points_flights: List[Flight], cabin_class: c.CabinClass = c.CabinClass.Economy):
        flights = []
        logger.info(f"{self.AIRLINE.value}- {cabin_class.value}: Doing matching for {len(cash_flights)} Cash and {len(points_flights)} Points")
        sorted_points_flights = dict()
        for points_flight in points_flights:
            flight_numbers = [segment.flight_number for segment in points_flight.segments]
            flight_number = '-'.join(flight_numbers)
            flight_key = f'{flight_number}-{points_flight.airline_cabin_class}'
            sorted_points_flights[flight_key] = points_flight

        print(f">>>> {cabin_class.value} sorted_points_flights: {sorted_points_flights}")
        
        sorted_cash_flights = dict()
        for cash_flight in cash_flights:
            flight_numbers = [segment.flight_number for segment in cash_flight.segments]
            flight_number = '-'.join(flight_numbers)
            flight_key = f'{flight_number}-{cash_flight.airline_cabin_class}'
            sorted_cash_flights[flight_key] = cash_flight
        print(f">>>> {cabin_class.value} sorted_cash_flights: {sorted_cash_flights}")
        
        for flight_key, sorted_points_flight in sorted_points_flights.items():
            if flight_key in sorted_cash_flights:
                sorted_points_flight.amount = sorted_cash_flights[flight_key].amount
                del sorted_cash_flights[flight_key]

            flights.append(sorted_points_flight)

        flights = flights + list(sorted_cash_flights.values())

        return flights

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        flights_pricing_data, flights_points_data = asyncio.run(self.get_flights(origin, destination, departure_date, cabin_class, adults))
        pricing_errors = (flights_pricing_data or {}).get('errors', [])
        if pricing_errors:
            msg = f"{self.AIRLINE.value}: Cash Error Message: {pricing_errors}"
            logger.error(msg)
            raise CrawlerException(msg)

        points_errors = (flights_points_data or {}).get('errors', [])
        if points_errors:
            msg = f"{self.AIRLINE.value}: points Error Message: {points_errors}"
            logger.error(msg)
            raise CrawlerException(msg)
        
        if not flights_pricing_data or not flights_points_data:
            raise CrawlerException(f"Not found data for cash: {flights_pricing_data} or points {flights_points_data}")
        all_cabins = []
        if cabin_class == c.CabinClass.All:
            all_cabins = [
                c.CabinClass.Economy, 
                c.CabinClass.PremiumEconomy, 
                c.CabinClass.Business,
                c.CabinClass.First
            ]
        else:
            all_cabins = [cabin_class]
        print(f"all for cabin class: {all_cabins}")
        for cabin_item in all_cabins:
            print(f"doing for cabin class: {cabin_item}")
            cash_flights = self.parse_cash_flights(flights_pricing_data, cabin_item) if (flights_pricing_data and not pricing_errors) else {}
            points_flights = self.parse_points_flights(flights_points_data, cabin_item) if (flights_points_data and not points_errors) else {}
            flights = self.match_flights(cash_flights, points_flights)
            for flight in flights:
                yield flight

    async def get_flights(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:
        async with ClientSession() as session:
            cookie_fetcher = CookieFetcher()
            self.all_headers = await cookie_fetcher.fetch_headers_from_db()
            tasks = [
                self.get_flights_pricing(session, origin, destination, departure_date, cabin_class, adults),
                self.get_flights_points(session, origin, destination, departure_date, cabin_class, adults),
            ]
            flights_pricing, flights_points = await asyncio.gather(*tasks, return_exceptions=True)
            if isinstance(flights_pricing, Exception) and isinstance(flights_points, Exception):
                raise ZenRowFailed(airline=self.AIRLINE, reason=f"Pricing & Points requests all failed: {flights_pricing} and points: {flights_points}")
            elif isinstance(flights_pricing, dict) and isinstance(flights_points, dict):
                return flights_pricing, flights_points
            else:
                return {}, {}
            
    async def get_flights_points(
        self,
        session: ClientSession,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:

        json_data = {
            'variables': {
                'offerSearchCriteria': {
                    'productGroups': [
                        {
                            'productCategoryCode': 'FLIGHTS',
                        },
                    ],
                    'offersCriteria': {
                        'showContentLinks': False,
                        'resultsPageNum': 1,
                        'resultsPerRequestNum': 50,
                        'preferences': {
                            'refundableOnly': False,
                            'showGlobalRegionalUpgradeCertificate': True,
                            'nonStopOnly': False,
                        },
                        'pricingCriteria': {
                            'priceableIn': [
                                'MILES',
                            ],
                        },
                        'flightRequestCriteria': {
                            'currentTripIndexId': '0',
                            'sortableOptionId': None,
                            'selectedOfferId': '',
                            'searchOriginDestination': [
                                {
                                    'departureLocalTs': departure_date.strftime('%Y-%m-%d') + 'T00:00:00',
                                    'destinations': [
                                        {
                                            'airportCode': destination,
                                        },
                                    ],
                                    'origins': [
                                        {
                                            'airportCode': origin,
                                        },
                                    ],
                                },
                            ],
                            'sortByBrandId': 'BE',
                        },
                    },
                    'customers': [
                        {
                            'passengerTypeCode': 'ADT',
                            'passengerId': f'{adults}',
                        },
                    ],
                },
            },
            'query': 'query ($offerSearchCriteria: OfferSearchCriteriaInput!) {\n  gqlSearchOffers(offerSearchCriteria: $offerSearchCriteria) {\n    offerResponseId\n    gqlOffersSets {\n      trips {\n        tripId\n        scheduledDepartureLocalTs\n        scheduledArrivalLocalTs\n        originAirportCode\n        destinationAirportCode\n        stopCnt\n        flightSegment {\n          aircraftTypeCode\n          dayChange\n          destinationAirportCode\n          flightLeg {\n            legId\n            dayChange\n            destinationAirportCode\n            feeRestricted\n            scheduledArrivalLocalTs\n            scheduledDepartureLocalTs\n            layover {\n              destinationAirportCode\n              layoverAirportCode\n              layoverDuration {\n                hourCnt\n                minuteCnt\n              }\n              departureFlightNum\n              equipmentChange\n              originAirportCode\n              scheduledArrivalLocalTs\n              scheduledDepartureLocalTs\n            }\n            operatedByOwnerCarrier\n            redEye\n            operatingCarrier {\n              carrierCode\n              carrierName\n            }\n            marketingCarrier {\n              carrierCode\n              carrierName\n            }\n            earnLoyaltyMiles\n            loyaltyMemberBenefits\n            dominantLeg\n            duration {\n              dayCnt\n              hourCnt\n              minuteCnt\n            }\n            originAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            destinationAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            originAirportCode\n            aircraft {\n              fleetTypeCode\n              subFleetTypeCode\n              newSubFleetType\n            }\n            carrierCode\n            distance {\n              unitOfMeasure\n              unitOfMeasureCnt\n            }\n          }\n          layover {\n            destinationAirportCode\n            layoverAirportCode\n            layoverDuration {\n              hourCnt\n              minuteCnt\n            }\n            departureFlightNum\n            equipmentChange\n            originAirportCode\n            scheduledArrivalLocalTs\n            scheduledDepartureLocalTs\n          }\n          marketingCarrier {\n            carrierCode\n            carrierNum\n          }\n          operatingCarrier {\n            carrierCode\n            carrierNum\n            carrierName\n          }\n          pendingGovtApproval\n          destinationCityCode\n          flightSegmentNum\n          originAirportCode\n          originCityCode\n          scheduledArrivalLocalTs\n          scheduledDepartureLocalTs\n          aircraft {\n            fleetTypeCode\n            subFleetTypeCode\n            newSubFleetType\n          }\n        }\n        totalTripTime {\n          dayCnt\n          hourCnt\n          minuteCnt\n        }\n        summarizedProductId\n      }\n      additionalOfferSetProperties {\n        globalUpgradeCertificateTripStatus {\n          brandId\n          upgradeAvailableStatusProductId\n        }\n        regionalUpgradeCertificateTripStatus {\n          brandId\n          upgradeAvailableStatusProductId\n        }\n        offerSetId\n        seatReferenceId\n        discountInfo {\n          discountPct\n          discountTypeCode\n          nonDiscountedOffersAvailable\n        }\n        promotionsInfo {\n          promotionalCode\n          promotionalPct\n        }\n        discountInEligibilityList {\n          code\n          reason\n        }\n      }\n      offerSetBadges {\n        brandId\n      }\n      offers {\n        offerId\n        additionalOfferProperties {\n          offered\n          fareType\n          dominantSegmentBrandId\n          priorityNum\n          soldOut\n          unavailableForSale\n          refundable\n          offerBadges {\n            brandId\n          }\n          payWithMilesEligible\n          discountAvailable\n          travelPolicyStatus\n        }\n        soldOut\n        offerItems {\n          retailItems {\n            retailItemMetaData {\n              fareInformation {\n                brandByFlightLegs {\n                  brandId\n                  cosCode\n                  tripId\n                  product {\n                    brandId\n                    typeCode\n                  }\n                  globalUpgradeCertificateLegStatus {\n                    upgradeAvailableStatusProductId\n                  }\n                  regionalUpgradeCertificateLegStatus {\n                    upgradeAvailableStatusProductId\n                  }\n                  flightSegmentNum\n                  flightLegNum\n                }\n                discountInEligibilityList {\n                  code\n                  reason\n                }\n                availableSeatCnt\n                farePrice {\n                  discountsApplied {\n                    pct\n                    code\n                    description\n                    reason\n                    amount {\n                      currencyEquivalentPrice {\n                        currencyAmt\n                      }\n                      milesEquivalentPrice {\n                        mileCnt\n                        discountMileCnt\n                      }\n                    }\n                  }\n                  totalFarePrice {\n                    currencyEquivalentPrice {\n                      roundedCurrencyAmt\n                      formattedCurrencyAmt\n                    }\n                    milesEquivalentPrice {\n                      mileCnt\n                      cashPlusMilesCnt\n                      cashPlusMiles\n                    }\n                  }\n                  originalTotalPrice {\n                    currencyEquivalentPrice {\n                      roundedCurrencyAmt\n                      formattedCurrencyAmt\n                    }\n                    milesEquivalentPrice {\n                      mileCnt\n                      cashPlusMilesCnt\n                      cashPlusMiles\n                    }\n                  }\n                  promotionalPrices {\n                    price {\n                      currencyEquivalentPrice {\n                        roundedCurrencyAmt\n                        formattedCurrencyAmt\n                      }\n                      milesEquivalentPrice {\n                        mileCnt\n                        cashPlusMilesCnt\n                        cashPlusMiles\n                      }\n                    }\n                  }\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n    offerDataList {\n      responseProperties {\n        discountInfo {\n          discountPct\n          discountTypeCode\n          nonDiscountedOffersAvailable\n        }\n        promotionsInfo {\n          promotionalCode\n          promotionalPct\n        }\n        discountInEligibilityList {\n          code\n          reason\n        }\n        resultsPerRequestNum\n        pageResultCnt\n        resultsPageNum\n        sortOptionsList {\n          sortableOptionDesc\n          sortableOptionId\n        }\n        tripTypeText\n      }\n      offerPreferences {\n        stopCnt\n        destinationAirportCode\n        connectionTimeRange {\n          maximumNum\n          minimumNum\n        }\n        originAirportCode\n        flightDurationRange {\n          maximumNum\n          minimumNum\n        }\n        layoverAirportCode\n        totalMilesRange {\n          maximumNum\n          minimumNum\n        }\n        totalPriceRange {\n          maximumNum\n          minimumNum\n        }\n      }\n      retailItemDefinitionList {\n        brandType\n        retailItemBrandId\n        refundable\n        retailItemPriorityText\n      }\n      pricingOptions {\n        pricingOptionDetail {\n          currencyCode\n        }\n      }\n    }\n    gqlSelectedOfferSets {\n      trips {\n        tripId\n        scheduledDepartureLocalTs\n        scheduledArrivalLocalTs\n        originAirportCode\n        destinationAirportCode\n        stopCnt\n        flightSegment {\n          destinationAirportCode\n          marketingCarrier {\n            carrierCode\n            carrierNum\n          }\n          operatingCarrier {\n            carrierCode\n            carrierNum\n          }\n          flightSegmentNum\n          originAirportCode\n          scheduledArrivalLocalTs\n          scheduledDepartureLocalTs\n          aircraft {\n            fleetTypeCode\n            subFleetTypeCode\n            newSubFleetType\n          }\n          flightLeg {\n            destinationAirportCode\n            feeRestricted\n            layover {\n              destinationAirportCode\n              layoverAirportCode\n              layoverDuration {\n                hourCnt\n                minuteCnt\n              }\n              departureFlightNum\n              equipmentChange\n              originAirportCode\n              scheduledArrivalLocalTs\n              scheduledDepartureLocalTs\n            }\n            operatedByOwnerCarrier\n            redEye\n            operatingCarrier {\n              carrierCode\n              carrierName\n            }\n            marketingCarrier {\n              carrierCode\n              carrierName\n            }\n            earnLoyaltyMiles\n            loyaltyMemberBenefits\n            dominantLeg\n            duration {\n              dayCnt\n              hourCnt\n              minuteCnt\n            }\n            originAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            destinationAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            originAirportCode\n            aircraft {\n              fleetTypeCode\n              subFleetTypeCode\n              newSubFleetType\n            }\n            carrierCode\n            distance {\n              unitOfMeasure\n              unitOfMeasureCnt\n            }\n            scheduledArrivalLocalTs\n            scheduledDepartureLocalTs\n            dayChange\n          }\n        }\n        totalTripTime {\n          dayCnt\n          hourCnt\n          minuteCnt\n        }\n      }\n      offers {\n        additionalOfferProperties {\n          dominantSegmentBrandId\n          fareType\n        }\n        soldOut\n        offerItems {\n          retailItems {\n            retailItemMetaData {\n              fareInformation {\n                brandByFlightLegs {\n                  tripId\n                  brandId\n                  cosCode\n                }\n              }\n            }\n          }\n        }\n      }\n      additionalOfferSetProperties {\n        seatReferenceId\n      }\n    }\n    contentLinks {\n      type\n      variables {\n        brandProductMapping\n      }\n    }\n  }\n}',
        }
        random.shuffle(self.all_headers)
        retry_count = len(self.all_headers)
        last_cookie = ''
        for i, headers_rec in enumerate(self.all_headers):
            self.setup_proxy_str()
            headers = headers_rec.get("headers", {})
            headers = self.compute_headers_trnx(headers)
            # print(f">>>>>>>>>>>> points headers: {headers}")
            # print(f">>>>>>>>self.proxy_attr: {self.proxy_attr}")
            
            client = ZenRowsClient(c.ZENROWS_API_KEY)
            params = {"premium_proxy":"true"}
            response = crequests.post(
                'https://offer-api-prd.delta.com/prd/rm-offer-gql',
                impersonate="chrome124",
                proxies=self.proxy_attr,
                # params=params,
                headers=headers, json=json_data)

            logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Retrieving Points API Data => {i+1}/{retry_count} => Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                if response.status_code == 444:
                    logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: result: {response.text}")
                headers_id = headers_rec.get("_id")
                update_target_headers(headers_id, {"active": False}, self.TARGET)

        return CrawlerException("No active headers to run")

    async def get_flights_pricing(
        self,
        session: ClientSession,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:

        json_data = {
            'variables': {
                'offerSearchCriteria': {
                    'productGroups': [
                        {
                            'productCategoryCode': 'FLIGHTS',
                        },
                    ],
                    'offersCriteria': {
                        'showContentLinks': False,
                        'resultsPageNum': 1,
                        'resultsPerRequestNum': 50,
                        'preferences': {
                            'refundableOnly': False,
                            'showGlobalRegionalUpgradeCertificate': True,
                            'nonStopOnly': False,
                        },
                        'pricingCriteria': {
                            'priceableIn': [
                                'CURRENCY',
                            ],
                        },
                        'flightRequestCriteria': {
                            'currentTripIndexId': '0',
                            'sortableOptionId': None,
                            'selectedOfferId': '',
                            'searchOriginDestination': [
                                {
                                    'departureLocalTs': departure_date.strftime('%Y-%m-%d') + 'T00:00:00',
                                    'destinations': [
                                        {
                                            'airportCode': destination,
                                        },
                                    ],
                                    'origins': [
                                        {
                                            'airportCode': origin,
                                        },
                                    ],
                                },
                            ],
                            'sortByBrandId': 'BE',
                        },
                    },
                    'customers': [
                        {
                            'passengerTypeCode': 'ADT',
                            'passengerId': f'{adults}',
                        },
                    ],
                },
            },
            'query': 'query ($offerSearchCriteria: OfferSearchCriteriaInput!) {\n  gqlSearchOffers(offerSearchCriteria: $offerSearchCriteria) {\n    offerResponseId\n    gqlOffersSets {\n      trips {\n        tripId\n        scheduledDepartureLocalTs\n        scheduledArrivalLocalTs\n        originAirportCode\n        destinationAirportCode\n        stopCnt\n        flightSegment {\n          aircraftTypeCode\n          dayChange\n          destinationAirportCode\n          flightLeg {\n            legId\n            dayChange\n            destinationAirportCode\n            feeRestricted\n            scheduledArrivalLocalTs\n            scheduledDepartureLocalTs\n            layover {\n              destinationAirportCode\n              layoverAirportCode\n              layoverDuration {\n                hourCnt\n                minuteCnt\n              }\n              departureFlightNum\n              equipmentChange\n              originAirportCode\n              scheduledArrivalLocalTs\n              scheduledDepartureLocalTs\n            }\n            operatedByOwnerCarrier\n            redEye\n            operatingCarrier {\n              carrierCode\n              carrierName\n            }\n            marketingCarrier {\n              carrierCode\n              carrierName\n            }\n            earnLoyaltyMiles\n            loyaltyMemberBenefits\n            dominantLeg\n            duration {\n              dayCnt\n              hourCnt\n              minuteCnt\n            }\n            originAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            destinationAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            originAirportCode\n            aircraft {\n              fleetTypeCode\n              subFleetTypeCode\n              newSubFleetType\n            }\n            carrierCode\n            distance {\n              unitOfMeasure\n              unitOfMeasureCnt\n            }\n          }\n          layover {\n            destinationAirportCode\n            layoverAirportCode\n            layoverDuration {\n              hourCnt\n              minuteCnt\n            }\n            departureFlightNum\n            equipmentChange\n            originAirportCode\n            scheduledArrivalLocalTs\n            scheduledDepartureLocalTs\n          }\n          marketingCarrier {\n            carrierCode\n            carrierNum\n          }\n          operatingCarrier {\n            carrierCode\n            carrierNum\n            carrierName\n          }\n          pendingGovtApproval\n          destinationCityCode\n          flightSegmentNum\n          originAirportCode\n          originCityCode\n          scheduledArrivalLocalTs\n          scheduledDepartureLocalTs\n          aircraft {\n            fleetTypeCode\n            subFleetTypeCode\n            newSubFleetType\n          }\n        }\n        totalTripTime {\n          dayCnt\n          hourCnt\n          minuteCnt\n        }\n        summarizedProductId\n      }\n      additionalOfferSetProperties {\n        globalUpgradeCertificateTripStatus {\n          brandId\n          upgradeAvailableStatusProductId\n        }\n        regionalUpgradeCertificateTripStatus {\n          brandId\n          upgradeAvailableStatusProductId\n        }\n        offerSetId\n        seatReferenceId\n        discountInfo {\n          discountPct\n          discountTypeCode\n          nonDiscountedOffersAvailable\n        }\n        promotionsInfo {\n          promotionalCode\n          promotionalPct\n        }\n        discountInEligibilityList {\n          code\n          reason\n        }\n      }\n      offerSetBadges {\n        brandId\n      }\n      offers {\n        offerId\n        additionalOfferProperties {\n          offered\n          fareType\n          dominantSegmentBrandId\n          priorityNum\n          soldOut\n          unavailableForSale\n          refundable\n          offerBadges {\n            brandId\n          }\n          payWithMilesEligible\n          discountAvailable\n          travelPolicyStatus\n        }\n        soldOut\n        offerItems {\n          retailItems {\n            retailItemMetaData {\n              fareInformation {\n                brandByFlightLegs {\n                  brandId\n                  cosCode\n                  tripId\n                  product {\n                    brandId\n                    typeCode\n                  }\n                  globalUpgradeCertificateLegStatus {\n                    upgradeAvailableStatusProductId\n                  }\n                  regionalUpgradeCertificateLegStatus {\n                    upgradeAvailableStatusProductId\n                  }\n                  flightSegmentNum\n                  flightLegNum\n                }\n                discountInEligibilityList {\n                  code\n                  reason\n                }\n                availableSeatCnt\n                farePrice {\n                  discountsApplied {\n                    pct\n                    code\n                    description\n                    reason\n                    amount {\n                      currencyEquivalentPrice {\n                        currencyAmt\n                      }\n                      milesEquivalentPrice {\n                        mileCnt\n                        discountMileCnt\n                      }\n                    }\n                  }\n                  totalFarePrice {\n                    currencyEquivalentPrice {\n                      roundedCurrencyAmt\n                      formattedCurrencyAmt\n                    }\n                    milesEquivalentPrice {\n                      mileCnt\n                      cashPlusMilesCnt\n                      cashPlusMiles\n                    }\n                  }\n                  originalTotalPrice {\n                    currencyEquivalentPrice {\n                      roundedCurrencyAmt\n                      formattedCurrencyAmt\n                    }\n                    milesEquivalentPrice {\n                      mileCnt\n                      cashPlusMilesCnt\n                      cashPlusMiles\n                    }\n                  }\n                  promotionalPrices {\n                    price {\n                      currencyEquivalentPrice {\n                        roundedCurrencyAmt\n                        formattedCurrencyAmt\n                      }\n                      milesEquivalentPrice {\n                        mileCnt\n                        cashPlusMilesCnt\n                        cashPlusMiles\n                      }\n                    }\n                  }\n                }\n              }\n            }\n          }\n        }\n      }\n    }\n    offerDataList {\n      responseProperties {\n        discountInfo {\n          discountPct\n          discountTypeCode\n          nonDiscountedOffersAvailable\n        }\n        promotionsInfo {\n          promotionalCode\n          promotionalPct\n        }\n        discountInEligibilityList {\n          code\n          reason\n        }\n        resultsPerRequestNum\n        pageResultCnt\n        resultsPageNum\n        sortOptionsList {\n          sortableOptionDesc\n          sortableOptionId\n        }\n        tripTypeText\n      }\n      offerPreferences {\n        stopCnt\n        destinationAirportCode\n        connectionTimeRange {\n          maximumNum\n          minimumNum\n        }\n        originAirportCode\n        flightDurationRange {\n          maximumNum\n          minimumNum\n        }\n        layoverAirportCode\n        totalMilesRange {\n          maximumNum\n          minimumNum\n        }\n        totalPriceRange {\n          maximumNum\n          minimumNum\n        }\n      }\n      retailItemDefinitionList {\n        brandType\n        retailItemBrandId\n        refundable\n        retailItemPriorityText\n      }\n      pricingOptions {\n        pricingOptionDetail {\n          currencyCode\n        }\n      }\n    }\n    gqlSelectedOfferSets {\n      trips {\n        tripId\n        scheduledDepartureLocalTs\n        scheduledArrivalLocalTs\n        originAirportCode\n        destinationAirportCode\n        stopCnt\n        flightSegment {\n          destinationAirportCode\n          marketingCarrier {\n            carrierCode\n            carrierNum\n          }\n          operatingCarrier {\n            carrierCode\n            carrierNum\n          }\n          flightSegmentNum\n          originAirportCode\n          scheduledArrivalLocalTs\n          scheduledDepartureLocalTs\n          aircraft {\n            fleetTypeCode\n            subFleetTypeCode\n            newSubFleetType\n          }\n          flightLeg {\n            destinationAirportCode\n            feeRestricted\n            layover {\n              destinationAirportCode\n              layoverAirportCode\n              layoverDuration {\n                hourCnt\n                minuteCnt\n              }\n              departureFlightNum\n              equipmentChange\n              originAirportCode\n              scheduledArrivalLocalTs\n              scheduledDepartureLocalTs\n            }\n            operatedByOwnerCarrier\n            redEye\n            operatingCarrier {\n              carrierCode\n              carrierName\n            }\n            marketingCarrier {\n              carrierCode\n              carrierName\n            }\n            earnLoyaltyMiles\n            loyaltyMemberBenefits\n            dominantLeg\n            duration {\n              dayCnt\n              hourCnt\n              minuteCnt\n            }\n            originAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            destinationAirport {\n              airportTerminals {\n                terminalId\n              }\n            }\n            originAirportCode\n            aircraft {\n              fleetTypeCode\n              subFleetTypeCode\n              newSubFleetType\n            }\n            carrierCode\n            distance {\n              unitOfMeasure\n              unitOfMeasureCnt\n            }\n            scheduledArrivalLocalTs\n            scheduledDepartureLocalTs\n            dayChange\n          }\n        }\n        totalTripTime {\n          dayCnt\n          hourCnt\n          minuteCnt\n        }\n      }\n      offers {\n        additionalOfferProperties {\n          dominantSegmentBrandId\n          fareType\n        }\n        soldOut\n        offerItems {\n          retailItems {\n            retailItemMetaData {\n              fareInformation {\n                brandByFlightLegs {\n                  tripId\n                  brandId\n                  cosCode\n                }\n              }\n            }\n          }\n        }\n      }\n      additionalOfferSetProperties {\n        seatReferenceId\n      }\n    }\n    contentLinks {\n      type\n      variables {\n        brandProductMapping\n      }\n    }\n  }\n}',
        }
        random.shuffle(self.all_headers)
        retry_count = len(self.all_headers)
        last_cookie = ''
        for i, headers_rec in enumerate(self.all_headers):
            self.setup_proxy_str()
            print(f">>>>>>>>self.proxy_attr: {self.proxy_attr}")
            headers = headers_rec.get('headers', {})
            headers = self.compute_headers_trnx(headers)
            # print(f">>>>>>>>>>>>cash headers: {headers}")
            client = ZenRowsClient(c.ZENROWS_API_KEY)
            params = {"premium_proxy":"true"}
            response = crequests.post(
                'https://offer-api-prd.delta.com/prd/rm-offer-gql',
                impersonate="chrome124",
                proxies=self.proxy_attr,
                # params = params,
                headers=headers, json=json_data)

            logger.info(f"{self.AIRLINE.value} - {cabin_class.value}:: Retrieving Cash API Data => {i+1}/{retry_count} => Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                # if response.status_code == 444:
                #     continue
                if response.status_code == 444:
                    logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: result: {response.text}")
                headers_id = headers_rec.get("_id")
                update_target_headers(headers_id, {"active": False}, self.TARGET)

        return CrawlerException("No active headers to run")

    def now_milliseconds(self):
        return int(time.time() * 1000)
    def compute_headers_trnx(self, headers):
        cache_suffix, time_str = headers["transactionid"].split("_")
        cache_suffix = str(uuid.uuid4())
        new_time = self.now_milliseconds()
        print(f">>>>>>>>>>>>old time: {time_str} ---- new time: {new_time}")
        headers["transactionid"] = f"{cache_suffix}_{new_time}"
        # print("heades", headers)
        return headers
    
if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = DeltaAirlineRequestsCrawler()
        # travel_departure_date = datetime.date.today() + datetime.timedelta(days=14)
        travel_departure_date = datetime.date(year=2025, month=4, day=15)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=travel_departure_date.isoformat(),
                cabin_class=cabin_class,
                adults=adults,
            )
        )
        end_time = time.perf_counter()
        if flights:
            with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    # run("PVG", "PNG", c.CabinClass.Economy)
    # run("JFK", "DPS", c.CabinClass.All, 1)
    run("JFK", "LAX", c.CabinClass.All, 1)
    # run("ATL", "CDG", c.CabinClass.Business, 1)
    # run("CDG", "ORY", c.CabinClass.Economy, 1)
    # run("ORD", "IST", c.CabinClass.Economy, 1)
    # run("JFK", "LAX", c.CabinClass.First)
