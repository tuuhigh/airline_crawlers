import datetime
import json
import logging
import random
import time
from collections import namedtuple
from typing import Iterator, List, Optional, Tuple
from isodate import duration_isoformat

from undetected_playwright.sync_api import TimeoutError

from playwright.sync_api import Locator, Page
from src import constants as c
from src.dl.constants import CabinClassMapping
from src.exceptions import NoSearchResult
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    convert_time_string_to_iso_format,
    extract_flight_number,
    parse_date,
    convert_human_time_to_seconds,
)

logger = logging.getLogger(__name__)
GeoLocationConfiguration = namedtuple("GeoLocationConfiguration", ("proxy_host", "proxy_port", "home_page_url"))
GeoLocationConfigurations = [
    GeoLocationConfiguration(
        proxy_host="us.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com"
    ),
    GeoLocationConfiguration(
        proxy_host="ca.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/ca/en"
    ),
    GeoLocationConfiguration(
        proxy_host="gb.smartproxy.com", proxy_port="30001", home_page_url="https://www.delta.com/gb/en"
    ),
    GeoLocationConfiguration(
        proxy_host="nl.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com/eu/en"
    ),
    GeoLocationConfiguration(
        proxy_host="de.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/eu/en"
    ),
    GeoLocationConfiguration(
        proxy_host="fr.smartproxy.com", proxy_port="40001", home_page_url="https://www.delta.com/fr/en"
    ),
    GeoLocationConfiguration(
        proxy_host="mx.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/mx/en"
    ),
    GeoLocationConfiguration(
        proxy_host="br.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com/br/en"
    ),
]


class DeltaAirlinePlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.DeltaAirline
    REQUIRED_LOGIN = False
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smart_proxy_host, self.smart_proxy_port, self.home_page_url = random.choice(GeoLocationConfigurations)

    def get_proxy(self):
        return {
            "ip": self.smart_proxy_host,
            "port": self.smart_proxy_port,
            "user": "spyc5m5gbs",
            "pwd": "puFNdLvkx6Wcn6h6p8",
        }

    def _select_locale(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        try:
            page.click(".btn-keep.btn.btn-outline-secondary-cta.rounded-0", timeout=3000)
            logger.info(f"{self.AIRLINE.value}: English selected")
        except Exception:
            logger.info(f"{self.AIRLINE.value}: No need to select language button")

    def _select_miles(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        miles_is_checked = page.is_checked('input[id="shopWithMiles"]')
        if not miles_is_checked:
            js_script_check_miles = """
                var checkbox = document.getElementById('shopWithMiles');
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change', { 'bubbles': true }));
            """
            page.evaluate(js_script_check_miles)

    def _select_oneway(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_tripType_dropdown = "var selectElement = document.querySelector('span[aria-owns=\"selectTripType-desc\"]'); selectElement.click();"
        js_script_select_OneWay = (
            "var selectElement = document.querySelector('li[id=\"ui-list-selectTripType1\"]'); selectElement.click();"
        )
        page.evaluate(js_script_tripType_dropdown)
        time.sleep(1)
        page.evaluate(js_script_select_OneWay)
        time.sleep(1)

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
        time.sleep(1)

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
        time.sleep(1)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_open_calendar = "document.querySelector('.calenderDepartSpan').click()"
        page.evaluate(js_script_open_calendar)
        time.sleep(1)

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

    def _select_flexible_dates(self, *args, **kwargs) -> None:
        pass

    def _select_passengers(self, *args, **kwargs):
        pass

    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click('xpath=//button[@id="btn-book-submit"]')
        time.sleep(3)

    def continue_search(self, page: Page):
        logger.info(f"{self.AIRLINE.value}: Continue Search...")
        try:
            page.wait_for_load_state(timeout=30000)
            # check flight availability on flexible page
            logger.info(f"{self.AIRLINE.value}: Checking if it lands on Flexible dates Page...")
            selected_date_element = page.locator(
                "//div[contains(@class, 'flexible-dates-grid-row')]/div[contains(@class, 'isSelected') and contains(@class, 'isPriceCell')]"
            )
            selected_date_element.wait_for(timeout=30000)
            is_flexible_dates_page = True
        except TimeoutError:
            is_flexible_dates_page = False

        if is_flexible_dates_page:
            logger.info(f"{self.AIRLINE.value}: On flexible dates page, checking availability...")

            lowest_price_text = self.get_text(selected_date_element)
            if lowest_price_text.lower() == "not available":
                logger.info(f"{self.AIRLINE.value}: No available flights...")
                raise NoSearchResult(airline=self.AIRLINE, reason="Not available flights on Flexible Page")

            try:
                # accept policy
                logger.info(f"{self.AIRLINE.value}: Check if policy popup displayed...")
                accept_cookie_buton = page.locator("//button[@class='btn btn-secondary-cta']")
                accept_cookie_buton.wait_for(timeout=10000)
                accept_cookie_buton.click()
            except TimeoutError:
                pass
            
            try:
                # accept cookies
                logger.info(f"{self.AIRLINE.value}: Have available flights on flexible dates page, continue...")
                accept_cookie_buton = page.locator(".btn-danger.gdpr-banner-btn.gdpr-banner-accept-btn")
                accept_cookie_buton.wait_for(timeout=3000)
                accept_cookie_buton.click()
            except TimeoutError:
                pass

            try:
                # Continue to search
                logger.info(f"{self.AIRLINE.value}: Click continue buttons...")
                continue_button = page.locator("//idp-button[contains(@class, 'flex-dates-continue-btn')]//button")
                continue_button.wait_for(timeout=3000)
                continue_button.click()
                time.sleep(3)
            except TimeoutError:
                pass
        else:
            try:
                advance_search = page.locator("//div[@class='idp-advance-search']/idp-error-message")
                advance_search.wait_for(timeout=3000)
                raise NoSearchResult(airline=self.AIRLINE, reason="Does not support this route")
            except TimeoutError as e:
                raise e

    def load_more(self, page: Page) -> None:
        page.wait_for_load_state()
        try:
            logger.info(f"{self.AIRLINE.value}: Waiting for search result...")
            search_result = page.locator("//idp-flight-grid")
            search_result.wait_for(timeout=60000)
        except TimeoutError as e:
            raise NoSearchResult(airline=self.AIRLINE, reason=f"{e}")

        try:
            logger.info(f"{self.AIRLINE.value}: Checking if there is more button...")
            load_more_button = page.locator(
                "//div[contains(@class, 'search-results__load-more-btn')]//button[contains(@class, 'idp-btn')]"
            )
            load_more_button.wait_for(timeout=1000)
            load_more_button.click()
        except Exception:
            pass

    def extract_points(
        self, page: Page, flight_row_element: Locator, cabin_classes: List[Tuple[int, str]]
    ) -> List[Tuple[str, float, CashFee]]:
        logger.info(f"{self.AIRLINE.value}: Found points...")
        ret = []
        fares = flight_row_element.locator("//idp-fare-cell-desktop")
        duration = self.get_text(flight_row_element.locator("//div[@class='flight-duration']"))
        duration_s = convert_human_time_to_seconds(duration)

        for cabin_class_index, brand_name in cabin_classes:
            fare_info_element = fares.nth(cabin_class_index)
            try:
                points = self.get_text(fare_info_element.locator("//div[@class='fare-cell-miles-value']"))
                points = convert_k_to_float(points)
                currency = self.get_text(fare_info_element.locator("//span[@class='fare-cell-currency']"))
                amount = self.get_text(
                    fare_info_element.locator("//span[contains(@class, 'fare-cell-rounded-amount')]")
                )
                ret.append((brand_name, points, CashFee(currency=currency, amount=amount), duration_s))
            except Exception:
                continue
        return ret

    def extract_flight_detail(
        self,
        page: Page,
        flight_row_element: Locator,
        departure_date: datetime.date,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: extracting flight details...")
        # segments = []
        # origin = self.get_text(flight_row_element.locator('//div[contains(@class, "flight-card-path__start")]'))
        # destination = self.get_text(flight_row_element.locator('//div[contains(@class, "flight-card-path__end")]'))
        # layover = self.get_text(flight_row_element.locator("//div[contains(@class, 'flight-card-path__layover')]"))
        # flight_numbers = self.get_text(flight_row_element.locator('//div[contains(@class, "flight-number")]'))
        # flight_numbers = flight_numbers.split(",")
        # departure_arrival_times = flight_row_element.locator('//div[@class="schedule-time"]')
        # departure_time = convert_time_string_to_iso_format(self.get_text(departure_arrival_times.first))
        # arrival_time = convert_time_string_to_iso_format(self.get_text(departure_arrival_times.last))
        # next_day = self.get_text(flight_row_element.locator('//div[contains(@class, "next-day-schedule")]'))
        # if next_day:
        #     arrival_date = datetime.datetime.strptime(next_day, "%a %d %b")
        #     arrival_date = arrival_date.replace(year=departure_date.year)
        # else:
        #     arrival_date = departure_date

        # click detail button
        detail_button = flight_row_element.locator(
            '//idp-flight-card-footer//div[contains(@class, "flight-card-footer__links")]'
            '//a[contains(@class, "details-link")]'
        )
        detail_button.click()
        while True:
            flight_segments_elements = page.locator(
                "//div[contains(@class, 'flight-specific-detail-modal')]"
                "//idp-segment-info-accordion//div[contains(@class, 'idp-summary-outer')]",
            ).all()
            if len(flight_segments_elements) > 0:
                break
            time.sleep(1)

        segments: List[FlightSegment] = []
        for segment_index, segment_element in enumerate(flight_segments_elements):
            segment_item_header_container = segment_element.locator(
                '//div[contains(@class, "idp-summary__accordion")]'
                '//idp-accordion-header//div[contains(@class, "accordion-header-head-wrapper")]'
                '/div[@class="accordion-header-head"]',
            )
            segment_item_body_container = segment_element.locator(
                '//div[contains(@class, "idp-summary__accordion-content")]/div[@class="idp-summary__box"]',
            )

            segment_item_left = segment_item_body_container.locator('//div[@class="idp-summary__box-left"]')

            segment_flight_leg_info = segment_item_left.locator(
                '//idp-accordion-flight-leg-info/section[contains(@class, "flight-leg-info")]'
            )

            segment_departure_time = segment_flight_leg_info.locator('//div[contains(@class, "flight-leg-info-header")]').inner_text()
            segment_departure_time = convert_time_string_to_iso_format(segment_departure_time)
            segment_arrival_time = segment_flight_leg_info.locator('//div[contains(@class, "flight-leg-info-footer")]').inner_text()
            segment_arrival_time = convert_time_string_to_iso_format(segment_arrival_time)

            segment_leg_airport_info = segment_flight_leg_info.locator(
                '//div[contains(@class, "flight-leg-info-content")]/div[@class="flight-leg-info-content-desc"]',
            )

            airport_code_elements = segment_leg_airport_info.locator(
                '//div[contains(@class, "flight-leg-info-content-desc-code")]'
            ).all()

            depart_airline_code_element = airport_code_elements[0]
            segment_origin = self.get_text(depart_airline_code_element)

            arrival_airline_code_element = airport_code_elements[1]
            segment_destination = self.get_text(arrival_airline_code_element)
            
            duration = segment_item_left.locator("//div[@class='flight-leg-info-content-desc-time']").inner_text()
            duration_s = convert_human_time_to_seconds(duration)
            duration_time = None
            if duration_s:
                duration_time = duration_isoformat(datetime.timedelta(seconds=duration_s))
                
            segment_item_right = segment_item_body_container.locator('//div[@class="idp-summary__box-right"]')
            segment_aircraft = self.get_text(
                segment_item_right.locator('//div[contains(@class, "idp-summary__box-fleet")]')
            )

            segment_flight_number = self.get_text(
                segment_item_header_container.locator('//div[contains(@class, "accordion-header-head-number")]')
            )
            segment_carrier, segment_flight_number = extract_flight_number(segment_flight_number)

            segment_departure_date = self.get_text(segment_item_header_container.locator('//div[contains(@class, "accordion-header-head-date")]/span'))
            segment_departure_date = parse_date(segment_departure_date, "%a, %b %d")
            if segment_departure_date:
                segment_departure_date = datetime.date.fromisoformat(str(segment_departure_date)).replace(
                    year=departure_date.year
                )
                segment_departure_date = segment_departure_date.isoformat()

            try:
                segment_arrival_date = self.get_text(segment_item_header_container.locator('//div[contains(@class, "accordion-header-head-date")]/div'))
                segment_arrival_date = segment_arrival_date.lower()[len("arrives on ") :]
                segment_arrival_date = parse_date(segment_arrival_date, "%a, %b %d")
                segment_arrival_date = datetime.date.fromisoformat(segment_arrival_date).replace(
                    year=departure_date.year
                )
                segment_arrival_date = segment_arrival_date.isoformat()
            except Exception:
                segment_arrival_date = segment_departure_date
                
            layover_duration = self.get_text(segment_element.locator("//div[@class='accordion-layover-info-time']"))
            layover_duration_s = convert_human_time_to_seconds(layover_duration)
            layover_time = None
            if layover_duration_s:
                layover_time = duration_isoformat(datetime.timedelta(seconds=layover_duration_s))

            segments.append(
                FlightSegment(
                    origin=segment_origin,
                    destination=segment_destination,
                    departure_date=segment_departure_date,
                    departure_time=segment_departure_time,
                    departure_timezone="",
                    arrival_date=segment_arrival_date,
                    arrival_time=segment_arrival_time,
                    arrival_timezone="",
                    duration=duration_time,
                    aircraft=segment_aircraft,
                    flight_number=segment_flight_number,
                    carrier=segment_carrier,
                    layover_time=layover_time
                )
            )

        close_button = page.locator(
            "//idp-simple-modal[contains(@class, 'flight-details-modal')]"
            "//div[contains(@class, 'idp-simple-modal__body')]/div[contains(@class, 'idp-dialog__header')]"
            "/button[contains(@class, 'idp_dialog__close')]"
        )
        close_button.click()
        return segments

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        self.continue_search(page)
        self.load_more(page)

        search_results = page.locator('//idp-flight-grid/div[contains(@class, "flight-results-grid")]').all()
        brand_cabin_types_elements = page.locator("//div[@class='brand-cabin-type']//a").all()

        brand_cabin_classes = [
            (index, brand_cabin)
            for index, brand_cabin_type_element in enumerate(brand_cabin_types_elements)
            if (brand_cabin := self.get_text(brand_cabin_type_element)) in CabinClassMapping[cabin_class]
        ]
        if not brand_cabin_classes:
            raise NoSearchResult(airline=self.AIRLINE)

        logger.info(f"{self.AIRLINE.value}: Found {len(search_results)} flights...")
        for index, flight_row_element in enumerate(search_results):
            fares = self.extract_points(page, flight_row_element, brand_cabin_classes)
            if not fares:
                continue

            segments = self.extract_flight_detail(page, flight_row_element, departure_date)
            for fare_name, points, cash_fee, duration in fares:
                yield Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=str(cabin_class.value),
                    airline_cabin_class=fare_name,
                    points=points,
                    cash_fee=cash_fee,
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration))
                )


if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = DeltaAirlinePlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=24)

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
    # run("LHR", "PEK", c.CabinClass.PremiumEconomy)
    run("JFK", "LHR", c.CabinClass.Economy)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
