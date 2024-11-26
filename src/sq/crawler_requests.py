import base64
import datetime
import glob
import json
import logging
import os
import re
import shutil
import time
from typing import Iterator, Optional
from xml.dom import minidom
from typing import Dict, Iterator, List, Optional
from isodate import duration_isoformat
from zenrows import ZenRowsClient
import random
from scrapy import Selector

from playwright.sync_api import Locator, Page
from curl_cffi import requests as crequests
from botasaurus_requests import request
import requests
from src import constants as c
from src.base import RequestsBasedAirlineCrawler
from src.sq.constants import CabinClassCodeMapping, EndpointCabinClassCodeMapping
from src.exceptions import NoSearchResult, CrawlerException, ZenRowFailed
from src.proxy import PrivateProxyService
from src.schema import CashFee, Flight, FlightSegment
from src.types import SmartCabinClassType, SmartDateType
from src.utils import (
    convert_time_string_to_iso_format,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    extract_k_digits,
    extract_letters,
    parse_date,
    parse_time,
    sanitize_text,
)
from src.db import get_target_headers, update_target_headers
import traceback
from pprint import pprint

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


SingaporeAirlineCredentials = c.Credentials[c.Airline.SingaporeAir]

class SingaporeAirRequestCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = c.Airline.SingaporeAir
    REQUIRED_LOGIN = True
    TARGET = 'singaporeair'
    HOME_PAGE_URL = "https://www.singaporeair.com/en_UK/us/home#/book/redeemflight"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        self.bota_proxy_str = ""
        self.proxy_str = self.setup_proxy_str()
        super().__init__(*args, **kwargs)
        
    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-us",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }
        
    def extract_flight_detail(
        self,
        flight_data: Dict,
        flight_dictionary: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment in enumerate(flight_data["legs"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                if len(flight_data["legs"]) > segment_index+1:
                    connection_time = flight_data["legs"][segment_index+1].get("layoverDuration", 0)
                else:
                    connection_time = 0

                segment_origin = segment["originAirportCode"]
                segment_destination = segment["destinationAirportCode"]
                segment_departure_datetime = segment["departureDateTime"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment["arrivalDateTime"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                aircraft_id = segment["aircraftCode"]
                segment_aircraft = flight_dictionary["aircraft"][aircraft_id]
                segment_carrier = segment["carrierCode"]
                segment_flight_number = segment["flightNumber"]
                if not segment_carrier:
                    segment_carrier = segment.get("marketingAirlineCode", None)
                segment_duration = segment["flightDuration"]

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_datetime.date().isoformat(),
                        departure_time=segment_departure_datetime.time().isoformat()[:5],
                        departure_timezone="",
                        arrival_date=segment_arrival_datetime.date().isoformat(),
                        arrival_time=segment_arrival_datetime.time().isoformat()[:5],
                        arrival_timezone="",
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=duration_isoformat(datetime.timedelta(milliseconds=segment_duration)),
                        layover_time=duration_isoformat(datetime.timedelta(milliseconds=connection_time))
                        if connection_time
                        else None,
                    )
                )
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def extract_sub_classes_points(
        self, flight_data, miles, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        points_by_fare_names: Dict[str, dict] = {}

        try:
            miles_codes = flight_data["legs"][0]["cabinClassAvailability"]
            for miles_code in miles_codes:
                if miles_code.get('numberOfSeats', None) or miles_code.get('status', None):
                    selling_class_code = miles_code["sellingClass"]
                    for miles_selling_class in miles["sellingClass"]:
                        if miles_selling_class["code"] == selling_class_code:
                            fare_name = CabinClassCodeMapping[cabin_class] + ' ' + miles_selling_class["description"]
                            points_by_fare_names[fare_name] = {
                                "points": miles_selling_class["miles"],
                                "fare_brand_name": miles_selling_class["description"]
                            }

        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")
            import traceback
            traceback.print_exc()

        return points_by_fare_names

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
        self.bota_proxy_str = f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'
        return proxy_attr
    
    def fetch_data(
        self, cookies_rec: {}, origin:str, destination: str, departureMonth: str, cabin_class, session
    ) -> Optional[Dict[str, dict]]:
        try:
            cookies = cookies_rec.get("headers", [])
            cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            # print(f">>>> current cooies: {cookies}")
            
            cabin_code = EndpointCabinClassCodeMapping[cabin_class]

            # headers = {
            #     'authority': 'www.singaporeair.com',
            #     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            #     'accept-language': 'en-US,en;q=0.9,pt;q=0.7',
            #     'cache-control': 'max-age=0',
            #     'content-type': 'application/x-www-form-urlencoded',
            #     'cookie': cookie_str,
            #     'origin': 'https://www.singaporeair.com',
            #     'referer': 'https://www.singaporeair.com/en_UK/us/home',
            #     'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            #     'sec-ch-ua-mobile': '?0',
            #     'sec-ch-ua-platform': '"Windows"',
            #     'sec-fetch-dest': 'document',
            #     'sec-fetch-mode': 'navigate',
            #     'sec-fetch-site': 'same-origin',
            #     'sec-fetch-user': '?1',
            #     'upgrade-insecure-requests': '1',
            #     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            # }
            
            data = {
                '_payByMiles': 'on',
                'payByMiles': 'true',
                'fromHomePage': 'true',
                'orbOrigin': origin,
                'orbDestination': destination,
                '_tripType': 'on',
                'tripType': 'O',
                'departureMonth': departureMonth,
                'returnMonth': '',
                'cabinClass': cabin_code,
                'numOfAdults': '1',
                'numOfChildren': '0',
                'numOfInfants': '0',
                'flowIdentifier': 'redemptionBooking',
                '_eventId_flightSearchEvent': '',
                'isLoggedInUser': 'true',
                'numOfChildrenNominees': '1',
                'numOfAdultNominees': '1',
                'flexibleDates': 'off',
            }

            client = ZenRowsClient(c.ZENROWS_API_KEY)
            params = {"premium_proxy":"true"}
            for i in range(1):
                # response = client.post(
                #     'https://www.singaporeair.com/redemption/searchFlight.form',
                #     headers=headers,
                #     params=params,
                #     data=data
                # )
                # proxy_attr = self.setup_proxy_str()
                # print(f">>>>>>>>session.headers: {session.headers}")
                response = session.post(
                    'https://www.singaporeair.com/redemption/searchFlight.form',
                    impersonate="chrome124",
                    # proxy=self.bota_proxy_str,
                    proxies=self.proxy_str,
                    # headers=session.headers,
                    data=data
                )
                print(f'>>> Zenrow Call #{i+1}: {response.status_code}')
                if response.status_code == 200 and 'pageData = ' in response.text:
                    page_data_content = response.text.split('pageData = ')[-1].split('var ajax_urls')[0]
                    page_data_content = page_data_content.strip().strip('; ')
                    page_data = json.loads(page_data_content)
                    return page_data
                else:
                    _id = cookies_rec.get("_id")
                    update_target_headers(_id, {"active": False}, self.TARGET)
        except Exception as err:
            traceback.print_exc()
            _id = cookies_rec.get("_id")
            update_target_headers(_id, {"active": False}, self.TARGET)
            logger.error(f"fetch_data error:{err}")   
                               
    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        
        cookies_recs = get_target_headers(self.TARGET)
        logger.debug(f"total cookies_recs {len(cookies_recs)}")
        if not cookies_recs:
            raise CrawlerException("No active cookies to run !")
        
        success = False
        departureMonth = datetime.datetime.strftime(departure_date, '%d/%m/%Y')
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
        
        sess = crequests.Session(impersonate="chrome124", proxies=self.proxy_str)
        last_success_cookies_rec = []
        nb_cookies = cookies_recs[:3]
        for cabin_klass in all_cabins:
            for cookie_idx, cookies_rec in enumerate(nb_cookies):
                cookies = cookies_rec.get("headers", [])
                cookies_dict = {cookie['name']:cookie['value'] for cookie in cookies}
                new_cookies_dict = {k:v for k,v in sess.cookies.items()}
                
                cookies_dict.update(new_cookies_dict)
                cookie_str = "; ".join([f"{k}={v}" for k,v in cookies_dict.items()])
                
                cabin_code = EndpointCabinClassCodeMapping[cabin_klass]

                headers = {
                    'authority': 'www.singaporeair.com',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'accept-language': 'en-US,en;q=0.9,pt;q=0.7',
                    'cache-control': 'max-age=0',
                    'content-type': 'application/x-www-form-urlencoded',
                    'cookie': cookie_str,
                    'origin': 'https://www.singaporeair.com',
                    'referer': 'https://www.singaporeair.com/en_UK/us/home',
                    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                }
                # set headers for whole session
                sess.headers = headers
                
                flights_data = self.fetch_data(cookies_rec, origin, destination, departureMonth, cabin_klass, sess)
                flights_data = flights_data or {}
                logger.debug(f"> scraping with cookie {cookie_idx+1}th/{len(nb_cookies)} for cabin_klass: {cabin_klass} route: {origin}-{destination} - flight count {len(flights_data)}")
                if not flights_data:
                    if len(all_cabins) > 1:
                        continue
                        
                    raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")


                try: 
                    flights = flights_data["flightSearch"]["response"]["data"]["flights"][0]["segments"]
                    miles = flights_data["flightSearch"]["response"]["data"]["miles"]
                    dictionary = flights_data["flightSearch"]["response"]["dictionary"]
                except (KeyError, IndexError):
                    if len(all_cabins) > 1:
                        continue
                    raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

                
                logger.info(f"{self.AIRLINE.value}: Found {len(flights)} flights...")
                for index, flight_search_result in enumerate(flights):
                    logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item for cabin {cabin_klass.value} => index: {index}...")

                    points_by_fare_names = self.extract_sub_classes_points(flight_search_result, miles, cabin_klass)
                    if not points_by_fare_names:
                        continue
                    
                    segments = []
                    try:
                        segments = self.extract_flight_detail(flight_search_result, dictionary)
                    except Exception as e:
                        raise e
                    duration = flight_search_result["tripDuration"]

                    for fare_name, points_and_cash in points_by_fare_names.items():
                        if not segments:
                            continue
                        flight = Flight(
                            airline=str(self.AIRLINE.value),
                            origin=segments[0].origin,
                            destination=segments[-1].destination,
                            cabin_class=str(cabin_klass.value),
                            airline_cabin_class=fare_name,
                            fare_brand_name=points_and_cash["fare_brand_name"],
                            points=points_and_cash["points"],
                            segments=segments,
                            duration=duration_isoformat(datetime.timedelta(milliseconds=duration)),
                        )
                        yield flight
                        
                        success = True
                        new_cookies_dict = {k:v for k,v in sess.cookies.items()}
                        cookies_dict.update(new_cookies_dict)
                        updated_cookies = [{"name": k, "value": v} for k,v in cookies_dict.items()]
                        last_success_cookies_rec = [cookies_rec.get("_id"), updated_cookies]
                        
            time.sleep(random.uniform(1.53,2.2))
            
        if last_success_cookies_rec:
            _id, updated_cookies = last_success_cookies_rec
            update_target_headers(_id, {"headers": updated_cookies}, self.TARGET)
                
        if not success:
            raise ZenRowFailed("Zenrows Requests Failed !")
        

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = SingaporeAirRequestCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=4)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                cabin_class=cabin_class,
            )
        )
        end_time = time.perf_counter()

        if flights:
            with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    # run("SIN", "CGK", c.CabinClass.Business)
    # run("SFO", "BKK", c.CabinClass.All)
    run("SIN", "CGK", c.CabinClass.All)
    # run("SIN", "LHR", c.CabinClass.All)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
