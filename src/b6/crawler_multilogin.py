import datetime
import logging
import random
import hashlib
import time
import socket
import json
import re
from typing import Iterator, List, Optional, Tuple, Dict

import requests
from src import constants as c
from src.base import MultiLoginAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException
from src.schema import CashFee, Flight, FlightSegment
from src.b6.constants import (
    CabinClassCodeMapping,
    CabinClassCodeMappingForHybrid,
)
from src.exceptions import NoSearchResult
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    parse_time,
    get_random_port
)
from isodate import duration_isoformat
from src import db

DISABLE_LOGGERS = [
    "seleniumwire.server",
    "hpack.hpack",
    "hpack.table",
    "seleniumwire.handler"
]
for thirdparty_logger in DISABLE_LOGGERS:
    logging.getLogger(thirdparty_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


from selenium import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from seleniumwire import webdriver as webdriversw  # Import from seleniumwire

STARTER_URL = "https://app.multiloginapp.com/WhatIsMyIP"
MLX_BASE = "https://api.multilogin.com"
MLX_LAUNCHER = "https://launcher.mlx.yt:45001/api/v1"
LOCALHOST = "http://127.0.0.1"
HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

USERNAME = "anujpatel@odynn.com"
PASSWORD = "ILoveMultiLogins1234@#"


class JetBlueMultiloginCrawler(MultiLoginAirlineCrawler):
    AIRLINE = Airline.JetBlue
    BLOCK_URLS = [
        'pdx-col.eum-appdynamics.com',
        'www.jetblue.com/resp-magnoliapublic/.rest/jetblue',
        'sdk.asapp.com',
        'www.googletagmanager.com',
        'px-cloud.net',
        'fullstory.com',
        'facebook.net',
        'micpn.com',
        'tiktok.com',
        'doubleclick.net',
    ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # profile = db.get_multilogin_profile_blocked_webrtc()
        # self.PROFILE_ID = profile.get("profile_id")
        # self.FOLDER_ID = profile.get("folder_id")
        # browser_type = profile.get("browser")
        # logger.info(f'browser: {browser_type}')
        # logger.info(f'PROFILE ID: {self.PROFILE_ID}')
        # self.OPTIONS = ChromiumOptions() if browser_type == 'chrome' else FirefoxOptions()

    @staticmethod
    def signin() -> str:

        payload = {
            'email': USERNAME,
            'password': hashlib.md5(PASSWORD.encode()).hexdigest()
            }

        r = requests.post(f'{MLX_BASE}/user/signin', json=payload)

        if(r.status_code != 200):
            logger.info(f'\nError during login: {r.text}\n')
            return ''
        else:
            response = r.json()['data']
            token = response['token']
            return token


    def start_profile(self) -> webdriver:

        r = requests.get(f'{MLX_LAUNCHER}/profile/f/{self.FOLDER_ID}/p/{self.PROFILE_ID}/start?automation_type=selenium', headers=HEADERS)

        response = r.json()

        if(r.status_code != 200):
            logger.info(f'\nError while starting profile: {r.text}\n')
            return None
        else:
            logger.info(f'\nProfile {self.PROFILE_ID} started.\n')

            selenium_port = response.get('status').get('message')
            sw_address = socket.gethostbyname(socket.gethostname())
            sw_port = get_random_port()
            sw_options = {
                "auto_config": False,
                "addr": sw_address,
                "port": sw_port,
                'disable_encoding': True,
                "request_storage_base_dir": "/tmp",  # Use /tmp to store captured data
            }
            print(f">>>>>>> {self.OPTIONS}")
            options = self.OPTIONS

            proxy = PROXY = f"{sw_address}:{sw_port}"
            print(f">>>>>>> proxy: {proxy}")
            # webdriversw.DesiredCapabilities.FIREFOX['proxy'] = {
            # "httpProxy": PROXY,
            # "ftpProxy": PROXY,
            # "sslProxy": PROXY,
            # "proxyType": "MANUAL",

            # }

            firefox_capabilities = webdriversw.DesiredCapabilities.FIREFOX
            firefox_capabilities['marionette'] = True
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": proxy,
                "sslProxy": proxy
            }
            # driver = webdriver.Firefox(capabilities=firefox_capabilities)
            driver = webdriversw.Remote(
                command_executor=f'{LOCALHOST}:{selenium_port}',
                options=options,
                desired_capabilities=firefox_capabilities,
                # desired_capabilities=self.OPTIONS.to_capabilities(),
                seleniumwire_options=sw_options
            )

            return driver

    def stop_profile(self) -> None:
        r = requests.get(f'{MLX_LAUNCHER}/profile/stop/p/{self.PROFILE_ID}', headers=HEADERS)

        if(r.status_code != 200):
            logger.info(f'\nError while stopping profile: {r.text}\n')
        else:
            logger.info(f'\nProfile {self.PROFILE_ID} stopped.\n')


    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_data in enumerate(flight_data["segments"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                connection_time = segment_data.get("layover", None)

                segment_origin = segment_data["from"]
                segment_destination = segment_data["to"]
                segment_departure = segment_data["depart"].replace("Z","+00:00")
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure)
                segment_arrival = segment_data["arrive"].replace("Z","+00:00")
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival)
                timezone_pattern = r'[\+\-]\d{2}:\d{2}$'
                departure_timezone_match = re.search(timezone_pattern, segment_departure)
                if departure_timezone_match:
                    departure_timezone = departure_timezone_match.group()
                else:
                    departure_timezone = ""
                arrival_timezone_match = re.search(timezone_pattern, segment_arrival)
                if arrival_timezone_match:
                    arrival_timezone = arrival_timezone_match.group()
                else:
                    arrival_timezone = ""
                segment_aircraft = segment_data["aircraft"]
                segment_carrier = segment_data["operatingAirlineCode"]
                segment_flight_number = segment_data["flightno"]
                segment_duration = segment_data["duration"]

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_datetime.date().isoformat(),
                        departure_time=segment_departure_datetime.time().isoformat()[:5],
                        departure_timezone=departure_timezone,
                        arrival_date=segment_arrival_datetime.date().isoformat(),
                        arrival_time=segment_arrival_datetime.time().isoformat()[:5],
                        arrival_timezone=arrival_timezone,
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=segment_duration,
                        layover_time=connection_time
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

        for air_bound in flight_data["bundles"]:
            if air_bound.get("code","") in cabin_class_codes:
                try:
                    fare_name = CabinClassCodeMapping[cabin_class]
                    fare_brand_name = air_bound["code"]
                    if fare_brand_name:
                        fare_brand_name = fare_brand_name.replace('_', ' ').replace('-', ' ')
                        fare_name = f'{fare_name} {fare_brand_name}'

                    points = -1 if air_bound.get("status","") == 'SOLD_OUT' else air_bound["points"]
                    amount = 0 if air_bound.get("status","") == 'SOLD_OUT' else air_bound["fareTax"]
                    points_by_fare_names[fare_name] = {
                        "points": int(points),
                        "fare_brand_name": fare_brand_name,
                        "cash_fee": CashFee(
                            amount=float(amount),
                            currency=currency,
                        ),
                    }
                except Exception as e:
                    logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return points_by_fare_names

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: CabinClass = CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        driver = False
        try:
            
            url = f'https://www.jetblue.com/booking/flights?from={origin}&to={destination}&depart={departure_date.isoformat()}&isMultiCity=false&noOfRoute=1&lang=en&adults={adults}&children=0&infants=0&sharedMarket=false&roundTripFaresFlag=false&usePoints=true'

            # token = self.signin()
            # HEADERS.update({"Authorization": f'Bearer {token}'})
            driver = self.setup_driver(use_selenium_wire=True)
            # driver.get(STARTER_URL)
            time.sleep(1)
            driver.get(url)


            logger.info(f"{self.AIRLINE.value}: Making Multilogin calls...")
            for request in driver.requests:
                if request.response:
                    print(
                        request.url,
                        request.response.status_code,
                    )
            request = driver.wait_for_request('https://jbrest.jetblue.com/lfs-rwb/outboundLFS', timeout=60)

            response = request.response
            response_body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
            self.intercepted_response = json.loads(response_body)

            logger.info(f"{self.AIRLINE.value}: Got Multilogin response: count: {len(self.intercepted_response)}")

            if not self.intercepted_response:
                raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

            if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
            
            crawler_cabin_classes = []

            if cabin_class == c.CabinClass.All:
                crawler_cabin_classes = [
                    c.CabinClass.Economy,
                    # c.CabinClass.PremiumEconomy,
                    c.CabinClass.Business,
                    # c.CabinClass.First
                ]
            else:
                # since B6 doesn't have cabin_class code for for PremiumEconomy and First, so we will
                # use PremiumEconomy = Economy and First = Business
                if cabin_class == c.CabinClass.PremiumEconomy:
                    cabin_class = c.CabinClass.Economy
                if cabin_class == c.CabinClass.First:
                    cabin_class = c.CabinClass.Business
                    
                crawler_cabin_classes = [cabin_class]
            
            flight_search_results = self.intercepted_response["itinerary"]
            currency = self.intercepted_response["currency"]
            # aircrafts = self.intercepted_response["dictionaries"]["aircraft"]
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
            for index, flight_search_result in enumerate(flight_search_results):
                logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

                for cabin_item in crawler_cabin_classes:
                    points_by_fare_names = self.extract_sub_classes_points(flight_search_result, currency, cabin_item)
                    print(points_by_fare_names)
                    if not points_by_fare_names:
                        continue

                    try:
                        segments = self.extract_flight_detail(flight_search_result)
                    except Exception as e:
                        raise e
                    duration = flight_search_result["duration"]
                    for fare_name, points_and_cash in points_by_fare_names.items():
                        if not segments:
                            continue
                        flight = Flight(
                            airline=str(self.AIRLINE.value),
                            origin=segments[0].origin,
                            destination=segments[-1].destination,
                            cabin_class=str(cabin_item.value),
                            fare_brand_name = points_and_cash["fare_brand_name"],
                            airline_cabin_class=fare_name,
                            points=points_and_cash["points"],
                            cash_fee=points_and_cash["cash_fee"],
                            segments=segments,
                            duration=duration,
                        )
                        yield flight

        except (LiveCheckerException, Exception) as e:
            raise e

        finally:
            logger.info(f"{self.AIRLINE.value}: closing driver")
            if driver:
                driver.quit()

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        try:
            print(">>>>>>>>>>>>>>")
            start_time = time.perf_counter()
            crawler = JetBlueMultiloginCrawler()
            # departure_date = datetime.date.today() + datetime.timedelta(days=14)
            departure_date = datetime.date(year=2024, month=11, day=15)

            flights = list(
                crawler.run(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date.isoformat(),
                    cabin_class=cabin_class,
                )
            )
            end_time = time.perf_counter()

            print(flights)

            if flights:
                with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                    json.dump([asdict(flight) for flight in flights], f, indent=2)
            else:
                print("No result")
            print(f"It took {end_time - start_time} seconds.")
        except Exception as e:
            print(f">>>>>>>>>>>> e:{e}")

    # run("CDG", "NYC", c.CabinClass.Economy)
    run("JFK", "AUS", c.CabinClass.All)
    # run("JFK", "CDG", c.CabinClass.Economy)