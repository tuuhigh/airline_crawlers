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
import random
from scrapy import Selector
import subprocess
import platform

from playwright.sync_api import Locator, Page
from curl_cffi import requests as crequests
import requests
from src import constants as c
from src.tk.constants import CabinClassCodeMapping, supported_airports
from src.exceptions import NoSearchResult, LoginFailed
from src.playwright.base import PlaywrightBaseAirlineCrawler
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

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TurkishAirlineCredentials = c.Credentials[c.Airline.Turkish]

# we can also block popular 3rd party resources like tracking and advertisements.
BLOCK_RESOURCE_NAMES = [
    'adzerk',
    'analytics',
    'twitter',
    'doubleclick',
    'exelator',
    'facebook',
    'fontawesome',
    # 'google.com',
    'google-analytics',
    'googletagmanager',
    "tiktok",
    #new
    'openh264',
    'adobedtm',
    'adobetarget',
    'mozilla.net',
    'mozilla.com',
    'bing',
    'pisano.com'
]

class TurkishPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.Turkish
    REQUIRED_LOGIN = True
    HOME_PAGE_URL = "https://www.turkishairlines.com/en-us/miles-and-smiles/book-award-tickets"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered
    BLOCK_RESOURCE = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._compute_latest_user_data_dir()
        self.intercepted = False
        self.credentials: List[c.AirlineCredential] = TurkishAirlineCredentials.copy()
        self.intercepted_response = None

    def __del__(self):
        self._clean_outdate_user_data_dir()

    def _copytree(self, src, dst):
        if platform.system() == 'Windows':
            subprocess.run(['robocopy', src, dst, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/nc', '/ns', '/np'],
                           shell=True)
        else:
            subprocess.run(['cp', '-a', src, dst])

    def _compute_latest_user_data_dir(self):
        """
        check if exist last user_data_dir belong to current user,
        if yes, clone this user_data_dir into new dir to keep last sesion session
        if no, return new latest empty dir
        """
        utc_now = datetime.datetime.utcnow().isoformat()
        pattern = re.sub("[@.:]", "-", f"user_data_dir_{self.username}*")
        user_data_dir_pattern = os.path.join(BASE_DIR, pattern)

        user_data_name = f"user_data_dir_{self.username}_{utc_now}"
        user_data_name = re.sub("[@.:]", "-", user_data_name)
        new_user_data_dir = os.path.join(BASE_DIR, user_data_name)
        # logger.info(f"new_user_data_name: {new_user_data_dir}")

        all_user_data_dirs = glob.glob(user_data_dir_pattern)
        # logger.info(f"all_user_data_dirs: {all_user_data_dirs}")

        if all_user_data_dirs:
            latest_user_data_dir = max(all_user_data_dirs, key=os.path.getmtime)
            logger.info(f"found latest user_data_dir: {latest_user_data_dir}")
            self._copytree(latest_user_data_dir, new_user_data_dir)
            time.sleep(5)

        self._user_data_dir = new_user_data_dir

    def _clean_outdate_user_data_dir(self):
        """
        Clean up all user_data_dir, only keep the latest one
        only delete user_data_dir of folder
        older than 15 minutes avoid to delete running chrome windows.
        (Assumed that each window has maxiumum 15 minutes to complete)
        """
        user_data_dir = os.path.join(BASE_DIR, re.sub("[@.:]", "-", f"user_data_dir_{self.username}*"))

        all_user_data_dirs = glob.glob(user_data_dir)
        MAX_COMPLETE_TIME = 60 * 15
        now = time.time()
        if all_user_data_dirs:
            last_user_data_dir = max(all_user_data_dirs, key=os.path.getmtime)
            logger.info(f"> cleanup oudate user_data_dir except for latest one: " f"{last_user_data_dir}")
            for user_data_dir in all_user_data_dirs:
                try:
                    if user_data_dir == last_user_data_dir:
                        continue
                    if os.path.getmtime(user_data_dir) < now - MAX_COMPLETE_TIME:
                        logger.info(
                            f"> cleanup oudate folder older than {(MAX_COMPLETE_TIME/60)}m user_data_dir: "
                            f"{user_data_dir}"
                        )
                        shutil.rmtree(user_data_dir)
                except Exception:
                    pass

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-us",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }

    def _close_cookie_popup(self, page):
        try:
            cookie_accept_button = page.locator("button#allowCookiesButton")
            cookie_accept_button.wait_for(timeout=1000)
            cookie_accept_button.click()
            logger.info("clicked accept cookie popup")
        except Exception as e:
            logger.error(f"click accept cookie popup error: {e}")
            pass

    def _select_oneway(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.click("span#one-way")

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        origin_input = page.locator('input[id="fromPort"]')
        origin_input.click()
        time.sleep(1)
        self.human_typing(page, origin_input, origin, False)
        page.click(f'//span[contains(@class, "hm__style_booker-input-list-item-text__")]/span[contains(text(), "{origin}")]')

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        destination_input = page.locator('input[id="toPort"]')
        destination_input.click()
        time.sleep(1)
        self.human_typing(page, destination_input, destination, False)
        page.click(f'//span[contains(@class, "hm__style_booker-input-list-item-text__")]/span[contains(text(), "{destination}")]')

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        departure_day_str = str(departure_date.day)  # Convert day to string to remove leading zero
        departure_date_str = f"{departure_date.strftime('%B')} {departure_day_str}, {departure_date.year}"

        try:
            next_month_ele = page.locator('button.react-calendar__navigation__next-button')
            next_month_ele.wait_for(timeout=2000)
        except:
            calendar_input_ele = page.locator('xpath=//div[contains(@class, "hm__RoundAndOneWayTab_dateLabel__")]')
            calendar_input_ele.wait_for(timeout=2000)
            calendar_input_ele.click()
            time.sleep(1)

        # Go to the earliest available month
        while True:
            try:
                before_month_ele = page.locator('button.react-calendar__navigation__arrow.react-calendar__navigation__prev-button')
                before_month_ele.wait_for(timeout=2000)
                before_month_ele.click()
                time.sleep(1)
            except:
                break

        # Now click next month button until we find the departure date
        while True:
            try:
                calendar_date_ele = page.locator(f'xpath=//div[@class="react-calendar__month-view__days"]/button/abbr[@aria-label="{departure_date_str}"]')
                calendar_date_ele.wait_for(timeout=2000)
                calendar_date_ele.click()
                break
            except:
                next_month_ele = page.locator('button.react-calendar__navigation__next-button')
                next_month_ele.wait_for(timeout=2000)
                next_month_ele.click()
                time.sleep(1)

        ok_btn = page.locator(f'xpath=//button[contains(@class, "hm__BookerDateWrapper_button__")]')
        ok_btn.wait_for(timeout=5000)
        ok_btn.click()

    def _select_cabin_class(self, cabin_class: c.CabinClass.Economy, *args, **kwargs) -> None:
        if cabin_class == c.CabinClass.Economy:
            pass
        elif cabin_class == c.CabinClass.Business:
            page: Page = kwargs.get("page")
            business_cabin_ele = page.locator('xpath=//div[contains(@class, "hm__style_booker-pax-picker-dropdown-cabin-bus__")]//input[@name="cabin-type"]')
            business_cabin_ele.wait_for(timeout=2000)
            business_cabin_ele.click()

    @staticmethod
    def intercept_route(route):
        """intercept all requests and abort blocked ones"""
        if route.request.resource_type in c.BLOCK_RESOURCE_TYPES:
            # print(f'blocking background resource {route.request} blocked type "{route.request.resource_type}"')
            return route.abort()
        if any(key in route.request.url for key in BLOCK_RESOURCE_NAMES):
            # print(f"blocking background resource {route.request} blocked name {route.request.url}")
            return route.abort()
        return route.continue_()
    
    def intercept_request(self, route, request):

        if request.url.endswith('/api/v1/availability') and request.method == "POST" and not self.intercepted:
            route.continue_()
            try:
                self.intercepted = True
                response = request.response()
                response_body = response.json()
                status_code = response.status
                logger.info(f"{self.AIRLINE.value}: Response from {request.url}: Status Code - {status_code}")

                if response_body:
                    self.intercepted_response = response_body
                    return

            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")
        else:
            return self.intercept_route(route)

    def submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.route("**", lambda route, request: self.intercept_request(route, request))
        page.click('xpath=//button[contains(@class, "hm__RoundAndOneWayTab_searchButton__")]')
        time.sleep(1)

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        credential = random.choice(self.credentials)
        
        page.wait_for_selector('div#navbarSupportedContent', timeout=60000)

        try:
            profile = page.locator('xpath=//li[contains(@class, "hm__HeaderNavBar_msLogin__")]//span[contains(@class, "hm__HeaderNavBar_userfullname")]')
            profile.wait_for(timeout=5000)
            need_login = False
        except Exception as e:
            logger.error(f"need to login exeption: {e}")
            need_login = True
        
        if need_login:
            self._close_cookie_popup(page)

            login_btn = page.locator('xpath=//div[contains(@class, "hm__HeaderNavBar_signinDropdown")]')
            login_btn.click()
            time.sleep(5)

            membership_num_input = page.locator('input#tkNumber')
            membership_num_input.wait_for(timeout=5000)
            membership_num_input.click()
            time.sleep(2)
            self.human_typing(page, membership_num_input, credential.username)
            password_input = page.locator('input#msPassword')
            password_input.wait_for(timeout=5000)
            password_input.click()
            time.sleep(2)
            self.human_typing(page, password_input, credential.password)
            remember_ele = page.locator('div#rememberMe')
            class_attribute = remember_ele.evaluate('(element) => element.className')
            if 'hm__style_checked_' not in class_attribute:
                remember_checkbox = page.locator('div#rememberMe label')
                remember_checkbox.click()
                time.sleep(2)
            page.click('button#msLoginButton')
            time.sleep(1)

        try:
            profile = page.locator('xpath=//li[contains(@class, "hm__HeaderNavBar_msLogin__")]//span[contains(@class, "hm__HeaderNavBar_userfullname")]')
            profile.wait_for(timeout=60000)
            logger.info(f"Login Succeed!")
        except Exception as e:
            raise LoginFailed(airline=self.AIRLINE)
        
    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment in enumerate(flight_data["segmentList"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")

                segment_origin = segment["departureAirportCode"]
                segment_destination = segment["arrivalAirportCode"]
                segment_departure_datetime = datetime.datetime.strptime(segment["departureDateTime"], '%d-%m-%Y %H:%M')
                segment_departure_date = segment_departure_datetime.strftime('%Y-%m-%d')
                segment_departure_time = segment_departure_datetime.strftime('%H:%M')
                segment_arrival_datetime = datetime.datetime.strptime(segment["arrivalDateTime"], '%d-%m-%Y %H:%M')
                segment_arrival_date = segment_arrival_datetime.strftime('%Y-%m-%d')
                segment_arrival_time = segment_arrival_datetime.strftime('%H:%M')
                segment_aircraft = segment["carrierAirline"]["airlineCode"]
                segment_carrier = segment["flightCode"]["airlineCode"]
                segment_flight_number = segment["flightCode"]["flightNumber"]

                connection_time = segment["groundDuration"]
                segment_duration = segment["journeyDurationInMillis"]

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
        self, flight_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        points_by_fare_names: Dict[str, dict] = {}

        try:
            if not flight_data["soldOut"]:
                cabin_str = CabinClassCodeMapping[cabin_class]
                if cabin_class == c.CabinClass.PremiumEconomy:
                    cabin_str = CabinClassCodeMapping[c.CabinClass.Economy]
                points_products = flight_data["fareCategory"].get(cabin_str, {}).get('bookingPriceInfoList', [])
                for points_product in points_products:
                    if cabin_class == c.CabinClass.PremiumEconomy:
                        if points_product["brandCode"] != "Y":
                            continue
                    fare_name = f'{CabinClassCodeMapping[cabin_class]} {points_product["brandCode"]}'
                    points_by_fare_names[fare_name] = {
                        "points": points_product["referencePassengerFare"]["totalFare"]["amount"],
                        "fare_brand_name": CabinClassCodeMapping[cabin_class] + ' - ' + f'{points_product["brandCode"]} Class',
                        "cash_fee": CashFee(
                            amount=70,
                            currency='USD',
                        ),
                    }

        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")
            import traceback
            traceback.print_exc()

        return points_by_fare_names

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        
        page.wait_for_selector('xpath=//div[contains(@class, "av__FlightItem_flightItem__")]', timeout=60000)

        if not self.intercepted_response:
            raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

        flights = list()
        flights_data = self.intercepted_response
        information_list = flights_data["data"].get('originDestinationInformationList', [])
        if information_list:
            flights = information_list[0].get('originDestinationOptionList', [])
        
        if not flights:
            raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

        logger.info(f"{self.AIRLINE.value}: Found {len(flights)} flights...")

        all_cabins = []
        if cabin_class == c.CabinClass.All:
            all_cabins = [
                c.CabinClass.Economy,
                c.CabinClass.First,
                c.CabinClass.Business
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
                duration = flight_search_result["journeyDuration"]

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
                        cash_fee=points_and_cash["cash_fee"],
                        segments=segments,
                        duration=duration_isoformat(datetime.timedelta(milliseconds=duration)),
                    )
                    yield flight
                    
    def _run(self, origin: str, destination: str, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy, adults: int = 1, **kwargs) -> Iterator[Flight]:
        if origin not in supported_airports:
            raise NoSearchResult(airline=self.AIRLINE.value, reason=f"Not supported airport - {origin}")
        
        if destination not in supported_airports:
            raise NoSearchResult(airline=self.AIRLINE.value, reason=f"Not supported airport - {destination}")
        
        return super()._run(origin, destination, departure_date, cabin_class, adults)

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = TurkishPlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=13)

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

    # run("JFK", "IST", c.CabinClass.Economy)
    run("IST", "LHR", c.CabinClass.All)
    # run("DFW", "LHR", c.CabinClass.Business)
