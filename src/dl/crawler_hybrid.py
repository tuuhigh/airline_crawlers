import asyncio
import datetime
import json
import logging
import random
import re
import os
import traceback
import shutil
import time
import uuid
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
from src.db import insert_target_headers, get_target_headers, update_target_headers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_RTC_PATH = os.path.join(c.BASE_DIR, "playwright", "webrtc_addon")
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

    def get_private_proxy(self):
        response = requests.get(c.PROXY_SERVICE_URL)
        if response.status_code == 200:
            res = response.json()
            proxy = res.get('proxy')
            return proxy
        return {}
    
    def get_smartproxy(self):
        proxy = {
            "ip": self.smart_proxy_host,
            "port": self.smart_proxy_port,
            "user": "spyc5m5gbs",
            "pwd": "puFNdLvkx6Wcn6h6p8",
        }
        return proxy
    
    def get_proxy(self):
        return self.get_private_proxy()
    
    def get_user_dir(self):
        utc_now = datetime.datetime.utcnow().isoformat().replace(":", "_")
        self._user_data_dir = os.path.join(c.BASE_DIR, f"_user_data_dir_{utc_now}")

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
        # print(">>>>>>>>>>.. request_handler headers:", headers)
    
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
    
    async def fetch_cookie_playright(self, last_cookie=""):
        # global FETCHED_COOKIES
        # if last_cookie and last_cookie in FETCHED_COOKIES:
        #     del FETCHED_COOKIES[FETCHED_COOKIES.index(last_cookie)]
        # if FETCHED_COOKIES:
        #     return FETCHED_COOKIES[0]
        try:
        
            print(1)
            proxy_vals = self.get_proxy()
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
                await page.route("**", self.block_resouces)

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
            

