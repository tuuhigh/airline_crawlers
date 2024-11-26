import datetime
import json
import logging
import time
import random
from typing import Dict, Iterator, List, Optional

from isodate import duration_isoformat
from collections import namedtuple

from playwright.sync_api import Page
from src import constants as c
from src.vs.constants import (
    AirlineCabinClassCodeMapping,
    CabinClassCodeMappingForHybrid,
)
from src.exceptions import NoSearchResult, AirlineCrawlerException
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.db import insert_target_headers

logger = logging.getLogger(__name__)

GeoLocationConfiguration = namedtuple("GeoLocationConfiguration", ("proxy_host", "proxy_port", "home_page_url"))
GeoLocationConfigurations = [
    # GeoLocationConfiguration(
    #     proxy_host="us.smartproxy.com", proxy_port="10001", home_page_url="https://www.virginatlantic.com/us/en"
    # ),
    GeoLocationConfiguration(
        proxy_host="ca.smartproxy.com", proxy_port="20001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
    GeoLocationConfiguration(
        proxy_host="gb.smartproxy.com", proxy_port="30001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
    GeoLocationConfiguration(
        proxy_host="nl.smartproxy.com", proxy_port="10001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
    GeoLocationConfiguration(
        proxy_host="de.smartproxy.com", proxy_port="20001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
    GeoLocationConfiguration(
        proxy_host="fr.smartproxy.com", proxy_port="40001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
    GeoLocationConfiguration(
        proxy_host="mx.smartproxy.com", proxy_port="20001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
    GeoLocationConfiguration(
        proxy_host="br.smartproxy.com", proxy_port="10001", home_page_url="https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    ),
]

class VirginAtlanticPlaywrightWireCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.VirginAtlantic
    REQUIRED_LOGIN = False
    TARGET = "virgin_atlantic"
    BLOCK_RESOURCE = True
    HOME_PAGE_URL = "https://www.virginatlantic.com/flight-search/book-a-flight?tripType=ONE_WAY"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered
    miles_selected = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smart_proxy_host, self.smart_proxy_port, self.home_page_url = random.choice(GeoLocationConfigurations)

    def get_proxy(self):
        # proxy_user = "ihgproxy1"
        # proxy_pass = "ihgproxy1234_country-us"
        # proxy_host = "geo.iproyal.com"
        # proxy_port = "12321"

        return {
            "ip": "geo.iproyal.com",
            "port": "12321",
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-ca",
        }

        # return {
        #     "ip": self.smart_proxy_host,
        #     "port": self.smart_proxy_port,
        #     "user": "spyc5m5gbs",
        #     "pwd": "puFNdLvkx6Wcn6h6p8",
        # }
    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_select_origin_box = "document.querySelector('#fromAirportName').click()"
        js_script_enter_origin_airport = (
            """var searchInput = document.getElementById('search_input');
            if (searchInput) {searchInput.value = '%s';}
            var closeButton = document.querySelector('.search-flyout-close.float-right.d-none.d-lg-block.circle-outline.icon-moreoptionsclose');
            if (closeButton) {closeButton.click();}
        """
            % origin
        )

        page.evaluate(js_script_select_origin_box)
        time.sleep(0.5)
        page.evaluate(js_script_enter_origin_airport)
        time.sleep(random.uniform(1.13, 1.5))

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_select_dest_box = (
            "var anchorElement = document.querySelector('#toAirportName'); if (anchorElement) {anchorElement.click();}"
        )
        js_script_enter_dest_airport = (
            """
            var searchInput = document.getElementById('search_input'); if (searchInput) {searchInput.value = '%s';} \
            var closeButton = document.querySelector('.search-flyout-close.float-right.d-none.d-lg-block.circle-outline.icon-moreoptionsclose'); \
            if (closeButton) {closeButton.click();}
        """
            % destination
        )
        page.evaluate(js_script_select_dest_box)
        time.sleep(0.5)
        page.evaluate(js_script_enter_dest_airport)
        time.sleep(random.uniform(1.13, 1.5))

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_open_calendar = "document.querySelector('.calenderDepartSpan').click()"
        page.evaluate(js_script_open_calendar)
        time.sleep(random.uniform(1.13, 1.5))

        months_until_departure_date = self.months_until_departure_date(departure_date)
        if months_until_departure_date > 0:
            js_script_scroll_date = "document.querySelectorAll('.monthSelector')[1].click()"
            for _ in range(months_until_departure_date):
                page.evaluate(js_script_scroll_date)
                time.sleep(0.2)

        js_script_select_date = """
            var element = document.querySelector("[data-date*='%s']");
            if (element) {
                element.click();
            }
        """ % departure_date.strftime(
            "%m/%d/%Y"
        )
        page.evaluate(js_script_select_date)
        print("date selected")
        time.sleep(1.5)

    def _select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        self.adults = adults

    def _select_oneway(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_tripType_dropdown = "var selectElement = document.querySelector('span[aria-owns=\"selectTripType-desc\"]'); selectElement.click();"
        js_script_select_OneWay = (
            "var selectElement = document.querySelector('li[id=\"ui-list-selectTripType1\"]'); selectElement.click();"
        )
        page.evaluate(js_script_tripType_dropdown)
        time.sleep(random.uniform(1.13, 1.5))
        page.evaluate(js_script_select_OneWay)
        time.sleep(random.uniform(1.13, 1.5))

    def _select_miles(self, *args, **kwargs) -> None:
        if self.miles_selected:
            pass
        else:
            page: Page = kwargs.get("page")
            # advanced_btn = page.locator('//a[@id="adv-search"]')
            # advanced_btn.wait_for(timeout=20000)
            # advanced_btn.click()
            # time.sleep(2)
            miles_btn = page.locator('//label[@id="milesLabel"]')
            miles_btn.wait_for(timeout=20000)
            miles_btn.click()
            self.miles_selected = True
            time.sleep(random.uniform(1.13, 1.5))
        # advanced_btn.click()
        # return
        # js_script_advanced_search = """
        #     var advaced_search = document.getElementById('adv-search');
        #     advaced_search.click();
        # """
        # page.evaluate(js_script_advanced_search)
        # time.sleep(random.uniform(1.13, 1.5))

        # js_script_check_miles = """
        #     var check_miles = document.getElementById('milesLabel');
        #     check_miles.click();
        # """
        # page.evaluate(js_script_check_miles)

    def _select_flexible_dates(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        flexible_is_checked = page.is_checked('input[id="chkFlexDate"]')
        if flexible_is_checked:
            js_script_check_miles = """
                var checkbox = document.getElementById('chkFlexDate');
                checkbox.checked = false;
                checkbox.dispatchEvent(new Event('change', { 'bubbles': true }));
            """
            page.evaluate(js_script_check_miles)

    def accept_cookie(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        # js_script_accept_cookie = """
        #     var accept_cookie = document.getElementById('privacy-btn-reject-all');
        #     accept_cookie.click();
        # """
        # page.evaluate(js_script_accept_cookie)
        # time.sleep(random.uniform(1.13, 1.5))
        try:
            cookie_btn = page.locator('//button[@id="privacy-btn-reject-all"]')
            cookie_btn.wait_for(timeout=5000)
            cookie_btn.click()
            logger.info(f"{self.AIRLINE.value}: Clicked accept cookie popup!")
        except Exception:
            logger.info(f"{self.AIRLINE.value}: Accept cookie popup not found!")
            pass

    def get_user_agent(self):
        version1 = random.choice(range(124, 130))
        flatform = random.choice([
            # somehow VS only works with Mac User agent at the moment - 20241003
            "(Macintosh; Intel Mac OS X 10_15_7)",
            "(Macintosh; Intel Mac OS X 10_15_6)",
            "(Macintosh; Intel Mac OS X 10_15_5)",
            "(Macintosh; Intel Mac OS X 10_15_4)",
            "(Macintosh; Intel Mac OS X 10_15_3)",
            "(Windows NT 10.0; Win64; x64)"
        ])
        user_agent = f"Mozilla/5.0 {flatform} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version1}.0.0.0 Safari/537.36"
        return user_agent

    def setup_driver(self, *args, **kwargs):
        playwright: SyncPlaywright = kwargs.get("playwright")
        default_user_agent = self.get_user_agent()
        user_agent = kwargs.get("user_agent", default_user_agent)
        proxy_vals = self.get_proxy()
        logger.info(f"setting up driver with user_agent {user_agent}.")
        proxy = None
        if proxy_vals:
            proxy_host = proxy_vals.get("ip")  # rotating proxy or host
            proxy_port = proxy_vals.get("port")  # port
            proxy_user = proxy_vals.get("user")  # username
            proxy_pass = proxy_vals.get("pwd")
            proxy = {
                "server": f"{proxy_host}:{proxy_port}",
                "username": proxy_user,
                "password": proxy_pass,
            }
            logger.info(f"running with proxy: {proxy}")

        # disable navigator.webdriver:true flag
        args = [
            "--disable-blink-features=AutomationControlled",
            f"--disable-extensions-except={self.WEB_RTC_PATH}",
            f"--load-extension={self.WEB_RTC_PATH}",
        ]
        browser = playwright.chromium.launch_persistent_context(
            args=args,
            proxy=proxy,
            user_data_dir=self._user_data_dir,
            headless=False,
            slow_mo=100,  # slow down step as human behavior,
            timezone_id="Canada/Atlantic",
            geolocation={
                "latitude": 43.651070,
                "longitude": -79.347015,
                "accuracy": 90,
            },
            user_agent=user_agent
        )
        browser.set_default_navigation_timeout(200 * 1000)
        
        return browser
    
    def intercept_request(self, route, request):

        if "/shop/ow/search" in request.url and request.method == "POST":
            route.continue_()
            response_received = False

            while not response_received:
                try:
                    response = request.response()
                    if response:
                        response_received = True
                        headers = request.all_headers()
                        payload = request.post_data_json
                        insert_target_headers(headers, self.TARGET, payload)
                except Exception as err:
                    logger.info(f"{self.AIRLINE.value}: Waiting for response: {err}")

            try:
                response_body = response.json()
                status_code = response.status
                logger.info(f"{self.AIRLINE.value}: Response from {request.url}: Status Code - {status_code}")

                if response_body:
                    self.intercepted_response = response_body
                    return

            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")
            finally:
                self.intercepted = True
        else:
            return self.intercept_route(route)
        
    def _submit(self, *args, **kwargs):
        self.intercepted = False
        self.intercepted_response = None
        page: Page = kwargs.get("page")
        page.route("**", lambda route, request: self.intercept_request(route, request))

        self._select_flexible_dates(*args, **kwargs)
        page: Page = kwargs.get("page")
        js_script_press_submit = "document.querySelector('#btnSubmit').click()"
        page.evaluate(js_script_press_submit)
        
        # page.click("button#btnSubmit")
        # time.sleep(5)

        # maxium time to wait for data is 60s
        waited_time = max_time = 120
        while not self.intercepted_response and max_time > 0:
            try:
                loading_spinner_count = page.locator("//app-interstitial-page-view").count()
                logger.info(
                    f"{self.AIRLINE.value}: spinner count: {loading_spinner_count} - "
                    f"waiting for loading flights data, {max_time}s remaining"
                )
                advanced_search_header_count = page.locator('//h1[@class="advanced-search-heading"]').count()
                if advanced_search_header_count \
                        and not loading_spinner_count \
                        and (waited_time - max_time) > 5: # must wait more than 5s:
                    logger.info(f"{self.AIRLINE.value}: Search Failed!")
                    raise AirlineCrawlerException(
                        airline=self.AIRLINE,
                        message=f"{self.AIRLINE.value}: Search Failed!",
                        reason="Found advanced_search_header"
                        )

                if self.intercepted and not self.intercepted_response and not loading_spinner_count:
                    logger.info(f"{self.AIRLINE.value}: Search Failed!")
                    raise AirlineCrawlerException(
                        airline=self.AIRLINE,
                        message=f"{self.AIRLINE.value}: Search Failed!",
                        reason="Can't get intercepted_response"
                    )
            except AirlineCrawlerException as e:
                print(f"Error: {e}")
                raise e

            except Exception as e:
                print(f"Error: {e}")
            finally:
                time.sleep(random.uniform(1.13, 1.5))
                max_time -= 1

        if max_time == 0:
            logger.error(f"{self.AIRLINE.value}: waited for {waited_time}s but no results, might get blocked")
            raise NoSearchResult(airline=self.AIRLINE)

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
                            amount=float(amount.replace(",", "")),
                            currency=currency,
                        ),
                    }
            except Exception as e:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return points_by_fare_names

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
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
                    logger.info(f"{self.AIRLINE.value}: extract_flight_detail error: {e}...")
                    continue
                    # raise e
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


if __name__ == "__main__":
    # import threading
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = VirginAtlanticPlaywrightWireCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=27)

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

    run("LHR", "LAX", c.CabinClass.All)
    # run("PVG", "BRU", c.CabinClass.Economy)
    # run("JFK", "LHR", c.CabinClass.Economy)
    # run("LAX", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Economy)
    # asyncio.run(run("YVR", "YYZ", c.CabinClass.Economy))
    # run("KUL", "YYZ", c.CabinClass.First)
