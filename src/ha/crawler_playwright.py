import datetime
import glob
import json
import logging
import os
import re
import shutil
import time
from typing import Iterator, Optional
from typing import Dict, Iterator, List, Optional, Tuple
from isodate import duration_isoformat
from lxml import etree, html
import random
import subprocess
import platform

from playwright.sync_api import Locator, Page
from src import constants as c
from src.ha.constants import CabinClassCodeMapping
from src.ha.constants import supported_airports
from src.exceptions import NoSearchResult, LoginFailed
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    parse_date,
    parse_time,
    extract_flight_number,
    convert_currency_symbol_to_name,
    convert_human_time_to_seconds
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HawaiianAirlineCredentials = c.Credentials[c.Airline.HawaiianAirline]

class HawaiianPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.HawaiianAirline
    REQUIRED_LOGIN = True
    BLOCK_RESOURCE = True
    HOME_PAGE_URL = "https://www.hawaiianairlines.com/my-account/login/?ReturnUrl=%2fmy-account"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials: List[c.AirlineCredential] = HawaiianAirlineCredentials.copy()
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
            acceptBtn = page.locator("xpath=//button[@class='accept-recommended-btn-handler']")
            acceptBtn.wait_for(timeout=5000)
            page.click("xpath=//button[@class='accept-recommended-btn-handler']")
            logger.info("clicked accept cookie popup")
        except Exception as e:
            logger.error(f"click accept cookie popup error: {e}")
            pass

    def _select_miles(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click('xpath=//span[@class="bodycopy-sans-4"][contains(text(), "Miles")]')

    def _select_oneway(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click("xpath=//a[contains(@id, 'triptype1')]")
        time.sleep(1)
        # page.click("xpath=.//ul[@id='redemption-trip-type-custom-list-box']/li[@id='redemption-trip-type-option--O']")
        # time.sleep(1)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        try:
            self.human_typing(page, page.locator("xpath=//input[@id='origin']"), origin)
            time.sleep(5)
            origin_airport = page.locator("//div[@class='location-dropdown']//ul/li[contains(@class, 'match')][1]")
            origin_airport.wait_for(timeout=20000)
            origin_airport.click()
            time.sleep(1)
        except Exception as e:
            raise NoSearchResult(airline=self.AIRLINE.value, reason=f"Could not find origin airport - {origin}")

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        try:
            self.human_typing(page, page.locator("xpath=//input[@id='destination']"), destination)
            time.sleep(5)
            destination_airport = page.locator("xpath=//div[@class='location-dropdown']//" "ul/li[contains(@class, 'match')][1]")
            destination_airport.wait_for(timeout=20000)
            destination_airport.click()
            time.sleep(1)
        except Exception as e:
            raise NoSearchResult(airline=self.AIRLINE.value, reason=f"Could not find destination airport - {destination}")

    def _select_date(self, depDate: datetime.date, *args, **kwargs):
        page: Page = kwargs.get("page")
        self.human_typing(page, page.locator("xpath=//input[@id='DepartureDate']"), depDate.strftime("%m/%d/%Y"))
        time.sleep(1)
        page.click("body", click_count=1)

    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click("xpath=//button[@class='btn-primary btn-cta-search ng-scope']")
        page.wait_for_load_state()

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        credential = random.choice(self.credentials)

        need_login = False
        
        try:
            profile = page.locator("xpath=//span[@class='nav-account-name']")
            profile.wait_for(timeout=20000)
            need_login = False
        except:
            need_login = True
            pass

        print("need_login ----------------->", need_login)

        if need_login:
            self.human_typing(page, page.locator('input[id="user_name"]'), credential.username)
            time.sleep(1)
            self.human_typing(page, page.locator('input[id="password"]'), credential.password)
            time.sleep(1)

            page.click("xpath=//button[contains(@id, 'submit_login_button')]")
            time.sleep(5)

            try:
                profile = page.locator("xpath=//span[@class='nav-account-name']")
                profile.wait_for(timeout=20000)
                logger.info(f"Login Succeed!")
            except Exception as e:
                raise LoginFailed(airline=self.AIRLINE)
        else:
            page.click('xpath=//a[@id="header_book_nav"]')
            time.sleep(1)
            page.click('xpath=//a[@id="book_flights_tile"]')
            time.sleep(1)


    def extract_flight_detail(self, page: Page, flight_row_element) -> list:
        segments = []
        try:
            # Click on link details
            detail_btn = flight_row_element.query_selector('xpath=//a[@class="link"][contains(text(), "Flight details")]')
            detail_btn.click()

            # Ensure the modal dialog is visible
            flight_segments = page.query_selector_all(
                "ha-modal-dialog div.ha-modal-body app-flight-details-modal "
                "div.flight-details-modal div.flight-section"
            )

            layover_sections = page.query_selector_all(
                "ha-modal-dialog div.ha-modal-body app-flight-details-modal "
                "div.flight-details-modal div.layover-section"
            )

            index = 0
            for segment_element in flight_segments:
                duration_element = segment_element.query_selector(f"#ha-flight-duration-{str(index)}")

                duration = duration_element.inner_text().replace(" Duration:  ", "")
                duration_s = convert_human_time_to_seconds(duration)
                print("duration_s ===>", duration_s)
                
                # print(f"#ha-flight-departure-info-{str(index)}")
                departure_element = segment_element.query_selector(f"#ha-flight-departure-info-{str(index)}")
                depart_info = departure_element.inner_text()
                print("depart_info ===>", depart_info)
                segment_departure_time = parse_time(depart_info, "%I:%M %p, %a, %b %d, %Y")
                segment_departure_date = parse_date(depart_info, "%I:%M %p, %a, %b %d, %Y")

                arrival_element = segment_element.query_selector(f"#ha-flight-arrival-info-{str(index)}")
                arrival_info = arrival_element.inner_text()
                print("arrival_info ===>", arrival_info)
                if "(Next day)" in arrival_info:
                    arrival_info = arrival_info.replace("(Next day)", "").strip()

                segment_arrival_time = parse_time(arrival_info, "%I:%M %p, %a, %b %d, %Y")
                segment_arrival_date = parse_date(arrival_info, "%I:%M %p, %a, %b %d, %Y")
                
                airline_elements = segment_element.query_selector_all(".location div")
                depart_airline = airline_elements[0].inner_text()
                segment_origin = re.search(r"\((.*?)\)", depart_airline).group(1)
                print("depart_airline ===>", depart_airline)

                destination_airline = airline_elements[2].inner_text()
                segment_destination = re.search(r"\((.*?)\)", destination_airline).group(1)

                segment_aircraft = segment_element.query_selector(f"*css=div[id*=ha-aircraft-num-{str(index)}]").inner_text()
                segment_aircraft = segment_aircraft.replace("Aircraft: ", "")
                print("segment_aircraft ===>", segment_aircraft)

                segment_flight_number = segment_element.query_selector(".flight-info-number").inner_text()
                segment_flight_number = segment_flight_number.replace("Flight ", "")
                print("segment_flight_number ===>", segment_flight_number)

                carrier, flight_number = extract_flight_number(segment_flight_number)
                print("flight_number ====>", flight_number)
                
                try:
                    time_pattern = re.compile(r'(\d+h )?\d+m')
                    layover_element = layover_sections[index].query_selector("span").inner_text()
                    layover_human_time = time_pattern.search(layover_element).group()
                    layover_time_s = convert_human_time_to_seconds(layover_human_time)
                    layover_time = duration_isoformat(datetime.timedelta(seconds=layover_time_s))
                except Exception:
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

                })
                index+=1

            # print("segments ===>", segments)
            # Close modal dialog
            page.click("ha-modal-dialog div.icon-close")
            return segments
        except Exception as e:
            print(f"Error while extracting flight details: {str(e)}")
            return []
        
    def extract_points(
        self, flight_row_element, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Tuple[str, float, CashFee]]:
        airline_cabin_class = CabinClassCodeMapping[cabin_class]

        try:
            price_container = flight_row_element.query_selector(
                f"xpath=//div[contains(@class, 'award-{airline_cabin_class}')]"
                f"/div[contains(@class, 'flight-results-column')]",
            )
            fare_name = price_container.query_selector("xpath=.//span[@class='flight-results-column__cabin-type']").inner_text()
            print("fare_name ===>", fare_name)
            mile_and_cost_elements = price_container.query_selector_all(
                "xpath=//div[contains(@class, 'flight-results-column__fare-cost')]/"
                "div[contains(@class, 'flight-results-column__fare-cost--miles')]/span"
            )

            points = mile_and_cost_elements[0].inner_text().replace(" mi", "")
            points = convert_k_to_float(points)
            print("points ===>", points)

            duration = flight_row_element.query_selector("xpath=//div[@class='duration']").inner_text()
            print("duration ===>", duration)

            price_text = mile_and_cost_elements[1].inner_text()
            currency, amount = extract_currency_and_amount(price_text.strip("+"))
            currency = convert_currency_symbol_to_name(currency)
            return fare_name, points, CashFee(currency=currency, amount=amount), duration
        except Exception as e:
            print(f"Get price error - {e}")
            pass
        return

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        
        try:
            result_page = page.locator("xpath=//div[contains(@class, 'flight-results')]")
            result_page.wait_for(timeout=60000)
        except Exception:
            pass
        try:
            search_results = page.query_selector_all("xpath=//div[contains(@class, 'flight-results')]//div[contains(@class, 'flight-row')]")
        except (TimeoutError):
            raise NoSearchResult(airline=self.AIRLINE)
        
        all_cabins = []
        if cabin_class == c.CabinClass.All:
            all_cabins = [
                c.CabinClass.Economy,
                c.CabinClass.First,
                c.CabinClass.Business
            ]
        else:
            all_cabins = [cabin_class]

        for index, flight_row_element in enumerate(search_results):

            for cabin_item in all_cabins:
                fare = self.extract_points(flight_row_element, cabin_item)
                if fare is None:
                    continue
                
                fare_name, points, cash_fee, duration = fare
                duration_s = convert_human_time_to_seconds(duration)

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
                    duration=duration_isoformat(datetime.timedelta(seconds=duration_s)),
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
        crawler = HawaiianPlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=11, day=17)

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
    run("HND", "HNL", c.CabinClass.All)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
