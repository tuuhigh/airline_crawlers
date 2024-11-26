import glob
import json
import logging
import os
import re
import shutil
import time
import datetime
from datetime import timedelta
from dateutil import parser
from typing import Iterator, Optional
from typing import Dict, Iterator, List, Optional, Tuple
from isodate import duration_isoformat
from lxml import etree, html
import random
from imap_tools import MailBox, AND
import subprocess
import platform

from playwright.sync_api import Locator, Page
from src import constants as c
from src.ek.constants import CabinClassCodeMapping, CabinClassFBMapping
from src.exceptions import NoSearchResult, LoginFailed
from src.ek.constants import supported_airports
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    parse_date,
    parse_time,
    extract_flight_number,
    convert_human_time_to_seconds
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EmiratesAirlineCredentials = c.Credentials[c.Airline.Emirates]

class EmiratesPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.Emirates
    REQUIRED_LOGIN = True
    HOME_PAGE_URL = "https://www.emirates.com/us/english/?page=%2Fus%2Fenglish%2F"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials: List[c.EKAirlineCredential] = EmiratesAirlineCredentials.copy()
        self._compute_latest_user_data_dir()

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
        all_user_data_dirs = glob.glob(user_data_dir_pattern)

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
        MAX_COMPLETE_TIME = 60 * 20
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
    
    def get_email_verification_code(self):
        credential = random.choice(self.credentials)
        time.sleep(30)
        with MailBox('imap.gmail.com').login(credential.username, credential.app_pass, 'INBOX') as mailbox:
            emails = list(mailbox.fetch(AND(seen=False), limit=1, reverse=True))

            if len(emails) > 0:
                match = re.search(r'Your passcode is\s*:\s*(\d+)', emails[0].text)
                    
                if match:
                    return match.group(1)
                else:
                    print("Passcode not found in the email body.")
                    return None

    def _close_cookie_popup(self, page):
        try:
            acceptBtn = page.locator("xpath=//button[@id='onetrust-accept-btn-handler']")
            acceptBtn.wait_for(timeout=10000)
            acceptBtn.click()
            logger.info("clicked accept cookie popup")
        except Exception as e:
            logger.error(f"click accept cookie popup error: {e}")
            pass

    def _select_miles(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        miles_button = page.locator('xpath=//div[@id="dvPoMiles"]')
        miles_button.wait_for(timeout=60000)
        miles_button.click()
        time.sleep(1)

    def _select_oneway(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click('xpath=//div[@id="dvRadioOneway"]')
        time.sleep(1)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        try:
            self.human_typing(page, page.locator("xpath=//input[@id='ctl00_c_CtWNW_ddlFrom-suggest']"), origin)
            time.sleep(3)
            airport_dropdown = page.locator("xpath=//input[@id='ctl00_c_CtWNW_ddlFrom-suggest']")
            airport_dropdown.press("ArrowDown")
            time.sleep(1)
            airport_dropdown.press("Enter")
        except Exception as e:
            raise NoSearchResult(airline=origin, reason="Could not find origin airport")

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        try:
            self.human_typing(page, page.locator("xpath=//input[@id='ctl00_c_CtWNW_ddlTo-suggest']"), destination)
            time.sleep(1)
            airport_dropdown = page.locator("xpath=//input[@id='ctl00_c_CtWNW_ddlTo-suggest']")
            airport_dropdown.press("ArrowDown")
            time.sleep(1)
            airport_dropdown.press("Enter")
        except Exception as e:
            raise NoSearchResult(airline=destination, reason="Could not find destination airport")

    def _select_date(self, depDate: datetime.date, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click('xpath=//input[@id="txtDepartDate"]')
    
        year = depDate.year
        month = depDate.month
        day = depDate.day
        adjusted_month = month - 1
        date = f"{day}-{adjusted_month}-{year}"
                
        while True:
            try:
                page.click(f"xpath=//a[@id='day-{date}']", timeout=5000)
                time.sleep(1)
                break
            except Exception:
                next_month_btn_xpath = "//div[@id='ui-datepicker-div']//a[@id='nextMonth']"
                next_month_btn = page.query_selector(f"xpath={next_month_btn_xpath}")
                if next_month_btn:
                    next_month_btn.click()
                else:
                    print("Next Month button not found")
                    raise()

                time.sleep(1)
                
    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click("xpath=//a[@id='ctl00_c_IBE_PB_FF']")
        page.wait_for_load_state()

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        credential = random.choice(self.credentials)
        self._close_cookie_popup(page)

        try:
            profile = page.locator("xpath=//span[@class='login-icon icon icon-profile-account mobile-hidden']")
            profile.wait_for(timeout=10000)
            need_login = False
            page.click('xpath=//a[@class="search-flight__inline-link search-flight__inline-link--advanced-search"]')
        except Exception:
            page.click("xpath=//a[@id='login-nav-link']")
            need_login = True
            

        if need_login:
            self.human_typing(page, page.locator('input[id="sso-email"]'), credential.username)
            time.sleep(1)
            self.human_typing(page, page.locator('input[id="sso-password"]'), credential.password)
            time.sleep(1)

            page.click("xpath=//button[contains(@id, 'login-button')]")
            time.sleep(3)

            try:
                code_input = page.locator("xpath=//input[@id='0']")
                code_input.wait_for(timeout=30000)

                pass_code = self.get_email_verification_code()
                time.sleep(3)

                for i, digit in enumerate(pass_code):
                    self.human_typing(page, page.locator(f'input[id="{i}"]'), digit)
            except:
                pass

            try:
                profile = page.locator("xpath=//span[@class='login-icon icon icon-profile-account mobile-hidden']")
                profile.wait_for(timeout=60000)
                logger.info(f"Login Succeed!")
                page.click('xpath=//a[@class="search-flight__inline-link search-flight__inline-link--advanced-search"]')
            except Exception as e:
                raise LoginFailed(airline=self.AIRLINE)

    def extract_flight_detail(self, page: Page, flight_row_element) -> list:
        segments = []
        try:
            detail_btn = flight_row_element.query_selector('xpath=//a[@class="ts-js-open-modal tc-fbr-cursor-style ts-info"]')
            detail_btn.click()

            modal = page.query_selector("xpath=//div[contains(@class, 'is-visible')]")
            flight_segments = modal.query_selector_all("xpath=//section[@class='ts-fip__modal__panel']")
            connection_sections = modal.query_selector_all("xpath=//div[@class='ts-fip__modal__connection']")
            connection_count = len(connection_sections)

            index = 0
            for segment_element in flight_segments:
                duration_content_locator = segment_element.query_selector('xpath=.//div[@class="ts-fip__modal__left"]/div[@class="ts-fie"]/div[@class="ts-fie__infographic"]')
                duration_element = duration_content_locator.query_selector_all('time > span')
                duration = duration_element[1].inner_text().strip()
                duration_s = convert_human_time_to_seconds(duration)
                departure_time_element = segment_element.query_selector("xpath=//div[@class='content']/div[@class='ts-fip__modal__left']/div[@class='ts-fie']/div[@class='ts-fie__place']/time")
                segment_departure_time = departure_time_element.inner_text().strip()

                departure_date_element = segment_element.query_selector('xpath=//div[@class="ts-fip__modal__panel__header"]/time')
                depart_date = departure_date_element.inner_text()
                segment_departure_date = parse_date(depart_date, "%A, %d %b %y")

                arrival_time_element = segment_element.query_selector("xpath=//div[@class='content']/div[@class='ts-fip__modal__left']/div[@class='ts-fie']/div[@class='ts-fie__place ts-fie__right-side']/time")
                segment_arrival_time = arrival_time_element.inner_text().strip()
                
                arrival_date_element = segment_element.query_selector('xpath=//div[@class="ts-fip__modal__panel__header"]/time')
                arrival_date = arrival_date_element.inner_text()

                segment_arrival_date = None
                if "+1 day" in segment_arrival_time:
                    segment_arrival_time = segment_arrival_time.replace(" +1 day", "").strip()
                    parsed_date = parser.parse(arrival_date)
                    date_obj = parsed_date.date()
                    arrival_date = date_obj + timedelta(days=1)
                    segment_arrival_date = str(arrival_date)
                else:
                    segment_arrival_date = parse_date(arrival_date, "%A, %d %b %y")

                segment_origin_element = segment_element.query_selector("xpath=//div[@class='content']/div[@class='ts-fip__modal__left']/div[@class='ts-fie']/div[@class='ts-fie__place']/p")
                segment_origin = segment_origin_element.inner_text()
                segment_origin = segment_origin.split()[1]
                
                segment_destination_element = segment_element.query_selector_all("xpath=//div[@class='content']/div[@class='ts-fip__modal__left']/div[@class='ts-fie']/div[@class='ts-fie__place ts-fie__right-side']/p/span")
                segment_destination = segment_destination_element[1].inner_text().strip()

                segment_aircraft = segment_element.query_selector("xpath=//p[@class='details aircraft-detail']//strong").inner_text().strip()


                segment_flight_number = segment_element.query_selector("xpath=//p[@class='details status-detail']//strong").inner_text().strip()
                carrier, flight_number = extract_flight_number(segment_flight_number)

                layover_time = None
                layover_time_pattern = re.compile(r'(\d+\s*hr[s]?\s*)?\d+\s*min[s]?')
                connection_time_pattern = re.compile(r'(\d+\s*hours?\s*)?\d+\s*minutes?')
                flight_stop = None

                layer_section = segment_element.query_selector("xpath=//div[@class='ts-fip__modal__footer']")
                if layer_section:
                    stop_layover_element = layer_section.query_selector('xpath=//td[contains(@class, "duration-time")]').inner_text()
                    
                    if match := layover_time_pattern.search(stop_layover_element):
                        stop_duration_s = convert_human_time_to_seconds(match.group())
                        stop_duration = duration_isoformat(datetime.timedelta(seconds=stop_duration_s))

                    stop_flight_data = layer_section.query_selector_all('xpath=//tr')
                    stop_city = stop_flight_data[1].query_selector('xpath=//th').inner_text()
                    stop_city_time_elements = stop_flight_data[1].query_selector_all('xpath=//td')
                    stop_city_arrival_date = stop_city_time_elements[0].inner_text()
                    stop_city_departure_date = stop_city_time_elements[1].inner_text()
                    stop_city_arrival_time = parse_time(stop_city_arrival_date, "%H:%M, %d %b %y")
                    stop_city_departure_time = parse_time(stop_city_departure_date, "%H:%M, %d %b %y")

                    flight_stop = {
                        'stop_city': stop_city,
                        'arrival_time': stop_city_arrival_time,
                        'departure_time': stop_city_departure_time,
                        'duration': stop_duration
                    }

                try:
                    if connection_count > 0 and index < connection_count:
                        layover_human_time = connection_sections[index].query_selector("p > time").inner_text()
                    
                        if match := connection_time_pattern.search(layover_human_time):
                            layover_time_s = convert_human_time_to_seconds(match.group())
                            layover_time = duration_isoformat(datetime.timedelta(seconds=layover_time_s))

                except Exception as e:
                    print(f"An error occurred: {e}")
                    layover_time = None

                segments.append({
                    'origin': segment_origin,
                    'destination': segment_destination,
                    'departure_date': segment_departure_date,
                    'departure_time': segment_departure_time,
                    'arrival_date': segment_arrival_date,
                    'arrival_time': segment_arrival_time,
                    'aircraft': segment_aircraft,
                    'flight_number': flight_number,
                    'carrier': carrier,
                    'layover_time': layover_time,
                    'duration': duration_isoformat(datetime.timedelta(seconds=duration_s)),
                    'flight_stop': flight_stop
                })
                index+=1

            page.click("xpath=//div[contains(@class, 'is-visible')]//button[@class='ts-icon-close']")
            return segments
        except Exception as e:
            print(f"Error while extracting flight details: {str(e)}")
            return []
        
    def extract_points(
        self, flight_row_element, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Tuple[str, float, CashFee]]:
        airline_cabin_class = CabinClassCodeMapping[cabin_class]
        fb_class_name = CabinClassFBMapping[cabin_class]

        duration_content_locator = flight_row_element.query_selector('xpath=.//div[@class="ts-fip__fie"]/div[@class="ts-fie"]/div[@class="ts-fie__infographic"]')
        duration_element = duration_content_locator.query_selector_all('time > span')
        duration = duration_element[1].inner_text()

        price_container = flight_row_element.query_selector(
            f"xpath=//div[contains(@class, 'upg{airline_cabin_class}')]"
        )
        if price_container:
            fare_name = price_container.query_selector("xpath=//strong[@class='ts-fbr-option__class']").inner_text()
            mile_and_cost_elements = price_container.query_selector_all(
                "xpath=//div[contains(@class, 'ts-fbr-option__container')]/"
                "p[contains(@class, 'ts-fbr-option__price ts-fbr-option-price-miles')]"
            )

            points = mile_and_cost_elements[0].get_attribute('data-miles')
            points = convert_k_to_float(points)
            price = mile_and_cost_elements[0].get_attribute('data-price')
            amount = convert_k_to_float(price)
            currency = mile_and_cost_elements[0].get_attribute('data-currency')

            return fare_name, points, CashFee(currency=currency, amount=amount), duration
        else:
            fare_name = None
            price_containers = flight_row_element.query_selector_all('xpath=//div[contains(@class, "ts-fbr-option--disabled")]')
            for container in price_containers:
                class_attribute = container.get_attribute('class')
                class_list = class_attribute.split()

                if 'upg' not in class_list and fb_class_name in class_list:
                    fare_name = container.query_selector('xpath=//strong[@class="ts-fbr-option__class"]').inner_text()
            return fare_name, None, CashFee(currency=None, amount=None), duration

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        
        try:
            result_page = page.locator("xpath=//div[contains(@class, 'ts-fbr-flight-list__body')]")
            result_page.wait_for(timeout=60000)
        except Exception:
            pass
        try:
            search_results = page.query_selector_all("xpath=//div[contains(@class, 'flights-row')]")
        except (TimeoutError):
            raise NoSearchResult(airline=self.AIRLINE)

        all_cabins = []
        if cabin_class == c.CabinClass.All:
            all_cabins = [
                c.CabinClass.Economy,
                c.CabinClass.Business,
                c.CabinClass.First
            ]
        else:
            all_cabins = [cabin_class]

        for index, flight_row_element in enumerate(search_results):
            for cabin_item in all_cabins:

                fare = self.extract_points(flight_row_element, cabin_item)
                if fare is None:
                    continue
                
                fare_name, points, cash_fee, duration = fare

                if fare_name is None:
                    continue

                duration_s = convert_human_time_to_seconds(duration)
                duration_s = duration_isoformat(datetime.timedelta(seconds=duration_s)),

                try: 
                    segments = self.extract_flight_detail(page, flight_row_element)
                except Exception as e:
                    raise e
                
                yield Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0]['origin'],
                    destination=segments[-1]['destination'],
                    cabin_class=str(cabin_item.value),
                    airline_cabin_class=fare_name,
                    points=points,
                    cash_fee=cash_fee,
                    segments=segments,
                    duration=duration_s[0]
                )

    def _run(self, origin: str, destination: str, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy, adults: int = 1) -> Iterator[Flight]:
        if origin not in supported_airports:
            raise NoSearchResult(airline=self.AIRLINE.value, reason=f"Not supported airport - {origin}")
        
        if destination not in supported_airports:
            raise NoSearchResult(airline=self.AIRLINE.value, reason=f"Not supported airport - {destination}")
        
        return super()._run(origin, destination, departure_date, cabin_class, adults)

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = EmiratesPlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2025, month=2, day=2)

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
    run("DXB", "LHR", c.CabinClass.All)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
