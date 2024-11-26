import datetime
import glob
import json
import logging
import os
import re
import shutil
import time
from typing import Iterator, Optional
from typing import Dict, Iterator, List, Optional
from isodate import duration_isoformat
from lxml import etree, html
from dateutil import tz
import subprocess
import platform
from playwright.sync_api import Locator, Page
from src import constants as c
from src.cx.constants import CabinClassCodeMapping, get_airport_timezone
from src.exceptions import NoSearchResult, LoginFailed
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class CathayPacificPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.CathayPacific
    REQUIRED_LOGIN = True
    HOME_PAGE_URL = "https://www.cathaypacific.com/cx/en_US/sign-in.html"
    # HOME_PAGE_URL = "https://www.cathaypacific.com"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._compute_latest_user_data_dir()
        self.airport_timezone = self._compute_airport_tz()

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

    def _compute_airport_tz(self):
        airport_tz = get_airport_timezone()
        return {ap.get('iata_code', ''):ap.get('time_zone', '') for ap in airport_tz}
    
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
        page.click('xpath=.//li[@id="redemption-radio"]')

    def _select_oneway(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click('xpath=.//div[@id="redemption-panel"]//div[@aria-controls="redemption-trip-type-custom-list-box"]')
        time.sleep(1)
        page.click("xpath=.//ul[@id='redemption-trip-type-custom-list-box']/li[@id='redemption-trip-type-option--O']")
        time.sleep(1)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        self.human_typing(page, page.locator('xpath=.//div[@id="redemption-panel"]//div[contains(@class, "bookTripPanel__origin")]//input'), origin)
        time.sleep(1)
        page.click('xpath=.//div[@id="redemption-bookTripPanel__origin-ODOverlayList"]/li[1]')
        self._close_cookie_popup(page)
        time.sleep(1)

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        self.human_typing(page, page.locator('xpath=.//div[@id="redemption-panel"]//div[contains(@class, "bookTripPanel__destination")]//input'), destination)
        time.sleep(1)
        page.click('xpath=.//div[@id="redemption-bookTripPanel__destination-ODOverlayList"]/li[1]')
        time.sleep(1)

    def _select_date(self, depDate: datetime.date, *args, **kwargs):
        page: Page = kwargs.get("page")
        # page.click("xpath=//div[@id='redemption-panel']//div[@class='bookTripPanel__datePicker']/div[1]")
        page.evaluate(
            "document.querySelector(\".redemption-panel .bookTripPanel__datePicker .-departingDateInput\").click()"
        )
        time.sleep(2)

        found = False

        while True:
            try:
                page.click(f"xpath=//div[@id='redemption-date-picker-flyout']//button/div[@id='redemption-day-{depDate.isoformat()}']", timeout=5000)
                found = True
                time.sleep(1.13)
                break
            except Exception:
                next_month_btn_xpath = "//div[@id='redemption-date-picker-flyout']//div[@class='rdp-month rdp-caption_end']//div[@class='dayPicker__nav']//button[@class='dayPicker__navBtn dayPicker__navBtn__next']"
                next_month_btn = page.query_selector(f"xpath={next_month_btn_xpath}")
                if next_month_btn:
                    print("Next Month button found")
                    next_month_btn.click()
                    time.sleep(1.13)
                    print("Next Month button clicked")
                else:
                    print("Next Month button not found")
                    raise()

                time.sleep(1)

        if found:
            page.click("xpath=//div[@id='redemption-date-picker-flyout']//button[contains(@class, 'datePickerFlyout__doneBtn')]")

    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click("xpath=//button[@id='redemption-booking-search-btn']")
        page.wait_for_load_state()

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        username: str = kwargs.get("username")
        password: str = kwargs.get("password")

        if username is None or password is None:
            username = self.username
            password = self.password

        try:
            profile = page.locator('xpath=//div[@class="signIn"]//span[@class="button__label"][contains(text(), "with email")]')
            page.click('xpath=//div[@class="signIn"]//span[@class="button__label"][contains(text(), "with email")]')
            profile.wait_for(timeout=10000)
            need_login = False
        except Exception as e:
            logger.error(f"need to login exeption: {e}")
            need_login = True

        if need_login:
            self._close_cookie_popup(page)

            # page.click("button.kf-log-in-container__button")
            # time.sleep(10)
            self.human_typing(page, page.locator('input[name="email"]'), username)
            time.sleep(2)
            self.human_typing(page, page.locator('input[name="password"]'), password)
            time.sleep(1)
            # page.click('label[for="kf-login-remember"]')
            # time.sleep(1)

            page.click('xpath=//div[@class="signIn"]//button[@class="button -primary"]')
            time.sleep(5)

        try:
            profile = page.locator('xpath=//span[@class="welcomeLabel sensitive-data"]')
            profile.wait_for(timeout=20000)
            logger.info(f"Login Succeed!")
        except Exception as e:
            raise LoginFailed(airline=self.AIRLINE)

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
                segment_origin_tz = self.airport_timezone.get(segment_origin, '')
                segment_destination_tz = self.airport_timezone.get(segment_destination, '')
                segment_departure_datetime = datetime.datetime.fromtimestamp(segment_departure/1000, datetime.timezone.utc)
                segment_arrival = segment_data["destinationDate"]
                segment_arrival_datetime = datetime.datetime.fromtimestamp(segment_arrival/1000, datetime.timezone.utc)
                segment_aircraft = segment_data["flightIdentifier"]["marketingAirline"]
                segment_carrier = segment_data["flightIdentifier"]["marketingAirline"]
                segment_flight_number = segment_data["flightIdentifier"]["flightNumber"]
                
                segment_departure_datetime_tz = segment_departure_datetime.replace(tzinfo=tz.gettz(segment_origin_tz)).astimezone(tz.tzutc())
                segment_arrival_datetime_tz = segment_arrival_datetime.replace(tzinfo=tz.gettz(segment_destination_tz)).astimezone(tz.tzutc())
                segment_duration = duration_isoformat(segment_arrival_datetime_tz - segment_departure_datetime_tz)

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
                        departure_timezone=segment_origin_tz,
                        arrival_date=segment_arrival_datetime.date().isoformat(),
                        arrival_time=segment_arrival_datetime.time().isoformat()[:5],
                        arrival_timezone=segment_destination_tz,
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

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        try:
            flight_steps = page.locator("xpath=//span[@class='ribe-progress-label ng-binding'][contains(text(), 'Select flights')]")
            flight_steps.wait_for(timeout=20000)
        except Exception:
            pass

        page_content = page.content()
        
        # page_content_file = "CX_HTML_content.txt"
        
        # with open(page_content_file, 'w', encoding='utf-8') as f:
        #     f.write(page_content)

        # with open(page_content_file, 'r', encoding='utf-8') as f:
        #     page_content = f.read()
            
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
        print(f">>>>>>>>>>> flight_json_data: {flight_json_data}")
        if flight_json_data:
            flight_rows = html_dom.xpath('//div[contains(@class, "col-select-flight-wrap")]/div[contains(@class, "row-flight-card")]')
            if flight_rows:
                for flight_row in flight_rows:
                    print(f">>>>>>>>>>>. flight_row:{flight_row}")
                    flight_id = flight_row.xpath('./@data-flight-name')[0]
                    points_ele = flight_row.xpath('.//span[contains(@class, "am-total")]/text()')
                    print(f"point element: {points_ele}")
                    if points_ele:
                        points = points_ele[0]
                        print(f">>>>>>>.. points: {points}")
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
                    points=int(flight_search_result.get('points', '-1').replace(',', '')),
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration_s)),
                )
                yield flight

        else:
            print('No flights found')



if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = CathayPacificPlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=8, day=23)

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
    # run("JFK", "LHR", c.CabinClass.Economy)
    run("IAD", "HKG", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