class DeltaAirlineHybridCrawler(RequestsBasedAirlineCrawler):
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

    def get_smart_proxy(self):
        proxy = {
            "ip": self.smart_proxy_host,
            "port": self.smart_proxy_port,
            "user": "spyc5m5gbs",
            "pwd": "puFNdLvkx6Wcn6h6p8",
        }
        return proxy
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
        
        proxy = self.get_smart_proxy()
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
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
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
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes Cash...")
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

    def match_flights(self, cash_flights: List[Flight], points_flights: List[Flight], cabin_class):
        flights = []
        logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Doing matching for {len(cash_flights)} Cash and {len(points_flights)} Points")
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
            logger.error(f"{self.AIRLINE.value}: Cash Error Message: {pricing_errors}")

        points_errors = (flights_points_data or {}).get('errors', [])
        if points_errors:
            logger.error(f"{self.AIRLINE.value}: points Error Message: {points_errors}")
        
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
            flights = self.match_flights(cash_flights, points_flights, cabin_item)
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
        
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
            'airline': 'DL',
            'applicationid': 'DC',
            'authorization': 'GUEST',
            'channelid': 'DCOM',
            'content-type': 'application/json',
            # 'cookie': 'AMCV_F0E65E09512D2CC50A490D4D%40AdobeOrg=T; TLTUID=AF17FA96146B10143A18BC493A58A032; rxVisitor=1715963821174HF60K11HCORIT23NGJA8OHSC1EMGRO1E; s_ecid=MCMID%7C16739982591190755480163554947216299227; _fbp=fb.1.1715963821762.1700882866; uuid=bba28ce5-343d-45ec-b485-16f1c0c3ac0b; ft_id=590761168D304D; QuantumMetricUserID=73380caf390fd7c571d3778b0a3b6e0b; AAMC_delta_0=REGION%7C3; aam_uuid=21698014878257832910820361166915612156; visitorID=8992f5bb-2128-491d-88a7-7acf46065a11; tkpi_fvid=c65c7dcf-b869-4936-aed7-98aa26664060; LPVID=VkOGZlMmIyMDIyZGFiNjZj; trip_type=; kndctr_F0E65E09512D2CC50A490D4D_AdobeOrg_identity=CiYxNjczOTk4MjU5MTE5MDc1NTQ4MDE2MzU1NDk0NzIxNjI5OTIyN1IRCOKc74b6MRgBKgRTR1AzMAPwAeKc74b6MQ==; DL_PER=true; CTY_LANG=true; _dpm_id.6941=12326236-63a7-43db-a525-9be2dbbede71.1716390713.2.1716401451.1716390713.e76db349-4474-4967-8e9e-daa47534a384; prefUI=en-us; criteoid=Tz-vm2bkYQFnmwhTrVg3d6PSXMdX27fh; dlsite=a; TLTSID=25580237640999940468137419955064; dtCookie=v_4_srv_11_sn_28AC673BB3C42CA6F2AEC14AF067763F_perc_100000_ol_0_mul_1_app-3A9912e316bf6ad580_1; xssid=9d2b2b99-6c59-4d38-bed7-0555ff30fe1c; check=true; s_visit=1; exp_type=%5B%5BB%5D%5D; s_dl=1; c_m=undefinedDirect%20LoadDirect%20Load; s_chl=%5B%5B%27Direct%2520Load%27%2C%271718199422748%27%5D%5D; s_cc=true; QuantumMetricSessionID=c424ded840f08670cc5d769ed5595720; dtPCB=true; AKA_A2=A; bm_mi=B50CD495617C36C5DD4CFD56166EADDC~YAAQZTNDGxu+BQeQAQAAYMiqDBjK82lmqmwiBWgfb5KFiDDwFUoTTyloQLyZDe2hHnRBzN59vzFOyrkhXFK9BYygy22aJaIhynqiTPwO5YtzacHpEJbQw8/se5GkqE5XvkuCC3OzSVzqWcluoV7Js4DhfE2vAs2pRPnDyVdq2bs1CarzrjF7YbEgXQQN4qeF9kgVS0L4Y3nMcjI9OTT0Kgd5GbPZiG9y50BjvD/M4f0R7bEtsuAbe2Ikr5t6DfrSzGvknUca2I5uceXjteu6YWj8ALf3ahjUsWRGpSGEOC1e+kSbVcp1JUDl1u813FSkDE4C7hARYvt1wGzAXdDJ8v+NvfDQWiuw~1; ak_bmsc=475E09471E8E2EC7888502B98FA28240~000000000000000000000000000000~YAAQZTNDGy6+BQeQAQAAN8+qDBjkGDTv9oQNSGf+WDDLou7ibhn3YIcJV3bbg50zg3JuDIkKvnolehFw7AgtuJGg4IvXx9tMPSueEnm/RpdeDWSntpvYRzHQaJ9gyjfTBLrxKehKM6txD6089r2HDJ2kG5Sn2f1gqjBR0sIvWZGqhjcwvL+U4wxeGT0McwKB5gbccXxgQ4jyjyxtCLGQXxMB3sB0J8Z7KsRhdsLpjh5onUFRhjcONhM9cBDGXjkSQ9yrgPomV4dKnPPdlFeDK7Lrog95a4yN0o+KwtY84a/OQ9dnNkczDIfWq3Ox7G83mm1CpJaD3XQvKgGjSFK9VOZq3U4bIGswM2dSPhWeeHwB8BHQoRVT4mXxirNxbLHSAYM1I3HJG2BzqegGZU7qR+cX10AHc5uHGSXHHP3L8g/qVCO4L7NjkE5U6u5Q+/trIlD8Wfz2d7a63RZzjqzrWgSJvh4fa7LhA9FtcXrb+iYR/ATFr9YA+gzx2qkdhqIwWg416ThRe5nHtv1mSeMY; mbox=PC#4eecf6cdf9904fdda6ca883085601fd1.38_0#1781444240|session#b3f5a20015c64e3ba049c300be50bfc2#1718201300; akaalb_alb_offer_api_prd_delta_com=~op=offer_api_prd_delta_100E:offer_api_prod_aws_east|~rv=96~m=offer_api_prod_aws_east:0|~os=06954c349a07914ebfe39f47635613f8~id=0ce4bb8d1473fe3735865176ea1cf682; _abck=D2E7A09DCB6A677A671C47826C333C15~0~YAAQJDNDGzy2sOaPAQAAt+mqDAwzRhwhxLgtTQi+hG5oX8f0+Yqufrh+MVqhnUMzvwpgQS79tzpdsLnJZT7PGYttC1+22kgemnEXs9s6dIPmbOjIkO9cfi5tHGBGWWI0VDHXVEHmMRWcTtk/yzbtVKhV7AaH9de8ClkU3cwYXqOqyYM8Q2yzdC+Uo9t5bwsZG4Bwpvfc4usOFNrSSRc8L7aK4BiHgP++wAZmUeaWq6caT+sN9JRwfdJZVDt04Jk6o5wf8mQ1Q/o+yhpeTJ1MDL7EhlATQs4NLY7TNMInbzuILECYLHACwR0jWIOTLHSjA85ug5ZQ93AQTOFlL3msGL/XOyxVe49/2FthJKYIrzS0tYZOBMOjd3pAjQfpm47j6QumAAiOZl806atEPC23MDZcLCXUS9XeRuqh+roXOggUF6PhJBKBWXg=~-1~-1~1718203038; bm_sz=177CA6C6C2FFDBF655ADF16A239C6508~YAAQJDNDGz62sOaPAQAAt+mqDBirFxMo1QE+I7cDlsNdi0oNbQaqocciLeXyyBCsx1varNa06Jn7OVzMK1GhuBL8EhTxbGAVk8c1RUITCDXKqKW/O6ISD+fQ2PQqfwNiIAzN+XH8T/K2wISnbQ8RwJ70RpuTRmMzRqvoaq4cZp69Xk0Vp+HQq5R3AjF4/xduchP62isIvfQkdSvA+fnNUn2hjpNSlgmV+KwqGDEs003tTZzPk0gOjN4cug/ZzYWWNFFit0VX/2O3MEbUSKVXDPC0+aFFc+E6bvlbHKN6cx12bBB4sfr++wzOLFuC1KlJtD0BAR5uJbTL2fTuSunM8jlWXE4Arg5ub1IlnXLKtvBiEfGquZUbZ0IWapKYk4P9Hm71hnmP6pz3Rw9B4xj7XwZUm0k3ioCI//XGINw=~3162946~3490613; tnt_pagename=Select%20Outbound%20Flight; bm_sv=8CF3B9BD795DA093A7D14318B80BBB9A~YAAQZTNDGze+BQeQAQAA3/iqDBhcGDDCoWdo1z86k778/6LwIa2mQLayidzGZteZrB1IP2pI9B4d5A0IaqhpgVjhbLcPM9gqeB9TlkDD/G5TBfrDKSrSS/yS7KqCPBCQIsqw8dMxakJOVbbbSlCm2JvASqJKsbY5tOd98jCE26//q4qNIeOIKQpwLgbuXOAk6A5hCP1x6NvQwn/nYVD4xL+Czc/07G3lWcBhn5yRPCP4e6iOww8jFA1Cze54T+56~1; tas=%7B%22createdDate%22%3A1718199425353%2C%22ID%22%3A%22xbz72332a8q.1718199425353%22%2C%22status%22%3A%22existing%22%2C%22lastVisitedDate%22%3A1718199450539%7D; tkpi_phid=ee25a1c7-aad2-48a7-a6c7-0c4c7f0fc202; tkpiphid=ee25a1c7-aad2-48a7-a6c7-0c4c7f0fc202; s_nr=1718199451498-Repeat; s_sq=deltacom2%3D%2526c.%2526a.%2526activitymap.%2526page%253DSelect%252520Outbound%252520Flight%2526link%253DMiles%2526region%253DBODY%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c',
            'origin': 'https://www.delta.com',
            'priority': 'u=1, i',
            'referer': 'https://www.delta.com/',
            'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'transactionid': f'{str(uuid.uuid4())}_1718199451507',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'x-app-type': 'shop',
        }
        
        async with ClientSession() as session:
            cookie_fetcher = CookieFetcher()
            self.headers["cookie"] = await cookie_fetcher.fetch_cookie_playright()
            insert_target_headers(self.headers, self.TARGET)
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

        retry_count = 3
        last_cookie = ''
        proxy_user = "ihgproxy1"
        proxy_pass = "ihgproxy1234_country-us"
        proxy_host = "geo.iproyal.com"
        proxy_port = "12321"
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        
        for i in range(retry_count):
            self.headers = self.compute_headers_trnx(self.headers)
            response = crequests.post(
                'https://offer-api-prd.delta.com/prd/rm-offer-gql',
                impersonate="chrome120",
                proxies=proxy_attr,
                # params=params,
                headers=self.headers, json=json_data)

            logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Retrieving Points API Data => {i+1}/{retry_count} => Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                pass

        return CrawlerException(f"{self.AIRLINE.value} - {cabin_class.value}: Hydrid cookie failed")


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
        
    
        proxy_user = "ihgproxy1"
        proxy_pass = "ihgproxy1234_country-us"
        proxy_host = "geo.iproyal.com"
        proxy_port = "12321"
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        retry_count = 3
        
        for i in range(retry_count):
            self.headers = self.compute_headers_trnx(self.headers)
            response = crequests.post(
                'https://offer-api-prd.delta.com/prd/rm-offer-gql',
                impersonate="chrome120",
                proxies=proxy_attr,
                # params = params,
                headers=self.headers, json=json_data)

            logger.info(f"{self.AIRLINE.value}-{cabin_class.value}: Retrieving Cash API Data => {i+1}/{retry_count} => Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                pass

        return CrawlerException(f"{self.AIRLINE.value} - {cabin_class.value}: Hydrid cookie failed")

    def now_milliseconds(self):
        return int(time.time() * 1000)
    
    def compute_headers_trnx(self, headers):
        cache_suffix, time_str = headers["transactionid"].split("_")
        new_time = self.now_milliseconds()
        # print(f">>>>>>>>>>>>old time: {time_str} ---- new time: {new_time}")
        headers["transactionid"] = f"{cache_suffix}_{new_time}"
        # print(">> computed headers", headers)
        return headers
    
if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = DeltaAirlineHybridCrawler()
        # travel_departure_date = datetime.date.today() + datetime.timedelta(days=14)
        travel_departure_date = datetime.date(year=2024, month=11, day=29)

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
