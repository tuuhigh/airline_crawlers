import datetime
import logging
import random
import hashlib
import socket
import time
from typing import Dict, Iterator, List, Optional, Tuple
import re

import requests
from bs4 import BeautifulSoup

from src import constants as c
from src.exceptions import NoSearchResult
from src.base import MultiLoginAirlineCrawler
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException
from src.schema import CashFee, Flight, FlightSegment
from src.ua.constants import CabinClassCodeMapping, CabinClassZenrowsCodeMapping
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    parse_time,
    get_random_port,
)
from isodate import duration_isoformat
from src import db

logger = logging.getLogger(__name__)

from selenium import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
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


class UnitedAirlineMultiloginWireCrawler(MultiLoginAirlineCrawler):
    AIRLINE = Airline.UnitedAirline

    def __init__(self):
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
        def interceptor(request):
            # Block PNG, JPEG and GIF images
            if request.path.endswith(('.png', '.jpg', '.gif')):
                request.abort()
            for block_url in self.BLOCK_URLS:
                if block_url in request.url:
                    request.abort()
                    
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
                'proxy': {
                    'http': 'http://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321',
                    'https': 'https://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321',
                    'no_proxy': 'http://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321'
                }
            }
            print(f">>>>>>> {self.OPTIONS}")
            options = self.OPTIONS

            proxy = PROXY = f"{sw_address}:{sw_port}"
            print(f">>>>>>> proxy: {proxy}")

            firefox_capabilities = webdriversw.DesiredCapabilities.FIREFOX
            firefox_capabilities['marionette'] = True
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": proxy,
                "sslProxy": proxy
            }

            driver = webdriversw.Remote(
                command_executor=f'{LOCALHOST}:{selenium_port}',
                options=options,
                desired_capabilities=firefox_capabilities,
                seleniumwire_options=sw_options
            )
            driver.request_interceptor = interceptor
            return driver

    def stop_profile(self) -> None:
        r = requests.get(f'{MLX_LAUNCHER}/profile/stop/p/{self.PROFILE_ID}', headers=HEADERS)

        if(r.status_code != 200):
            logger.info(f'\nError while stopping profile: {r.text}\n')
        else:
            logger.info(f'\nProfile {self.PROFILE_ID} stopped.\n')


    @staticmethod
    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        # logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
        flight_segments: List[FlightSegment] = []
        
        first_connection_time = 0
        try:
            first_layover_min = flight_data["Connections"][0]["ConnectTimeMinutes"]
            if first_layover_min:
                first_connection_time = first_layover_min * 60
        except:
            pass

        first_segment_origin = flight_data["Origin"]
        first_segment_destination = flight_data["Destination"]
        first_segment_departure_datetime = flight_data["DepartDateTime"]
        first_segment_departure_datetime = datetime.datetime.fromisoformat(first_segment_departure_datetime)
        first_segment_arrival_datetime = flight_data["DestinationDateTime"]
        first_segment_arrival_datetime = datetime.datetime.fromisoformat(first_segment_arrival_datetime)
        first_segment_aircraft = flight_data["EquipmentDisclosures"]["EquipmentDescription"]
        first_segment_carrier = flight_data["MarketingCarrier"]
        first_segment_flight_number = flight_data["OriginalFlightNumber"]
        first_duration_min = flight_data["TravelMinutes"]
        first_segment_duration = 60 * first_duration_min

        flight_segments.append(
            FlightSegment(
                origin=first_segment_origin,
                destination=first_segment_destination,
                departure_date=first_segment_departure_datetime.date().isoformat(),
                departure_time=first_segment_departure_datetime.time().isoformat()[:5],
                departure_timezone="",
                arrival_date=first_segment_arrival_datetime.date().isoformat(),
                arrival_time=first_segment_arrival_datetime.time().isoformat()[:5],
                arrival_timezone="",
                aircraft=first_segment_aircraft,
                flight_number=first_segment_flight_number,
                carrier=first_segment_carrier,
                duration=duration_isoformat(datetime.timedelta(seconds=first_segment_duration)),
                layover_time=duration_isoformat(datetime.timedelta(seconds=first_connection_time))
                if first_connection_time
                else None,
            )
        )
        
        for segment_index, segment_element in enumerate(flight_data["Connections"]):
            try:
                connection_time = 0
                try:
                    layover_min = flight_data["Connections"][segment_index + 1]["ConnectTimeMinutes"]
                    if layover_min:
                        connection_time = layover_min * 60
                except:
                    pass
                    
                segment_origin = segment_element["Origin"]
                segment_destination = segment_element["Destination"]
                segment_departure_datetime = segment_element["DepartDateTime"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment_element["DestinationDateTime"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                segment_aircraft = segment_element["EquipmentDisclosures"]["EquipmentDescription"]
                segment_carrier = segment_element["MarketingCarrier"]
                segment_flight_number = segment_element["OriginalFlightNumber"]

                # duration_day = segment_element["totalAirTime"]["day"]
                duration_min = segment_element["TravelMinutes"]
                segment_duration = 60 * duration_min

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
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Classes points...")
        cabin_class_code = CabinClassCodeMapping[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}
        
        fare_name = CabinClassZenrowsCodeMapping[cabin_class]
        
        points_by_fare_names[fare_name] = {
            "points": -1,
            "cash_fee": CashFee(
                amount=0,
                currency="",
            ),
        }
        
        for sub_class in flight_data['Products']:
            if sub_class['ProductType'] == cabin_class_code:
                try:
                    points = sub_class['Prices'][0]['Amount']
                    amount = sub_class['Prices'][1]['Amount']
                    currency = sub_class['Prices'][1]['Currency']
                    points_by_fare_names[fare_name] = {
                        "points": points,
                        "cash_fee": CashFee(
                            amount=amount,
                            currency=currency,
                        ),
                    }
                except:
                    pass
                break

        return points_by_fare_names
    
    def click_show_more_button(self, driver):
        try: 
            show_more_button=f"//button[@class='atm-c-btn atm-c-btn--primary atm-c-btn--block']"
            element = driver.find_element(By.XPATH, show_more_button)
            driver.execute_script("arguments[0].click();", element)
            
            identifier=f"//button[@class='atm-c-btn atm-c-btn--primary atm-c-btn--block']/span[contains(text(), 'Show fewer flights')]"
            WebDriverWait(driver, c.DEFAULT_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        except (NoSuchElementException, TimeoutException):
            pass

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
                f"https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&"
                f"d={departure_date.isoformat()}&tt=1&at=1&sc=7&px={adults}&taxng=1&newHP=True&clm=7&st=bestmatches&tqp=A"
            )
            token = self.signin()
            HEADERS.update({"Authorization": f'Bearer {token}'})
            driver = self.start_profile()
            # driver = self.setup_driver()
            # driver.get(STARTER_URL)
            time.sleep(1)
            driver.get(url)

            js_instruction_update_search = """
                var button = document.querySelector('[class="atm-c-btn atm-c-btn--secondary"]');

                // Check if the button exists
                if (button) {
                    // Trigger a click event on the button
                    button.click();
                } else {
                    console.error("Button not found");
                }
            """

            time.sleep(3)
            try:
                for i in range(3):
                    # Check if the error alert element is present
                    logger.info(f"attempt #{i+1}")
                    error_alert = driver.find_element(By.XPATH, '//div[@class="atm-c-alert atm-c-alert--error"]')
                    logger.info("Error alert found!")
                    driver.execute_script(js_instruction_update_search)
                    logger.info('updated search')
                    time.sleep(3)

            except NoSuchElementException:
                logger.info("Error alert not found.")

            logger.info(f"{self.AIRLINE.value}: Making Multilogin calls...")
            request = driver.wait_for_request('/api/flight/FetchFlights', timeout=60)

            response = request.response
            response_body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
            self.intercepted_response = json.loads(response_body)
            logger.info(f"{self.AIRLINE.value}: Got Multilogin response: count: {len(self.intercepted_response)}")

            if not self.intercepted_response:
                raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

            if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
            
            flight_search_results = self.intercepted_response['data']['Trips'][0]['Flights']
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")

            for index, flight_search_result in enumerate(flight_search_results):
                logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")
                
                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_class)
                if not points_by_fare_names:
                    continue
        
                try:
                    segments = self.extract_flight_detail(self, flight_search_result)
                except Exception as e:
                    raise e
                
                duration = flight_search_result["TravelMinutesTotal"]
                duration_s = duration * 60
                for fare_name, points_and_cash in points_by_fare_names.items():
                    if not segments:
                        continue
                    flight = Flight(
                        airline=str(self.AIRLINE.value),
                        origin=segments[0].origin,
                        destination=segments[-1].destination,
                        cabin_class=str(cabin_class.value),
                        airline_cabin_class=fare_name,
                        points=points_and_cash["points"],
                        cash_fee=points_and_cash["cash_fee"],
                        segments=segments,
                        duration=duration_isoformat(datetime.timedelta(seconds=duration_s)),
                    )
                    yield flight
            
        except (LiveCheckerException, Exception) as e:
            raise e

        finally:
            if driver:
                driver.quit()

if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()

        crawler = UnitedAirlineMultiloginWireCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=9, day=23)
        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
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

    # run("ORD", "CDG", CabinClass.Economy, 1)
    # run("DFW", "JFK", CabinClass.Economy)
    # run("JFK", "LAX", CabinClass.Economy, 1)
    # run("SGN", "LAX", CabinClass.Economy, 1)
    run("HND", "JFK", CabinClass.Economy, 1)
    # run("EWR", "IAD", CabinClass.First, 1)
