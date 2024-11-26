import datetime
import logging
import random
import re
import time
from typing import Dict, Iterator, List, Optional, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement

from src import constants as c
from src.ac.constants import CabinClassCodeMapping
from src.base import SeleniumBasedAirlineCrawler
from src.exceptions import CannotContinueSearch, NoSearchResult
from src.schema import CashFee, Flight, FlightSegment
from src.types import SmartCabinClassType
from src.utils import convert_k_to_float, extract_digits, extract_iso_time

logger = logging.getLogger(__name__)


class AirCanadaSeleniumBasedCrawler(SeleniumBasedAirlineCrawler):
    AIRLINE = c.Airline.AirCanada
    REQUIRED_LOGIN = False
    HOME_PAGE_URL = "https://www.aircanada.com/us/en/aco/home.html"

    def check_page(self):
        pass
        # for _ in range(3):
        #     try:
        #         self.wait_until_clickable(
        #             by=By.XPATH,
        #             identifier="//input[contains(@id, 'bkmgFlights_origin_trip_1')]",
        #             timeout=c.MEDIUM_SLEEP * 2,
        #         )
        #         break
        #     except (TimeoutException, NoSuchElementException):
        #         logger.info("cannot find airport element, refreshing page...")
        #         self.driver.refresh()

    def _select_oneway(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//div[@id='bkmg-tab-content-flight']//input[@id='bkmgFlights_tripTypeSelector_O']",
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_miles(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier='//abc-checkbox[contains(@class, "search-type-toggle-checkbox")]'
            '//input[@id="bkmgFlights_searchTypeToggle"]',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        origin_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[contains(@id, 'bkmgFlights_origin_trip_1')]",
            timeout=c.MEDIUM_SLEEP * 2,
        )
        self.click_element(origin_input)
        self.move_mouse()
        origin_input.send_keys(Keys.CONTROL, "a")
        self.human_typing(origin_input, origin)
        time.sleep(c.LOW_SLEEP)

        self.click_once_presence(
            by=By.XPATH,
            identifier='//ul[@id="bkmgFlights_origin_trip_1OptionsPanel"]' '/li[1]//div[@class="location-info-main"]',
            timeout=c.MEDIUM_SLEEP * 2,
        )

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        destination_input = self.wait_until_presence(
            by=By.XPATH,
            identifier='//input[contains(@id, "bkmgFlights_destination_trip")]',
            timeout=c.LOW_SLEEP,
        )
        self.click_element(destination_input)
        self.move_mouse()
        destination_input.send_keys(Keys.CONTROL, "a")
        self.human_typing(destination_input, destination)
        time.sleep(c.LOW_SLEEP)
        self.click_once_presence(
            by=By.XPATH,
            identifier='//ul[@id="bkmgFlights_destination_trip_1OptionsPanel"]'
            '/li[1]//div[@class="location-info-main"]',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        departure_date_element = self.wait_until_presence(
            by=By.XPATH,
            identifier='//input[@id="bkmgFlights_travelDates_1"]',
            timeout=c.MEDIUM_SLEEP,
        )
        self.click_element(departure_date_element)
        time.sleep(0.5)
        months_until_departure_date = self.months_until_departure_date(departure_date)
        if months_until_departure_date > 0:
            for _ in range(months_until_departure_date):
                self.driver.execute_script("document.getElementById('bkmgFlights_travelDates_1_nextMonth').click()")
                time.sleep(0.2)

        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier=f"//div[@id='bkmgFlights_travelDates_1-date-{departure_date.isoformat()}']",
                timeout=c.LOW_SLEEP,
            )
        except Exception as e:
            raise e

    def _select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        if adults > 1:
            passenger_element = self.wait_until_presence(
                by=By.XPATH,
                identifier='//button[@id="bkmgFlights_selectTravelers"]',
                timeout=c.MEDIUM_SLEEP,
            )
            self.click_element(passenger_element)
            adult_element = self.wait_until_presence(
                by=By.XPATH,
                identifier='//button[@id="bkmgFlights_selectTravelers_removeTraveler_ADT"]',
                timeout=c.MEDIUM_SLEEP,
            )
            for _ in range(adults - 1):
                self.click_element(adult_element)
                time.sleep(random.uniform(0.1, 0.5))

    def accept_cookie(self):
        try:
            self.find_and_click_element(
                by=By.XPATH,
                identifier='//ngc-cookie-banner//div[contains(@class, "close-cookie")]//button',
            )
        except NoSuchElementException:
            pass

    def _submit(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//button[@id='bkmgFlights_findButton']",
            timeout=c.MEDIUM_SLEEP,
        )

    def continue_search(self) -> None:
        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//abc-button//button[@id='confirmrewards']",
                timeout=c.MEDIUM_SLEEP,
            )
            logger.info(f"{self.AIRLINE.value}: Close primary cookie box...")

            self.click_once_presence(
                by=By.XPATH,
                identifier="//mat-dialog-container//kilo-simple-lightbox//div[@id='mat-dialog-title-0']"
                "//span[@aria-label='Close']",
                timeout=c.HIGHEST_SLEEP * 3,
            )
            logger.info(f"{self.AIRLINE.value}: Close secondary cookie box...")
        except (TimeoutException, NoSuchElementException) as e:
            raise CannotContinueSearch(airline=self.AIRLINE, reason=f"{e}")

    def extract_flight_detail(
        self, flight_row_element: WebElement, departure_date: datetime.date
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        # click detail element
        self.find_and_click_element(
            by=By.XPATH,
            identifier='.//div[contains(@class, "block-body")]//div[contains(@class, "details-row")]'
            '//span[contains(@class, "links")]//a[contains(@class, "detail-link")]',
            from_element=flight_row_element,
        )
        time.sleep(c.LOW_SLEEP)

        flight_segments_elements = self.wait_until_all_visible(
            by=By.XPATH,
            identifier="//mat-dialog-container//kilo-simple-lightbox//"
            "kilo-flight-details-pres//kilo-flight-segment-details-cont",
            timeout=c.HIGH_SLEEP,
        )

        for segment_index, segment_element in enumerate(flight_segments_elements):
            logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
            segment_items = segment_element.find_elements(By.XPATH, './/div[@class="container"]')
            segment_depart_info_element = segment_items[0]
            try:
                segment_departure_time_element = segment_depart_info_element.find_element(
                    by=By.XPATH, value='.//div[contains(@class, "flight-timings")]'
                )
            except NoSuchElementException:
                time.sleep(c.DEFAULT_SLEEP)
                segment_departure_time_element = segment_depart_info_element.find_element(
                    by=By.XPATH, value='.//div[contains(@class, "flight-timings")]'
                )
            try:
                segment_departure_day_element = segment_depart_info_element.find_element(
                    By.XPATH, './/div[contains(@class, "flight-timings")]//span[contains(@class, "arrival-days")]'
                )
                departure_days_delta = self.get_text(segment_departure_day_element)
                departure_days_delta = int(extract_digits(departure_days_delta))
                segment_departure_date = departure_date + datetime.timedelta(days=departure_days_delta)
            except NoSuchElementException:
                segment_departure_date = departure_date

            segment_departure_time = extract_iso_time(self.get_text(segment_departure_time_element))

            segment_flights_detail_element = segment_depart_info_element.find_element(
                By.XPATH, './/div[contains(@class, "flight-details-container")]'
            )

            flight_detail_container = segment_flights_detail_element.find_elements(
                By.XPATH, './/div[contains(@class, "d-flex")]'
            )
            depart_airline_info = flight_detail_container[0]
            depart_airline_city_code_element = depart_airline_info.find_elements(By.XPATH, ".//span")[0]
            depart_airline_city = depart_airline_city_code_element.find_element(By.XPATH, ".//strong")
            depart_airline_city = self.get_text(depart_airline_city)
            segment_origin = self.get_text(depart_airline_city_code_element).replace(depart_airline_city, "").strip()
            airline_attributes = flight_detail_container[1]
            airline_info = airline_attributes.find_elements(
                By.XPATH, './/div[contains(@class, "airline-info")]//div[contains(@class, "airline-details")]//span'
            )
            segment_flight_number = self.get_text(airline_info[0])
            segment_carrier = self.get_text(airline_info[1]).replace("| Operated by", "").strip()
            segment_aircraft = self.get_text(airline_info[2])

            segment_arrival_info_element = segment_items[1]
            segment_arrival_time_element = segment_arrival_info_element.find_element(
                By.XPATH, './/div[contains(@class, "flight-timings")]//span[1]'
            )
            segment_arrival_time = extract_iso_time(self.get_text(segment_arrival_time_element))
            try:
                segment_arrival_day_element = segment_depart_info_element.find_element(
                    By.XPATH, './/div[contains(@class, "flight-timings")]//span[contains(@class, "arrival-days")]'
                )
                arrival_days_delta = self.get_text(segment_arrival_day_element)
                arrival_days_delta = int(extract_digits(arrival_days_delta))
                segment_arrival_date = departure_date + datetime.timedelta(days=arrival_days_delta)
            except NoSuchElementException:
                segment_arrival_date = departure_date

            arrival_airline_city_code_element = segment_arrival_info_element.find_elements(
                By.XPATH, './/div[contains(@class, "flight-details-container")]//span'
            )[0]

            arrival_airline_city = arrival_airline_city_code_element.find_element(By.XPATH, ".//strong")
            arrival_airline_city = self.get_text(arrival_airline_city)

            segment_destination = (
                self.get_text(arrival_airline_city_code_element).replace(arrival_airline_city, "").strip()
            )
            flight_segments.append(
                FlightSegment(
                    origin=segment_origin,
                    destination=segment_destination,
                    departure_date=segment_departure_date.isoformat(),
                    departure_time=segment_departure_time,
                    departure_timezone="",
                    arrival_date=segment_arrival_date.isoformat(),
                    arrival_time=segment_arrival_time,
                    arrival_timezone="",
                    aircraft=segment_aircraft,
                    flight_number=segment_flight_number,
                    carrier=segment_carrier,
                )
            )

        self.find_and_click_element(
            identifier="//mat-dialog-container//div[contains(@class, 'lightbox-container')]"
            "//div[contains(@class, 'header')]//span[contains(@class, 'icon-close')]",
            by=By.XPATH,
        )
        return flight_segments

    @staticmethod
    def extract_currency_and_amount(input_string) -> Optional[Tuple[str, float]]:
        pattern = re.compile(r"([A-Za-z]+) \$([\d,]+(?:\.\d{2})?)")
        match = pattern.match(input_string)

        if match:
            currency = match.group(1)
            amount = float(match.group(2).replace(",", ""))
            return currency, amount
        else:
            return None

    def extract_sub_classes_points(
        self, flight_row_element: WebElement, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        cabin_class_code = CabinClassCodeMapping[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}
        try:
            self.find_and_click_element(
                by=By.XPATH,
                identifier=f".//div[contains(@class, 'cabins-container')]"
                f"//kilo-cabin-cell-pres[contains(@class, 'cabin')]"
                f"[contains(@data-analytics-val, '{cabin_class_code}')]"
                f"//div[contains(@class, 'available-cabin')][contains(@class, 'flight-cabin-cell')]",
                from_element=flight_row_element,
            )
        except NoSuchElementException:
            return None

        fare_names_elements = self.find_elements(
            by=By.XPATH, identifier="//div[contains(@class, 'fare-headers')]//span"
        )
        fare_details_elements = self.find_elements(
            by=By.XPATH, identifier="//div[contains(@class, 'fare-list')]//div[contains(@class, 'fare-list-item')]"
        )
        for fare_name_element, fare_details_element in zip(fare_names_elements, fare_details_elements):
            try:
                fare_name = self.get_text(fare_name_element)
                point_element = self.find_element(
                    by=By.XPATH,
                    identifier=".//div[contains(@class, 'price-container')]//div[contains(@class, 'points')]/span",
                    from_element=fare_details_element,
                )
                points = self.get_text(point_element)
                cash_fee_element = self.find_element(
                    by=By.XPATH,
                    identifier=".//div[contains(@class, 'price-container')]//kilo-price/span",
                    from_element=fare_details_element,
                )
                cash_fee = self.get_text(cash_fee_element)
                currency, amount = self.extract_currency_and_amount(cash_fee)
                points_by_fare_names[fare_name] = {
                    "points": convert_k_to_float(points),
                    "cash_fee": CashFee(
                        amount=amount,
                        currency=currency,
                    ),
                }
            except NoSuchElementException:
                continue
        return points_by_fare_names

    def extract(
        self,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
    ) -> Iterator[Flight]:
        try:
            logger.info(f"{self.AIRLINE.value}: Searching results...")
            provided_cabin_classes = [
                self.get_text(element).lower()
                for element in self.find_elements(by=By.XPATH, identifier="//div[@class='cabin-heading']")
            ]
            if CabinClassCodeMapping[cabin_class] not in provided_cabin_classes:
                raise NoSearchResult(airline=self.AIRLINE)

            stop_filter_element = self.wait_until_visible(
                by=By.XPATH,
                identifier="//button[@aria-label='Stops']",
                timeout=c.MEDIUM_SLEEP,
            )
            self.click_element(stop_filter_element)
            time.sleep(0.5)
            one_stop_filter = self.wait_until_visible(
                by=By.XPATH,
                identifier="//mat-radio-button[@name='oneStop']/label",
                timeout=c.MEDIUM_SLEEP,
            )
            self.click_element(one_stop_filter)
            time.sleep(1)
            close_button = self.wait_until_visible(
                by=By.XPATH,
                identifier="//div[@class='close-icon-container']",
                timeout=c.MEDIUM_SLEEP,
            )
            self.click_element(close_button)

            flight_search_results = self.wait_until_all_visible(
                by=By.XPATH,
                identifier='//div[@class="page-container"]//kilo-upsell-cont//kilo-upsell-pres'
                '//kilo-upsell-row-cont//div[contains(@class, "upsell-row")]',
                timeout=c.MEDIUM_SLEEP,
            )
        except (NoSuchElementException, TimeoutException):
            raise NoSearchResult(airline=self.AIRLINE)

        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

            points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_class)
            if not points_by_fare_names:
                continue

            try:
                segments = self.extract_flight_detail(flight_search_result, departure_date)
            except Exception as e:
                raise e

            duration_ele = flight_search_result.locator("div.flight-summary")
            duration_text = self.get_text(duration_ele)
            duration_re = re.search(r"(\d+(hr)?\d*m)", duration_text)
            if duration_re:
                duration = duration_re.group(1)
                duration = f'PT{duration.upper()}'
            else:
                duration = None

            for fare_name, points_and_cash in points_by_fare_names.items():
                yield Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=str(cabin_class.value),
                    airline_cabin_class=fare_name,
                    points=points_and_cash["points"],
                    cash_fee=points_and_cash["cash_fee"],
                    segments=segments,
                    duration=duration,
                )

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: SmartCabinClassType = c.CabinClass.Economy,
        adults: int = 1,
    ) -> Iterator[Flight]:
        self.continue_search()
        for flight in self.extract(departure_date, cabin_class):
            yield flight


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AirCanadaSeleniumBasedCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=10, day=1)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
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
    run("JFK", "LHR", c.CabinClass.Economy)
    run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    run("YVR", "YYZ", c.CabinClass.Business)
    run("KUL", "YYZ", c.CabinClass.First)
