import datetime
import logging
import time
from typing import Iterator, List, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement

from src import constants as c
from src.base import SeleniumBasedAirlineCrawler
from src.dl.constants import CabinClassMapping
from src.exceptions import AirportNotSupported, NoSearchResult
from src.schema import CashFee, Flight, FlightSegment
from src.utils import convert_k_to_float, parse_date, parse_time

logger = logging.getLogger(__name__)


class DeltaAirlineSeleniumBasedCrawler(SeleniumBasedAirlineCrawler):
    AIRLINE = c.Airline.DeltaAirline
    REQUIRED_LOGIN = False
    HOME_PAGE_URL = "https://www.delta.com/"

    def _select_oneway(self) -> None:
        self.click_once_clickable(
            by=By.XPATH,
            identifier="//span[@aria-labelledby='selectTripType-label']",
            timeout=c.MEDIUM_SLEEP,
        )
        self.click_once_clickable(
            by=By.XPATH,
            identifier="//ul[@id='selectTripType-desc']/li[@data='1']",
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_miles(self) -> None:
        self.click_once_clickable(
            by=By.XPATH,
            identifier='//input[@id="shopWithMiles"]',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//a[@id='fromAirportName']",
            timeout=c.MEDIUM_SLEEP,
        )
        origin_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[@id='search_input']",
            timeout=c.MEDIUM_SLEEP,
        )
        origin_input.send_keys(Keys.CONTROL, "a")
        origin_input.send_keys(Keys.BACKSPACE * 4)
        self.human_typing(origin_input, origin)
        time.sleep(c.LOW_SLEEP)

        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//div[@class='search-result-container']" "//ul/li[contains(@class, 'airport-list')][1]/a",
                timeout=c.MEDIUM_SLEEP,
            )
        except (NoSuchElementException, TimeoutException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=origin)

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//a[@id='toAirportName']",
            timeout=c.MEDIUM_SLEEP,
        )
        destination_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[@id='search_input']",
            timeout=c.MEDIUM_SLEEP,
        )

        destination_input.send_keys(Keys.CONTROL, "a")
        destination_input.send_keys(Keys.BACKSPACE * 4)
        self.human_typing(destination_input, destination)
        time.sleep(c.LOW_SLEEP)
        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//div[@class='search-result-container']" "//ul/li[contains(@class, 'airport-list')]/a",
                timeout=c.MEDIUM_SLEEP,
            )
        except (NoSuchElementException, TimeoutException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=destination)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        departure_date_str = departure_date.strftime("%m/%d/%Y")
        try:
            self.click_once_clickable(
                by=By.XPATH,
                identifier="//div[@id='input_departureDate_1' or @id='input_returnDate_1']",
                timeout=c.MEDIUM_SLEEP,
            )

            next_mon_btn = self.wait_until_clickable(
                by=By.XPATH,
                identifier="//div[@class='calPrevNextBtnCont']/a[@aria-label='Next']",
                timeout=c.MEDIUM_SLEEP,
            )
            while True:
                try:
                    self.click_once_clickable(
                        by=By.XPATH,
                        identifier=f"//table[@class='dl-datepicker-calendar']"
                        f"//td/a[contains(@data-date, '{departure_date_str}')]",
                        timeout=c.LOW_SLEEP,
                    )
                    break
                except TimeoutException:
                    next_mon_btn.click()
        except ElementClickInterceptedException:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//button[contains(@class, 'gdpr-banner-accept-btn')]",
                timeout=c.LOW_SLEEP,
            )

    def accept_cookie(self):
        try:
            self.find_element(
                by=By.XPATH,
                identifier='//ngc-cookie-banner//div[contains(@class, "close-cookie")]//button',
            )
        except NoSuchElementException:
            pass

    def _submit(self) -> None:
        self.click_once_clickable(
            by=By.XPATH,
            identifier="//button[@id='btn-book-submit']",
            timeout=c.MEDIUM_SLEEP,
        )

    def continue_search(self) -> None:
        try:
            self.click_once_clickable(
                by=By.XPATH,
                identifier="//idp-button[contains(@class, 'flex-dates-continue-btn')]//button",
                timeout=c.HIGH_SLEEP * 2,
            )
        except (NoSuchElementException, TimeoutException):
            raise NoSearchResult(airline=self.AIRLINE)

    def load_more(self) -> None:
        while True:
            try:
                self.click_once_clickable(
                    by=By.XPATH,
                    identifier="//div[contains(@class, 'search-results__load-more-btn')]"
                    "//button[contains(@class, 'idp-btn')]",
                    timeout=c.MEDIUM_SLEEP,
                )
            except TimeoutException:
                break

    def extract_points(
        self, flight_row_element: WebElement, cabin_classes: List[Tuple[int, str]]
    ) -> List[Tuple[str, float, CashFee]]:
        logger.info(f"{self.AIRLINE.value}: Found points...")
        ret = []
        fares = self.find_elements(
            by=By.XPATH,
            identifier=".//idp-fare-cell-desktop",
            from_element=flight_row_element,
        )
        for cabin_class_index, brand_name in cabin_classes:
            fare_info_element = fares[cabin_class_index]
            try:
                points = self.get_text_from_element(
                    by=By.XPATH,
                    identifier=".//div[@class='fare-cell-miles-value']",
                    from_element=fare_info_element,
                )
                points = convert_k_to_float(points)
                currency = self.get_text_from_element(
                    by=By.XPATH,
                    identifier=".//span[@class='fare-cell-currency']",
                    from_element=fare_info_element,
                )
                amount = self.get_text_from_element(
                    by=By.XPATH,
                    identifier=".//span[contains(@class, 'fare-cell-rounded-amount')]",
                    from_element=fare_info_element,
                )
                ret.append((brand_name, points, CashFee(currency=currency, amount=amount)))
            except NoSuchElementException:
                continue
        return ret

    def extract_flight_detail(
        self,
        flight_row_element: WebElement,
        departure_date: datetime.date,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: extracting flight details...")
        # click detail button
        self.find_and_click_element(
            by=By.XPATH,
            identifier='.//idp-flight-card-footer//div[contains(@class, "flight-card-footer__links")]'
            '//a[contains(@class, "details-link")]',
            from_element=flight_row_element,
        )

        flight_segments_elements = self.wait_until_all_visible(
            by=By.XPATH,
            identifier="//div[contains(@class, 'idp-dialog__content')]"
            "//div[contains(@class, 'flight-specific-detail-modal')]"
            "//idp-segment-info-accordion//div[contains(@class, 'idp-summary-outer')]",
            timeout=c.MEDIUM_SLEEP,
        )

        segments: List[FlightSegment] = []
        for segment_index, segment_element in enumerate(flight_segments_elements):
            segment_item_header_container = segment_element.find_element(
                By.XPATH,
                './/div[contains(@class, "idp-summary__accordion")]'
                '//idp-accordion-header//div[contains(@class, "accordion-header-head-wrapper")]'
                '/div[@class="accordion-header-head"]',
            )
            segment_item_body_container = segment_element.find_element(
                By.XPATH,
                './/div[contains(@class, "idp-summary__accordion-content")]' '/div[@class="idp-summary__box"]',
            )

            segment_item_left = segment_item_body_container.find_element(
                By.XPATH, './/div[@class="idp-summary__box-left"]'
            )

            segment_flight_leg_info = segment_item_left.find_element(
                By.XPATH, './/idp-accordion-flight-leg-info/section[contains(@class, "flight-leg-info")]'
            )

            segment_departure_time = self.get_text_from_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "flight-leg-info-header")]',
                from_element=segment_flight_leg_info,
            )
            segment_departure_time = parse_time(segment_departure_time, "%I:%M %p")

            segment_arrival_time = self.get_text_from_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "flight-leg-info-footer")]',
                from_element=segment_flight_leg_info,
            )
            segment_arrival_time = parse_time(segment_arrival_time, "%I:%M %p")

            segment_leg_airport_info = segment_flight_leg_info.find_element(
                By.XPATH,
                './/div[contains(@class, "flight-leg-info-content")]' '/div[@class="flight-leg-info-content-desc"]',
            )

            airport_code_elements = segment_leg_airport_info.find_elements(
                By.XPATH, './/div[contains(@class, "flight-leg-info-content-desc-code")]'
            )

            depart_airline_code_element = airport_code_elements[0]
            segment_origin = self.get_text(depart_airline_code_element)

            arrival_airline_code_element = airport_code_elements[1]
            segment_destination = self.get_text(arrival_airline_code_element)

            segment_item_right = segment_item_body_container.find_element(
                By.XPATH, './/div[@class="idp-summary__box-right"]'
            )

            segment_aircraft = self.get_text_from_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "idp-summary__box-fleet")]',
                from_element=segment_item_right,
            )

            segment_flight_number = self.get_text_from_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "accordion-header-head-number")]',
                from_element=segment_item_header_container,
            )

            segment_departure_date = self.get_text_from_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "accordion-header-head-date")]/span',
                from_element=segment_item_header_container,
            )
            segment_departure_date = parse_date(segment_departure_date, "%a, %b %d")
            segment_departure_date = datetime.date.fromisoformat(segment_departure_date).replace(
                year=departure_date.year
            )
            segment_departure_date = segment_departure_date.isoformat()

            try:
                segment_arrival_date = self.get_text_from_element(
                    by=By.XPATH,
                    identifier='.//div[contains(@class, "accordion-header-head-date")]/div',
                    from_element=segment_item_header_container,
                )
                segment_arrival_date = segment_arrival_date.lower()[len("arrives on ") :]
                segment_arrival_date = parse_date(segment_arrival_date, "%a, %b %d")
                segment_arrival_date = datetime.date.fromisoformat(segment_arrival_date).replace(
                    year=departure_date.year
                )
                segment_arrival_date = segment_arrival_date.isoformat()
            except NoSuchElementException:
                segment_arrival_date = segment_departure_date

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
                    duration="",
                    aircraft=segment_aircraft,
                    flight_number=segment_flight_number,
                    carrier="",
                )
            )

        self.find_and_click_element(
            by=By.XPATH,
            identifier="//idp-simple-modal[contains(@class, 'flight-details-modal')]"
            "//div[contains(@class, 'idp-simple-modal__body')]/div[contains(@class, 'idp-dialog__header')]"
            "/button[contains(@class, 'idp_dialog__close')]",
        )
        return segments

    def extract(
        self, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        try:
            search_results = self.wait_until_all_visible(
                by=By.XPATH,
                identifier='//idp-flight-grid/div[contains(@class, "flight-results-grid")]',
                timeout=c.HIGHEST_SLEEP * 2,
            )
        except (TimeoutException, NoSuchElementException):
            raise NoSearchResult(airline=self.AIRLINE)

        brand_cabin_types_elements = self.find_elements(
            by=By.XPATH,
            identifier="//div[@class='brand-cabin-type']//a",
        )

        brand_cabin_classes = [
            (index, brand_cabin)
            for index, brand_cabin_type_element in enumerate(brand_cabin_types_elements)
            if (brand_cabin := self.get_text(brand_cabin_type_element)) in CabinClassMapping[cabin_class]
        ]
        if not brand_cabin_classes:
            raise NoSearchResult(airline=self.AIRLINE)

        logger.info(f"{self.AIRLINE.value}: Found {len(search_results)} flights...")
        for index, flight_row_element in enumerate(search_results):
            fares = self.extract_points(flight_row_element, brand_cabin_classes)
            if not fares:
                continue

            segments = self.extract_flight_detail(flight_row_element, departure_date)
            for fare_name, points, cash_fee in fares:
                yield Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=str(cabin_class.value),
                    airline_cabin_class=fare_name,
                    points=points,
                    cash_fee=cash_fee,
                    segments=segments,
                )

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        self.continue_search()
        self.load_more()
        for flight in self.extract(departure_date, cabin_class):
            yield flight


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = DeltaAirlineSeleniumBasedCrawler()
        travel_departure_date = datetime.date.today() + datetime.timedelta(days=14)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=travel_departure_date.isoformat(),
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

    # run("PVG", "PNG", c.CabinClass.Economy)
    # run("JFK", "LAX", c.CabinClass.Economy)
    # run("JFK", "LAX", c.CabinClass.PremiumEconomy)
    run("JFK", "LAX", c.CabinClass.Business)
    # run("JFK", "LAX", c.CabinClass.First)
