import base64
import datetime
import glob
import json
import logging
import os
import re
import shutil
import time
from dateutil import tz
from typing import Iterator, Optional
from xml.dom import minidom
from typing import Dict, Iterator, List, Optional
from isodate import duration_isoformat
from zenrows import ZenRowsClient

from scrapy import Selector

from playwright.sync_api import Locator, Page
from curl_cffi import requests as crequests
import requests
from src import constants as c
from src.av.constants import CabinClassCodeMapping, CabinClassCodeIDMapping, CabinClassCodeTypeMapping
from src.exceptions import NoSearchResult, LoginFailed
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.proxy import PrivateProxyService
from src.schema import CashFee, Flight, FlightSegment
from src.types import SmartCabinClassType, SmartDateType
from src.utils import get_airport_timezone
from src.db import insert_target_headers

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

spanish_to_english_months = {
    'Ene': 'Jan',
    'Feb': 'Feb',
    'Mar': 'Mar',
    'Abr': 'Apr',
    'May': 'May',
    'Jun': 'Jun',
    'Jul': 'Jul',
    'Ago': 'Aug',
    'Sep': 'Sep',
    'Oct': 'Oct',
    'Nov': 'Nov',
    'Dic': 'Dec'
}


class AviancaPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.Avianca
    REQUIRED_LOGIN = True
    BLOCK_RESOURCE = True
    HOME_PAGE_URL = "https://www.lifemiles.com/fly/find"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered
    TARGET = 'avianca'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._compute_latest_user_data_dir()
        self.intercepted = False
        self.intercepted_response = None
        self.departure_date = None
        self.airport_timezone = get_airport_timezone()

    def __del__(self):
        self._clean_outdate_user_data_dir()

    def _copytree(self, src, dst):
        """
        shutil.copytree didn't work as expected, use this simple command to
        preserve attributes/permissions of original folder
        """
        os.system("cp -a " + src + " " + dst)

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
            
            # "ip": "us.smartproxy.com",
            # "port": "10001",
            # "user": "spyc5m5gbs",
            # "pwd": "puFNdLvkx6Wcn6h6p8",
        }

    def _close_cookie_popup(self, page):
        try:
            cookie = page.locator("button.CookiesBrowserAlert_acceptButtonNO")
            cookie.wait_for(timeout=1000)
            page.click("button.CookiesBrowserAlert_acceptButtonNO")
            logger.info("clicked accept cookie popup")
        except Exception as e:
            logger.error(f"click accept cookie popup error: {e}")
            pass

    def _select_oneway(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.click("button.waru-BookerContent_nonMobileTripTypeButton:first-child")

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        self.human_typing(page, page.locator('input[id="ar_bkr_fromairport"]'), origin)
        page.click(f'//p[@class="waru-AirportsDropdown_airportsDropdownCode"][contains(text(), "{origin}")]')

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        self.human_typing(page, page.locator('input[id="ar_bkr_toairport"]'), destination)
        page.click(f'//p[@class="waru-AirportsDropdown_airportsDropdownCode"][contains(text(), "{destination}")]')

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        self.departure_date = departure_date
        page: Page = kwargs.get("page")
        page.click(f'//div[@class="waru-BookerContent_bookerCalendar"]/button')
        track_ele = page.locator('div.waru-Month_buttonRight, button.waru-CalendarAvError_cancelButton')
        track_ele.wait_for(timeout=20000)

        try:
            cal_cancel_ele = page.wait_for_selector("button.waru-CalendarAvError_cancelButton", timeout=500)
        except:
            cal_cancel_ele = None
        
        if cal_cancel_ele:
            raise NoSearchResult(airline=self.AIRLINE)

        date_found = False
        while True:
            next_month_ele = page.locator('div.waru-Month_buttonRight')
            next_month_ele.wait_for(timeout=20000)

            calendars = page.locator('.waru-CalendarAvContent_monthWrapper').all()
            for calendar in calendars:
                month_element = calendar.locator('.waru-Month_monthName')
                month_name = month_element.inner_text()
                year_element = calendar.locator('.waru-Month_year')
                year_val = year_element.inner_text()

                en_month_name = spanish_to_english_months.get(month_name, month_name)
                cal_date_obj = datetime.datetime.strptime(f'{en_month_name} {year_val}', '%b %Y')

                if cal_date_obj.year == departure_date.year and cal_date_obj.month == departure_date.month:
                    date_found = True

                    cal_days = calendar.locator('.waru-Day_dayNumberNrm').all()
                    for cal_day in cal_days:
                        day_val = cal_day.inner_text()
                        if day_val and day_val.strip() == str(departure_date.day):
                            cal_day.click()
                            break

                    break
            
            if date_found:
                break
            else:
                next_month_ele.click()

    def _select_cabin_class(self, cabin_class: c.CabinClass.Economy, *args, **kwargs) -> None:
        if cabin_class == c.CabinClass.Economy:
            pass
        elif cabin_class == c.CabinClass.Business or cabin_class == c.CabinClass.First:
            page: Page = kwargs.get("page")
            page.click('//div[@class="waru-BookerContent_bookerTravelers"]/button')
            business_cabin_ele = page.locator('//div[@class="waru-TravelersDropdown_firstRow"][2]/button')
            business_cabin_ele.wait_for(timeout=2000)
            business_cabin_ele.click()

            page.click('.waru-TravelersDropdown_buttonTravels')

    def intercept_request(self, route, request):


        if "/svc/air-redemption-find-flight-private" in request.url and request.method == "POST" and not self.intercepted:
            route.continue_()
            try:
                self.intercepted = True
                response = request.response()
                response_body = response.json()
                av_headers = request.all_headers()
                payload = request.post_data_json
                insert_target_headers(av_headers, self.TARGET, payload)
                status_code = response.status
                logger.info(f"{self.AIRLINE.value}: Response from {request.url}: Status Code - {status_code} - response_body: {response_body}")

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
        page.click('.waru-BookerContent_bookerActionButtonLarge')

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: SmartDateType,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
        *args,
        **kwargs,
    ) -> None:
        logger.info(f"{self.AIRLINE.value}: Searching...")
        if self.REQUIRED_LOGIN:
            self.login(*args, **kwargs)
        self.select_oneway(*args, **kwargs)
        self.select_cabin_class(cabin_class, *args, **kwargs)
        self.select_origin(origin, *args, **kwargs)
        self.select_destination(destination, *args, **kwargs)
        self.select_date(departure_date, *args, **kwargs)
        self.submit(*args, **kwargs)

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        username: str = kwargs.get("username")
        password: str = kwargs.get("password")
        
        if username is None or password is None:
            username = self.username
            password = self.password

        page.wait_for_selector('div#FixedMenuHeader', timeout=60000)

        try:
            profile = page.locator('xpath=//div[contains(@class, "menu-ui-Menu_button")]/span')
            profile.wait_for(timeout=5000)
            need_login = False
        except Exception as e:
            logger.error(f"need to login exeption: {e}")
            need_login = True
        
        if need_login:
            self._close_cookie_popup(page)

            page.click("a.menu-ui-Menu_login")
            login_option = page.locator('a#social-Lifemiles')
            login_option.wait_for(timeout=60000)
            login_option.click()

            page.wait_for_selector('input[name="username"]', timeout=90000)
            self.human_typing(page, page.locator('input[name="username"]'), username)
            time.sleep(1)
            self.human_typing(page, page.locator('input[id="password"]'), password)
            time.sleep(1)
            page.click('button[id="Login-confirm"]')
            time.sleep(1)

        try:
            profile = page.locator('xpath=//div[contains(@class, "menu-ui-Menu_button")]/span')
            profile.wait_for(timeout=90000)
            logger.info(f"Login Succeed!")
        except Exception as e:
            raise LoginFailed(airline=self.AIRLINE)
        
    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment in enumerate(flight_data["flightsDetail"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")

                segment_origin = segment["departingCityCode"]
                segment_destination = segment["arrivalCityCode"]
                segment_origin_tz = self.airport_timezone.get(segment_origin, '')
                segment_destination_tz = self.airport_timezone.get(segment_destination, '')
                
                segment_departure_date = segment["departingDate"]
                segment_departure_time = segment["departingTime"]
                segment_arrival_date = segment["arrivalDate"]
                segment_arrival_time = segment["arrivalTime"]
                segment_aircraft = segment["operatedBy"]
                if segment_aircraft:
                    segment_aircraft = segment_aircraft.replace('OPERATED BY ', '')
                segment_carrier = segment["operatedCompany"]
                segment_flight_number = segment["flightNumber"]

                departure_datetime_str = f'{segment_departure_date}T{segment_departure_time}'
                departure_datetime_obj = datetime.datetime.strptime(departure_datetime_str, '%Y-%m-%dT%H:%M')
                arrival_datetime_str = f'{segment_arrival_date}T{segment_arrival_time}'
                arrival_datetime_obj = datetime.datetime.strptime(arrival_datetime_str, '%Y-%m-%dT%H:%M')

                segment_departure_datetime_tz = departure_datetime_obj.replace(tzinfo=tz.gettz(segment_origin_tz)).astimezone(tz.tzutc())
                segment_arrival_datetime_tz = arrival_datetime_obj.replace(tzinfo=tz.gettz(segment_destination_tz)).astimezone(tz.tzutc())
                segment_duration = duration_isoformat(segment_arrival_datetime_tz - segment_departure_datetime_tz)
                
                if len(flight_data["flightsDetail"]) > segment_index+1:
                    next_segment_departure_date = flight_data["flightsDetail"][segment_index+1]["departingDate"]
                    next_segment_departure_time = flight_data["flightsDetail"][segment_index+1]["departingTime"]
                    next_departure_datetime_str = f'{next_segment_departure_date}T{next_segment_departure_time}'
                    next_departure_datetime_obj = datetime.datetime.strptime(next_departure_datetime_str, '%Y-%m-%dT%H:%M')
                    connection_time = next_departure_datetime_obj - arrival_datetime_obj
                else:
                    connection_time = 0
                
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
                        duration=segment_duration,
                        layover_time=duration_isoformat(connection_time)
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
            points_products = flight_data["products"]
            for points_product in points_products:
                if not points_product["soldOut"] and points_product["showBundle"]:
                    if not points_product['pricingType'].endswith('D'):
                        if points_product["cabinCode"] == CabinClassCodeIDMapping[cabin_class]:
                            if cabin_class == c.CabinClass.PremiumEconomy:
                                if points_product["productType"] != "B3":
                                    continue
                            fare_name = CabinClassCodeMapping[cabin_class]
                            if points_product["productType"] in CabinClassCodeTypeMapping:
                                fare_name += ' ' + CabinClassCodeTypeMapping[points_product["productType"]]
                            points_by_fare_names[fare_name] = {
                                "points": int(points_product["totalMiles"]),
                                "fare_brand_name": CabinClassCodeTypeMapping.get(points_product["productType"], '')
                            }

        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")
            import traceback
            traceback.print_exc()

        return points_by_fare_names

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        
        try:
            page.wait_for_selector('.waru-AirRedemptionFlightPicker_flightTableBody .waru-AirRedemptionFlightPickerRow_flightItinerary', timeout=30000)
        except Exception:
            pass

        if not self.intercepted_response:
            raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")
        
        flights_data = self.intercepted_response
        flights = flights_data["tripsList"]

        if not flights:
            raise NoSearchResult(airline=self.AIRLINE, reason="Not available flights!")

        logger.info(f"{self.AIRLINE.value}: Found {len(flights)} flights...")

        all_cabins = []
        if cabin_class == c.CabinClass.All:
            all_cabins = [
                c.CabinClass.Economy,
                c.CabinClass.First,
                c.CabinClass.Business,
                c.CabinClass.PremiumEconomy
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
                duration = flight_search_result["duration"]
                duration = duration.replace(':', 'H')
                duration = f'PT{duration}M'

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
                        cash_fee=CashFee(
                            amount=float(flight_search_result["usdTaxValue"]),
                            currency="USD",
                        ),
                        segments=segments,
                        duration=duration,
                    )
                    yield flight



if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AviancaPlaywrightCrawler()
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

    # run("MIA", "LIM", c.CabinClass.Economy)
    run("IAD", "BCN", c.CabinClass.All)
    # run("JFK", "BOG", c.CabinClass.PremiumEconomy)
    # run("MIA", "BOG", c.CabinClass.Business)
    # run("MIA", "GRU", c.CabinClass.Economy)
