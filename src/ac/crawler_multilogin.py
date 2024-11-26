import datetime
import logging
import random
import hashlib
import time
import socket
import json
from typing import Iterator, List, Optional, Tuple, Dict

import requests
from src import constants as c
from src.base import MultiLoginAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException
from src.schema import CashFee, Flight, FlightSegment
from src.ac.constants import (
    AirlineCabinClassCodeMapping,
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
from src.exceptions import NoSearchResult, AirlineCrawlerException

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

from src.db import insert_target_headers

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


class AirCanadaMultiloginCrawler(MultiLoginAirlineCrawler):
    AIRLINE = Airline.AirCanada
    # QUICK_PROFILES_MLX_LAUNCHER = "https://launcher.mlx.yt:45001/api/v3/profile/quick"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TARGET = 'aircanada'
        profile = db.get_multilogin_profile()
        self.PROFILE_ID = profile.get("profile_id")
        self.FOLDER_ID = profile.get("folder_id")
        browser_type = profile.get("browser")
        logger.info(f'browser: {browser_type}')
        logger.info(f'PROFILE ID: {self.PROFILE_ID}')
        self.OPTIONS = ChromiumOptions() if browser_type == 'chrome' else FirefoxOptions()
   
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

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-ca",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }

    def setup_driver(self, use_selenium_wire=False):
        def interceptor(request):
            # Block PNG, JPEG and GIF images
            logger.info(f">>>>>request.path: {request.path}")
            if request.path.endswith(('.png', '.jpg', '.gif', '.css', '.svg')):
                request.abort()
            for block_url in self.BLOCK_URLS:
                if block_url in request.url:
                    request.abort()
                
        proxy = self.get_proxy()
        PROXY_HOST = proxy.get('ip')  # rotating proxy or host
        PROXY_PORT = int(proxy.get('port'))  # port
        PROXY_USER = proxy.get('user')  # username
        PROXY_PASS = proxy.get('pwd')  # password
        OS_TYPES = random.choice(['windows', 'macos'])

        browser_type = random.choice([
                                    'stealthfox',
                                    # 'mimic'
                                    ])

        mask_natural = random.choice(["mask", "real"])
        real_noise = random.choice(["real", "noise"])

        quick_payload = {
            "browser_type": browser_type,
            "name": "quick_profile",
            "os_type": OS_TYPES,
            "automation": "selenium",
            "proxy": {
                    "host": PROXY_HOST,
                    "type": "http",
                    "port": PROXY_PORT,
                    "username": PROXY_USER,
                    "password": PROXY_PASS
                },
            "parameters": {
                "fingerprint": {},
                "flags": {
                    "audio_masking": "mask",
                    "fonts_masking": "mask",
                    "geolocation_masking": "mask",
                    "geolocation_popup": "prompt",
                    "graphics_masking": "mask",
                    "graphics_noise": "mask",
                    "localization_masking": "mask",
                    "media_devices_masking": "mask",
                    "navigator_masking": "mask",
                    "ports_masking": "mask",
                    "screen_masking": "mask",
                    "timezone_masking": "mask",
                    "webrtc_masking": "mask",
                    "proxy_masking": "custom"
                    },
                "storage": {
                    "is_local": False,
                    "save_service_worker": True
                    },
                }
            }
        logger.info(f">>> Calling quick profile with header: {self.quick_header}")
        response = requests.post(url=self.QUICK_PROFILES_MLX_LAUNCHER, headers=self.quick_header,json=quick_payload)
        
        if response.status_code != 200:
            logger.error(f">>> Calling quick profile error: {response.text}")
            
        profile_port = response.json()["data"]["port"]
        self.profile_id = response.json()["data"]["id"]
        if browser_type == 'mimic':
            options = ChromiumOptions()
            # options.add_argument('--incognito')
        else:
            options = FirefoxOptions()
            if use_selenium_wire:
                options.set_preference('network.proxy.allow_hijacking_localhost', True)
            
        if use_selenium_wire:
            sw_address = socket.gethostbyname(socket.gethostname())
            sw_port = get_random_port()
            sw_options = {
                "auto_config": False,
                "addr": sw_address,
                "port": sw_port,
                'disable_encoding': True,
                "request_storage_base_dir": "/tmp",  # Use /tmp to store captured data
                'mitm_http2': False,
                'proxy': {
                    'http': 'http://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321',
                    'https': 'https://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321',
                    'no_proxy': 'localhost,127.0.0.1'
                }
            }

            proxy = f"{sw_address}:{sw_port}"
            print(f">>>>>>> proxy: {proxy}")
            firefox_capabilities = webdriversw.DesiredCapabilities.FIREFOX
            firefox_capabilities['marionette'] = True
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": proxy,
                "sslProxy": proxy
            }
            driver = webdriversw.Remote(
                command_executor=f'http://127.0.0.1:{profile_port}',
                options=options,
                desired_capabilities=firefox_capabilities,
                # desired_capabilities=self.OPTIONS.to_capabilities(),
                seleniumwire_options=sw_options
            )

            driver.request_interceptor = interceptor
            return driver
        # Instantiate the remote webdriver with the quick profile port
        driver = wd.Remote(command_executor=f'http://127.0.0.1:{profile_port}', options=options)
        return driver
    
    def extract_flight_detail(
        self,
        flight_data: Dict,
        flight_dictionaries: Dict,
        aircrafts: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["boundDetails"]["segments"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                flight_id = segment_element["flightId"]
                connection_time = segment_element.get("connectionTime", 0)
                flight_dictionary = flight_dictionaries.get(flight_id, None)

                if flight_dictionary:
                    segment_origin = flight_dictionary["departure"]["locationCode"]
                    segment_destination = flight_dictionary["arrival"]["locationCode"]
                    segment_departure_datetime = flight_dictionary["departure"]["dateTime"].replace("Z","+00:00")
                    segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                    segment_arrival_datetime = flight_dictionary["arrival"]["dateTime"].replace("Z","+00:00")
                    segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                    aircraft_id = flight_dictionary["aircraftCode"]
                    segment_aircraft = aircrafts.get(aircraft_id, None)
                    segment_carrier = flight_dictionary["marketingAirlineCode"]
                    segment_flight_number = flight_dictionary["marketingFlightNumber"]
                    if not segment_carrier:
                        segment_carrier = flight_dictionary.get("operatingAirlineName", None)
                    segment_duration = flight_dictionary["duration"]

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
        self, flight_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        cabin_class_code = CabinClassCodeMappingForHybrid[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        for air_bound in flight_data["airBounds"]:
            if c.CabinClass.Economy == cabin_class:
                continue_flag = all(
                    [
                        cabin_class_code == air_bound_availability["cabin"]
                        for air_bound_availability in air_bound["availabilityDetails"]
                    ]
                )
            else:
                continue_flag = any(
                    [
                        cabin_class_code == air_bound_availability["cabin"]
                        for air_bound_availability in air_bound["availabilityDetails"]
                    ]
                )

            if continue_flag:
                try:
                    fare_name = AirlineCabinClassCodeMapping[air_bound["fareFamilyCode"]]

                    points = air_bound["airOffer"]["prices"]["milesConversion"]["convertedMiles"]["base"]
                    amount = air_bound["airOffer"]["prices"]["totalPrices"][0]["total"]
                    if amount:
                        amount = round(amount / 100)
                    currency = air_bound["airOffer"]["prices"]["totalPrices"][0]["currencyCode"]
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
            url = (
                f'https://www.aircanada.com/aeroplan/redeem/availability/outbound?org0={origin}'
                f'&dest0={destination}&departureDate0={departure_date.isoformat()}&lang=en-CA&tripType=O&ADT={adults}&YTH=0&CHD=0&INF=0&INS=0&marketCode=INT'
            )

            token = self.signin()
            HEADERS.update({"Authorization": f'Bearer {token}'})
            # driver = self.start_profile()
            driver = self.setup_driver(use_selenium_wire=True)
            # driver.get(STARTER_URL)
            time.sleep(1)
            driver.get(url)

            if "Access Denied" in driver.page_source:
                raise AirlineCrawlerException(self.AIRLINE, "Access Denied")
            
            logger.info(f"{self.AIRLINE.value}: Making Multilogin calls...")
            request = driver.wait_for_request('/v2/search/air-bounds', timeout=300)

            response = request.response
            all_headers = {key:val for key, val in request.headers.items()}
            payload = json.loads(decode(request.body, 'utf-8'))
            insert_target_headers(all_headers, self.TARGET, payload)
            response_body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
            self.intercepted_response = json.loads(response_body)
            logger.info(f"{self.AIRLINE.value}: Got Multilogin response: count: {len(self.intercepted_response)}")

            if not self.intercepted_response:
                raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

            if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

            flight_search_results = self.intercepted_response["data"]["airBoundGroups"]
            flight_dictionaries = self.intercepted_response["dictionaries"]["flight"]
            aircrafts = self.intercepted_response["dictionaries"]["aircraft"]
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
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
                
                
            for index, flight_search_result in enumerate(flight_search_results):
                logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")
                for extract_cabin_class in all_cabins:
                    points_by_fare_names = self.extract_sub_classes_points(flight_search_result, extract_cabin_class)
                    if not points_by_fare_names:
                        continue

                    try:
                        segments = self.extract_flight_detail(flight_search_result, flight_dictionaries, aircrafts)
                    except Exception as e:
                        raise e
                    duration = flight_search_result["boundDetails"]["duration"]
                    for fare_name, points_and_cash in points_by_fare_names.items():
                        if not segments:
                            continue
                        flight = Flight(
                            airline=str(self.AIRLINE.value),
                            origin=segments[0].origin,
                            destination=segments[-1].destination,
                            cabin_class=str(extract_cabin_class.value),
                            airline_cabin_class=fare_name,
                            points=points_and_cash["points"],
                            cash_fee=points_and_cash["cash_fee"],
                            segments=segments,
                            duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                        )
                        yield flight

        except (LiveCheckerException, Exception) as e:
            raise e

        finally:
            if driver:
                logger.info(f"{self.AIRLINE.value}: closing driver")
                driver.quit()
                self.quit_driver()
                # self.stop_profile()

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AirCanadaMultiloginCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=23)

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

    # run("PVG", "ICN", c.CabinClass.Economy)
    # run("JFK", "LHR", c.CabinClass.Economy)
    # run("LAX", "YYZ", c.CabinClass.PremiumEconomy)
    run("JFK", "LHR", c.CabinClass.All)