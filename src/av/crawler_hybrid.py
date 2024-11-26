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
from dateutil import tz
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

from src.av.constants import CabinClassCodeMapping, CabinClassCodeIDMapping, CabinClassCodeTypeMapping
from src.exceptions import NoSearchResult, LoginFailed
from src import constants as c
from src.base import RequestsBasedAirlineCrawler, MultiLoginAirlineCrawler
from src.exceptions import ZenRowFailed, CrawlerException
from src.schema import CashFee, Flight, FlightSegment
from src.utils import get_airport_timezone
from src.db import get_target_headers, update_target_headers

logger = logging.getLogger(__name__)

        
class AviancaAirlineHybridCrawler(RequestsBasedAirlineCrawler):
    TARGET = 'avianca'
    AIRLINE = c.Airline.Avianca

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fare_codes: Dict[str, str] = {}
        self.cookie = ""
        self.headers = {}
        self.all_headers = []
        self.proxy_attr = self.setup_proxy_str()
        self.airport_timezone = get_airport_timezone()
    
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
        
        # proxy = self.get_private_proxy()
        # proxy_host = proxy.get('ip')  # rotating proxy or host
        # proxy_port = int(proxy.get('port'))  # port
        # proxy_user = proxy.get('user')  # username
        # proxy_pass = proxy.get('pwd')  # password
        
        proxy_user = "ihgproxy1"
        proxy_pass = "ihgproxy1234_country-us"
        proxy_host = "geo.iproyal.com"
        proxy_port = "12321"
        
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        return proxy_attr

    def fetch_headers_from_db(self):
        headers_rec = get_target_headers(self.TARGET)
        return headers_rec

    def convert_to_seconds(self, days=0, hours=0, minutes=0):
        return (3600 * 24 * days) + (3600 * hours) + (60 * minutes)

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment in enumerate(flight_data["flightsDetail"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")

                segment_origin = segment["departingCityCode"]
                segment_destination = segment["arrivalCityCode"]
                segment_origin_tz = self.airport_timezone.get(segment_origin, '')
                segment_destination_tz = self.airport_timezone.get(segment_destination, '')
                
                segment_departure_date = segment["departingDate"]
                segment_departure_time = segment["departingTime"]
                segment_arrival_date = segment["arrivalDate"]
                segment_arrival_time = segment["arrivalTime"]
                segment_aircraft = segment["operatedBy"]
                if segment_aircraft:
                    segment_aircraft = segment_aircraft.replace('OPERATED BY ', '')
                segment_carrier = segment["operatedCompany"]
                segment_flight_number = segment["flightNumber"]

                departure_datetime_str = f'{segment_departure_date}T{segment_departure_time}'
                departure_datetime_obj = datetime.datetime.strptime(departure_datetime_str, '%Y-%m-%dT%H:%M')
                arrival_datetime_str = f'{segment_arrival_date}T{segment_arrival_time}'
                arrival_datetime_obj = datetime.datetime.strptime(arrival_datetime_str, '%Y-%m-%dT%H:%M')

                segment_departure_datetime_tz = departure_datetime_obj.replace(tzinfo=tz.gettz(segment_origin_tz)).astimezone(tz.tzutc())
                segment_arrival_datetime_tz = arrival_datetime_obj.replace(tzinfo=tz.gettz(segment_destination_tz)).astimezone(tz.tzutc())
                segment_duration = duration_isoformat(segment_arrival_datetime_tz - segment_departure_datetime_tz)
                
                if len(flight_data["flightsDetail"]) > segment_index+1:
                    next_segment_departure_date = flight_data["flightsDetail"][segment_index+1]["departingDate"]
                    next_segment_departure_time = flight_data["flightsDetail"][segment_index+1]["departingTime"]
                    next_departure_datetime_str = f'{next_segment_departure_date}T{next_segment_departure_time}'
                    next_departure_datetime_obj = datetime.datetime.strptime(next_departure_datetime_str, '%Y-%m-%dT%H:%M')
                    connection_time = next_departure_datetime_obj - arrival_datetime_obj
                else:
                    connection_time = 0
                
                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_date,
                        departure_time=segment_departure_time,
                        departure_timezone="",
                        arrival_date=segment_arrival_date,
                        arrival_time=segment_arrival_time,
                        arrival_timezone="",
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=segment_duration,
                        layover_time=duration_isoformat(connection_time)
                        if connection_time
                        else None,
                    )
                )
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def extract_sub_classes_points(
        self, flight_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        points_by_fare_names: Dict[str, dict] = {}

        try:
            points_products = flight_data["products"]
            for points_product in points_products:
                if not points_product["soldOut"] and points_product["showBundle"]:
                    if not points_product['pricingType'].endswith('D'):
                        if points_product["cabinCode"] == CabinClassCodeIDMapping[cabin_class]:
                            if cabin_class == c.CabinClass.PremiumEconomy:
                                if points_product["productType"] != "B3":
                                    continue
                            fare_name = CabinClassCodeMapping[cabin_class]
                            if points_product["productType"] in CabinClassCodeTypeMapping:
                                fare_name += ' ' + CabinClassCodeTypeMapping[points_product["productType"]]
                            points_by_fare_names[fare_name] = {
                                "points": int(points_product["totalMiles"]),
                                "fare_brand_name": CabinClassCodeTypeMapping.get(points_product["productType"], '')
                            }

        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")
            import traceback
            traceback.print_exc()

        return points_by_fare_names

    def parse_flights(
        self, flights_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flights = flights_data["tripsList"]

        if not flights:
            raise NoSearchResult(airline=self.AIRLINE, reason="Not available flights!")

        logger.info(f"{self.AIRLINE.value}: Found {len(flights)} flights...")

        all_cabins = []
        if cabin_class == c.CabinClass.All:
            all_cabins = [
                c.CabinClass.Economy,
                c.CabinClass.First,
                c.CabinClass.Business,
                c.CabinClass.PremiumEconomy
            ]
        else:
            all_cabins = [cabin_class]

        for index, flight_search_result in enumerate(flights):
            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

            for cabin_item in all_cabins:
                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_item)
                if not points_by_fare_names:
                    continue

                try:
                    segments = self.extract_flight_detail(flight_search_result)
                except Exception as e:
                    raise e
                duration = flight_search_result["duration"]
                duration = duration.replace(':', 'H')
                duration = f'PT{duration}M'

                for fare_name, points_and_cash in points_by_fare_names.items():
                    if not segments:
                        continue
                    flight = Flight(
                        airline=str(self.AIRLINE.value),
                        origin=segments[0].origin,
                        destination=segments[-1].destination,
                        cabin_class=str(cabin_item.value),
                        airline_cabin_class=fare_name,
                        fare_brand_name=points_and_cash["fare_brand_name"],
                        points=points_and_cash["points"],
                        cash_fee=CashFee(
                            amount=float(flight_search_result["usdTaxValue"]),
                            currency="USD",
                        ),
                        segments=segments,
                        duration=duration,
                    )
                    yield flight

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        flights_data = self.get_flights_points(origin, destination, departure_date, cabin_class, adults)
        
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
            cash_flights = self.parse_flights(flights_data, cabin_item)
            # points_flights = self.parse_points_flights(flights_points_data, cabin_item) if (flights_points_data and not points_errors) else {}
            # flights = self.match_flights(cash_flights, points_flights)
            for flight in cash_flights:
                yield flight
                
    def get_flights_points(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:

        json_data = {
            "internationalization": {
                "language": "en",
                "country": "us",
                "currency": "usd"
            },
            "currencies": [
                {
                    "currency": "USD",
                    "decimal": 2,
                    "rateUsd": 1
                }
            ],
            "passengers": 1,
            "od": {
                "orig": origin,
                "dest": destination,
                "depDate": departure_date.isoformat(),
                "depTime": ""
            },
            "filter": False,
            "codPromo": None,
            "idCoti": "209093642898299879",
            "officeId": "",
            "ftNum": "",
            "discounts": [],
            "promotionCodes": [
                "DBEP36"
            ],
            "context": "D",
            "channel": "COM",
            "cabin": "1",
            "itinerary": "OW",
            "odNum": 1,
            "usdTaxValue": "0",
            "getQuickSummary": False,
            "ods": "",
            "searchType": "SMR",
            "searchTypePrioritized": "AVH",
            "sch": {
                "schHcfltrc": "xAQL/r6euF+3mSh6SUwB3qb7+2xhyAB2CyWSn/Y92gw="
            },
            "posCountry": "GB",
            "odAp": [
                {
                    "org": origin,
                    "dest": destination,
                    "cabin": 1
                }
            ],
            "suscriptionPaymentStatus": ""
        }
        self.all_headers = self.fetch_headers_from_db()
        retry_count = len(self.all_headers)
        last_cookie = ''
        for i, headers_rec in enumerate(self.all_headers):
            headers = headers_rec.get("headers", {})
            payload = headers_rec.get("payload", {})
            payload["odAp"][0]["org"] = origin
            payload["odAp"][0]["dest"] = destination
            payload["od"]["orig"] = origin
            payload["od"]["dest"] = destination
            payload["od"]["depDate"] = departure_date.isoformat()
            del payload["od"]["departingCity"]
            del payload["od"]["arrivalCity"]
            del payload["ipAddress"]
            
            response = crequests.post(
                'https://api.lifemiles.com/svc/air-redemption-find-flight-private',
                impersonate="chrome124",
                proxies=self.proxy_attr,
                headers=headers, json=payload)
            
            time.sleep(random.uniform(1.13,1.23))

            logger.info(f"{self.AIRLINE.value}: Retrieving Points API Data => {i+1}/{retry_count} => Status: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                headers_id = headers_rec.get("_id")
                update_target_headers(headers_id, {"active": False}, self.TARGET)

        return CrawlerException("No active headers to run")

if __name__ == "__main__":
    
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = AviancaAirlineHybridCrawler()
        # travel_departure_date = datetime.date.today() + datetime.timedelta(days=14)
        travel_departure_date = datetime.date(year=2025, month=3, day=5)

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

    run("IAD", "BCN", c.CabinClass.All, 1)
    # run("MIA", "LIM", c.CabinClass.All, 1)
    # run("JFK", "BOG", c.CabinClass.PremiumEconomy)
    # run("MIA", "BOG", c.CabinClass.All, 1)
    # run("MIA", "GRU", c.CabinClass.All, 1)
