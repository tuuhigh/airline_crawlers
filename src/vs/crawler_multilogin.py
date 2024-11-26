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
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, AirportNotSupported, NoSearchResult
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

DISABLE_LOGGERS = [
    # "seleniumwire.server",
    # "hpack.hpack",
    # "hpack.table",
    # "seleniumwire.handler"
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


class VirginAtlanticMultiloginCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.VirginAtlantic
    HOME_PAGE_URL = "https://www.virginatlantic.com/us/en"
    # HOME_PAGE_URL = "https://pixelscan.net/"

    # self.PROFILE_ID = "d1841620-8d12-4ac5-bde0-8f4e95bd9bc4"
    def __init__(self):
        profile = db.get_multilogin_profile_blocked_webrtc()
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

# vn.smartproxy.com:46001:spyc5m5gbs:puFNdLvkx6Wcn6h6p8
            proxy_user = "spyc5m5gbs"
            proxy_pass = "puFNdLvkx6Wcn6h6p8"
            proxy_host = "us.smartproxy.com"
            proxy_port = random.choice(range(10001,10010))
            proxy_address = f'{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'

            # proxy_user = "ihgproxy1"
            # proxy_pass = "ihgproxy1234_country-us"
            # proxy_host = "geo.iproyal.com"
            # proxy_port = "12321"
            # proxy_address = f'{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}'

            sw_options = {
                "auto_config": False,
                "addr": sw_address,
                "port": sw_port,
                'disable_encoding': True,
                "request_storage_base_dir": "/tmp",  # Use /tmp to store captured data,
                'proxy': {
                    'http': f"http://{proxy_address}",
                    'https': f"https://{proxy_address}"
                }
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

    @staticmethod
    def human_typing(element: WebElement, text: str, speed=(0.2, 0.5)):
        for character in text:
            time.sleep(random.uniform(*speed))
            element.send_keys(character)

    def _select_oneway(self, driver) -> None:
        identifier="//span[@aria-labelledby='selectTripType-label']"
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

        identifier="//ul[@id='selectTripType-desc']/li[@data='1']"
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

    def _select_miles(self, driver: WebDriver) -> None:
        identifier='//a[contains(@class, "icon-advsearchtriangle")]'
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        # element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.presence_of_element_located((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

        identifier='//label[@for="miles"]'
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

    def _select_origin(self, origin: str, driver) -> None:
        identifier="//a[@id='fromAirportName']"
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

        identifier="//input[@id='search_input']"
        origin_input = WebDriverWait(driver, c.LOW_SLEEP).until(ec.presence_of_element_located((By.XPATH, identifier)))
        origin_input.send_keys(Keys.CONTROL, "a")
        origin_input.clear()
        self.human_typing(origin_input, origin)

        time.sleep(c.LOW_SLEEP)
        try:
            identifier="//div[@class='search-result-container']//ul/li[contains(@class, 'airport-list')][1]/a"
            WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
            exact_identifier=f"//div[@class='search-result-container']//ul/li[contains(@class, 'airport-list')][1]/a[./span[contains(text(), '{origin}')]]"
            element = driver.find_element(By.XPATH, exact_identifier)
            driver.execute_script("arguments[0].click();", element)
        except (NoSuchElementException, TimeoutException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=origin)

    def _select_destination(self, destination: str, driver) -> None:
        identifier="//a[@id='toAirportName']"
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

        identifier="//input[@id='search_input']"
        destination_input = WebDriverWait(driver, c.LOW_SLEEP).until(ec.presence_of_element_located((By.XPATH, identifier)))
        destination_input.send_keys(Keys.CONTROL, "a")
        destination_input.clear()
        self.human_typing(destination_input, destination)

        time.sleep(c.LOW_SLEEP)

        try:
            identifier="//div[@class='search-result-container']//ul/li[contains(@class, 'airport-list')][1]/a"
            WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
            exact_identifier=f"//div[@class='search-result-container']//ul/li[contains(@class, 'airport-list')][1]/a[./span[contains(text(), '{destination}')]]"
            element = driver.find_element(By.XPATH, exact_identifier)
            driver.execute_script("arguments[0].click();", element)
        except (NoSuchElementException, TimeoutException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=destination)

    def _select_flexible_dates(self, driver) -> None:
        identifier='//input[@name="chkFlexDate"]'
        flexible_dates_checkbox = WebDriverWait(driver, c.LOW_SLEEP).until(ec.presence_of_element_located((By.XPATH, identifier)))
        if flexible_dates_checkbox.is_selected():
            print("Checkbox is selected")
            driver.execute_script("arguments[0].click();", flexible_dates_checkbox)

    def _select_date(self, departure_date: datetime.date, driver) -> None:
        departure_date_str = departure_date.strftime("%m/%d/%Y")
        identifier="//div[@id='input_departureDate_1' or @id='input_returnDate_1']"
        element = WebDriverWait(driver, c.MEDIUM_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

        identifier="//div[@class='calPrevNextBtnCont']/a[@aria-label='Next']"
        next_mon_btn = WebDriverWait(driver, c.LOW_SLEEP).until(ec.presence_of_element_located((By.XPATH, identifier)))

        while True:
            try:
                identifier=f"//table[@class='dl-datepicker-calendar']//td/a[contains(@data-date, '{departure_date_str}')]"
                element = WebDriverWait(driver, c.LOW_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
                driver.execute_script("arguments[0].click();", element)
                break
            except (TimeoutException, StaleElementReferenceException):
                driver.execute_script("arguments[0].click();", next_mon_btn)

    def accept_cookie(self, driver):
        try:
            identifier='//button[@id="privacy-btn-reject-all"]'
            element = WebDriverWait(driver, c.LOW_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
            driver.execute_script("arguments[0].click();", element)
        except TimeoutException:
            pass

    def _submit(self, driver) -> None:
        identifier="//button[@id='btnSubmit']"
        element = WebDriverWait(driver, c.HIGHEST_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)

    def _click_adv_search(self, driver) -> None:
        identifier="//a[@id='adv-search']"
        element = WebDriverWait(driver, c.HIGHEST_SLEEP).until(ec.element_to_be_clickable((By.XPATH, identifier)))
        driver.execute_script("arguments[0].click();", element)



    def search(self, driver, origin, destination, departure_date, cabin_class, adults):
        self.accept_cookie(driver)
        self._select_miles(driver)
        self._select_oneway(driver)
        self._select_origin(origin, driver)
        self._select_destination(destination, driver)
        self._select_date(departure_date, driver)
        self._select_flexible_dates(driver)
        # self._click_adv_search(driver)
        self._submit(driver)

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["trip"][0]["flightSegment"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")

                connection_time = 0
                layover = segment_element.get("layover", {})
                if layover:
                    layover_duration = layover.get('duration', {})
                    layover_hour = layover_duration.get('hour', 0)
                    layover_min = layover_duration.get('minute', 0)
                    connection_time = layover_hour * 3600 + layover_min * 60

                segment_origin = segment_element["originAirportCode"]
                segment_destination = segment_element["destAirportCode"]
                segment_departure_datetime = segment_element["schedDepartLocalTs"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment_element["schedArrivalLocalTs"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                segment_aircraft = segment_element["flightLeg"][0]["aircraft"]["fleetName"]
                segment_carrier = segment_element.get('marketingCarrier', {}).get('code', '')
                if not segment_carrier:
                    segment_carrier = segment_element.get('operatingCarrier', {}).get('code', '')
                segment_flight_number = segment_element.get('operatingFlightNum', '')
                if not segment_flight_number:
                    segment_flight_number = segment_element.get('operatingFlightNum', '')

                # duration_day = segment_element["totalAirTime"]["day"]
                duration_hour = segment_element["totalAirTime"]["hour"]
                duration_min = segment_element["totalAirTime"]["minute"]
                segment_duration = 3600 * duration_hour + 60 * duration_min

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

        for air_bound in flight_data["fare"]:
            try:
                if cabin_class_code != str(air_bound["fareId"]):
                    continue

                fare_name = AirlineCabinClassCodeMapping[str(air_bound["fareId"])]
                if air_bound["soldOut"]:
                    points_by_fare_names[fare_name] = {
                        "points": -1,
                        "cash_fee": CashFee(
                            amount=0,
                            currency="",
                        ),
                    }
                else:
                    points = air_bound["totalPrice"]["miles"]["miles"]
                    amount = air_bound["totalPrice"]["currency"]["formattedAmount"]
                    currency = air_bound["totalPrice"]["currency"]["code"]
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
        driver = None
        try:
            token = self.signin()
            HEADERS.update({"Authorization": f'Bearer {token}'})
            driver: WebDriver = self.start_profile()
            # driver.get(STARTER_URL)
            time.sleep(1)
            driver.get(self.HOME_PAGE_URL)

            # search submit
            self.search(driver, origin, destination, departure_date, cabin_class, adults)

            logger.info(f"{self.AIRLINE.value}: Making Multilogin calls...")
            request = driver.wait_for_request('/shop/ow/search', timeout=300)

            response = request.response
            response_body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
            self.intercepted_response = json.loads(response_body)
            logger.info(f"{self.AIRLINE.value}: Got Multilogin response: count: {len(self.intercepted_response)}")

            if not self.intercepted_response:
                raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

            if self.intercepted_response.get('shoppingError', {}).get('error', {}).get('message', ''):
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
            
            all_cabins = []             
            if cabin_class == c.CabinClass.All:
                all_cabins = [
                    c.CabinClass.Economy, 
                    c.CabinClass.PremiumEconomy, 
                    c.CabinClass.Business
                ]
            else:
                all_cabins = [cabin_class]

            flight_search_results = self.intercepted_response["itinerary"]
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
            for index, flight_search_result in enumerate(flight_search_results):
                logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

                for cabin_item in all_cabins:
                    points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_item)
                    if not points_by_fare_names:
                        continue

                    try:
                        segments = self.extract_flight_detail(flight_search_result)
                    except Exception as e:
                        raise e
                    # duration_day = flight_search_result["trip"][0]["totalTripTime"]["day"]
                    duration_hour = flight_search_result["trip"][0]["totalTripTime"]["hour"]
                    duration_min = flight_search_result["trip"][0]["totalTripTime"]["minute"]
                    duration = 3600 * duration_hour + 60 * duration_min

                    for fare_name, points_and_cash in points_by_fare_names.items():
                        if not segments:
                            continue
                        flight = Flight(
                            airline=str(self.AIRLINE.value),
                            origin=segments[0].origin,
                            destination=segments[-1].destination,
                            cabin_class=str(cabin_item.value),
                            airline_cabin_class=fare_name,
                            points=points_and_cash["points"],
                            cash_fee=points_and_cash["cash_fee"],
                            segments=segments,
                            duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                        )
                        yield flight

        except json.decoder.JSONDecodeError:
            print("Error: response_body is not valid JSON data")
            print(response_body)
        except (LiveCheckerException, Exception) as e:
            raise e
        finally:
            if driver:
                driver.quit()
            self.stop_profile()

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = VirginAtlanticMultiloginCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=7, day=24)

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

    run("IAD", "AMD", c.CabinClass.Economy)
    # run("PVG", "ICN", c.CabinClass.Economy)
    # run("JFK", "LHR", c.CabinClass.PremiumEconomy)
    # run("LAX", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Economy)