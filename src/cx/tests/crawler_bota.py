import datetime
import logging
import random
import hashlib
import time
import socket
import os
import json
from typing import Iterator, List, Optional, Tuple, Dict
from lxml import etree, html

import traceback
import requests
from src import constants as c
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, AirportNotSupported, NoSearchResult
from src.schema import CashFee, Flight, FlightSegment
from src.cx.constants import CabinClassCodeMapping
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
from botasaurus.browser import browser, Driver
from botasaurus.user_agent import UserAgent
from botasaurus.window_size import WindowSize


DISABLE_LOGGERS = [
    "seleniumwire.server",
    "hpack.hpack",
    "hpack.table",
    "seleniumwire.handler",
    "selenium.webdriver.remote.remote_connection"
]
for thirdparty_logger in DISABLE_LOGGERS:
    logging.getLogger(thirdparty_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


from selenium import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from seleniumwire import webdriver as webdriversw  # Import from seleniumwire
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.common.keys import Keys
from botasaurus_driver import Driver

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
WEB_RTC_PATH = os.path.join(BASE_DIR, "webrtc_addon")


class ProxyExtension:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Odynn Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %d
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        self._proxy = {
            'host': host,
            'port': port,
            'user': user,
            'password': password
        }
        self._dir = os.path.normpath(tempfile.mkdtemp())

        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    @property
    def proxy(self):
        return self._proxy

    def __del__(self):
        shutil.rmtree(self._dir)
    
class CathayPacificMultiloginCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.CathayPacific
    HOME_PAGE_URL = "https://www.cathaypacific.com/cx/en_US.html"
    

    @staticmethod
    def human_typing(element: WebElement, text: str, speed=(0.2, 0.5)):
        for character in text:
            time.sleep(random.uniform(*speed))
            element.send_keys(character)

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_data in enumerate(flight_data["segments"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                segment_origin = segment_data["originLocation"].split('_')[-1]
                segment_destination = segment_data["destinationLocation"].split('_')[-1]
                segment_departure = segment_data["flightIdentifier"]["originDate"]
                segment_departure_datetime = datetime.datetime.fromtimestamp(segment_departure/1000, tz=datetime.timezone.utc)
                segment_arrival = segment_data["destinationDate"]
                segment_arrival_datetime = datetime.datetime.fromtimestamp(segment_arrival/1000, tz=datetime.timezone.utc)
                segment_aircraft = segment_data["flightIdentifier"]["marketingAirline"]
                segment_carrier = segment_data["flightIdentifier"]["marketingAirline"]
                segment_flight_number = segment_data["flightIdentifier"]["flightNumber"]
                segment_duration = duration_isoformat(segment_arrival_datetime - segment_departure_datetime)

                connection_time = None
                if (segment_index + 1) < len(flight_data["segments"]):
                    next_segment = flight_data["segments"][segment_index + 1]
                    next_segment_departure = next_segment["flightIdentifier"]["originDate"]
                    connection_time = duration_isoformat(datetime.datetime.fromtimestamp(next_segment_departure/1000, tz=datetime.timezone.utc) - segment_arrival_datetime)

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
                        duration=segment_duration,
                        layover_time=connection_time
                    )
                )
            
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def parse_flights(self, driver, cabin_class: str):
        # page_content = driver.page_source

        # Temporary Content Start
        page_content_file = 'search_content_LAX_JFK_ECO_1015.html'
        page_content_file = 'search_content_LHR_SEA_ECO_1114.html'
        page_content_file = 'search_content_IAD_CDG_BUS_1206.html'

        with open(page_content_file, 'r', encoding='utf-8') as f:
            page_content = f.read()
        # Temporary Content End

        html_dom = html.fromstring(page_content)

        flight_json_data = {}
        meta_script_ele = html_dom.xpath('//script[@type="text/javascript"][contains(text(), "staticFilesPath =")]')
        if meta_script_ele:
            meta_json = meta_script_ele[0].text
            meta_json = meta_json.split('pageBom =')[1].split('pageTicket =')[0].strip(' ;')
            meta_data = json.loads(meta_json)

            bounds = meta_data.get('modelObject', {}).get('availabilities', {}).get('upsell', {}).get('bounds', [])
            if bounds:
                flights = bounds[0].get('flights', [])

                for flight in flights:
                    if len(flight["segments"]) == 1:
                        flight_id = flight["segments"][0]["flightIdentifier"]["marketingAirline"] + flight["segments"][0]["flightIdentifier"]["flightNumber"]
                    else:
                        first_flight = flight["segments"][0]["flightIdentifier"]
                        last_flight = flight["segments"][-1]["flightIdentifier"]
                        flight_id = first_flight["marketingAirline"] + first_flight["flightNumber"] + '_' + last_flight["marketingAirline"] + last_flight["flightNumber"]

                    flight_json_data[flight_id] = flight
        
        if flight_json_data:
            flight_rows = html_dom.xpath('//div[contains(@class, "col-select-flight-wrap")]/div[contains(@class, "row-flight-card")][@data-flight-name]')
            if flight_rows:
                for flight_row in flight_rows:
                    flight_id = flight_row.xpath('./@data-flight-name')[0]
                    points_ele = flight_row.xpath('.//div[contains(@class, "col-flight-pricing")]/span[contains(@class, "am-total")]')
                    if points_ele:
                        points = points_ele[0].text
                        if flight_id in flight_json_data:
                            flight_json_data[flight_id]["points"] = points
                        else:
                            print('Flight {} not found in flight data'.format(flight_id))

            logger.info(f"{self.AIRLINE.value}: Found {len(flight_json_data)} flights...")
            for index, flight_search_result in enumerate(flight_json_data.values()):
                logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

                try:
                    segments = self.extract_flight_detail(flight_search_result)
                except Exception as e:
                    raise e
                
                duration_s = flight_search_result["duration"] / 1000
                
                if not segments:
                    continue
                flight = Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=str(cabin_class.value),
                    airline_cabin_class=CabinClassCodeMapping[cabin_class],
                    points=int(flight_search_result.get('points', '0').replace(',', '')),
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration_s)),
                )
                yield flight

        else:
            print('No flights found')

    def scrape_heading_task(self):
        WEB_RTC_PATH = os.path.join(BASE_DIR, "webrtc_addon")
        driver = Driver(
            proxy="http://ihgproxy1:ihgproxy1234_country-us@geo.iproyal.com:12321",
            arguments=[f"--load-extension={WEB_RTC_PATH}"]
        )
    
        print(f">>>>>>>>>>>>.... driver: {driver}")
        # driver.get("https://pixelscan.net")
        # time.sleep(120)
        return driver

    # "user": "ihgproxy1",
    # "pwd": "ihgproxy1234_country-us",
    # "ip": "geo.iproyal.com",
    # "port": "12321",    
    def login(self, driver):
        try:
            signin_email = 'zachburau@gmail.com'
            signin_password = 'Mgoblue16!'
            signin_url = 'https://www.cathaypacific.com'
            driver.get(signin_url)
            time.sleep(5)
            print(">>>>>>>>>>>>>>>>>>>")
            signin_url = 'https://www.cathaypacific.com/cx/en_US/sign-in.html'
            driver.get(signin_url)

            signin_option_btn_xpath = '//div[@class="signIn"]//button[@class="button -secondary"]'
            driver.wait_for_element(signin_option_btn_xpath, c.HIGH_SLEEP)

            email_signin_btn_xpath = '//div[@class="signIn"]//span[@class="button__label"][contains(text(), "with email")]'
            email_signin_btn = driver.select(email_signin_btn_xpath)
            print(f">email_signin_btn:{email_signin_btn}")
            if email_signin_btn:
                email_signin_btn.run_js("arguments[0].click();")
                time.sleep(1)

            email_input_xpath = '//div[@class="signIn"]//input[@name="email"]'
            email_input = driver.select(email_input_xpath)
            # email_input.click()
            # time.sleep(1)
            # email_input.send_keys(Keys.CONTROL, "a")
            # driver.type(email_input, signin_email) 
            # time.sleep(1)

            # password_input_xpath = '//div[@class="signIn"]//input[@name="password"]'
            # password_input = WebDriverWait(driver, 5).until(
            #     ec.element_to_be_clickable(
            #         (By.XPATH, password_input_xpath)
            #     )
            # )
            # password_input.click()
            # time.sleep(1)
            # password_input.send_keys(Keys.CONTROL, "a")
            # password_input.send_keys(signin_password)
            # # password_input.write(signin_password)
            # time.sleep(1)

            # signin_btn_xpath = '//div[@class="signIn"]//button[@class="button -primary"]'
            # signin_btn = WebDriverWait(driver, 5).until(
            #     ec.element_to_be_clickable(
            #         (By.XPATH, signin_btn_xpath)
            #     )
            # )
            # # driver.execute_script("arguments[0].click();", signin_btn)
            # time.sleep(2)
            # signin_btn.click()
            # time.sleep(2)

        except TimeoutException:
            print("TimeoutException")
        except:
            traceback.print_exc()
            
    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: CabinClass = CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        try:
            driver = self.scrape_heading_task()
            self.login(driver)
            # for flight in self.parse_flights(driver, cabin_class):
            #     yield flight

        except (LiveCheckerException, Exception) as e:
            raise e

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class, departure_date):
        start_time = time.perf_counter()
        crawler = CathayPacificMultiloginCrawler()

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

    # run("LHR", "SEA", c.CabinClass.Economy, datetime.date(year=2024, month=11, day=14))
    # run("LAX", "JFK", c.CabinClass.Economy, datetime.date(year=2024, month=10, day=15))
    run("IAD", "CDG", c.CabinClass.Business, datetime.date(year=2024, month=12, day=6))
