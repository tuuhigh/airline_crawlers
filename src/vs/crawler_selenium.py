import datetime
import logging
import time
from typing import Iterator, List, Optional, Tuple

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement

from src import constants as c
from src.base import SeleniumBasedAirlineCrawler
from src.exceptions import AirportNotSupported, NoSearchResult
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    parse_date,
    parse_time,
)
from src.vs.constants import CabinClassCodeMapping

logger = logging.getLogger(__name__)


class VirginAtlanticSeleniumBasedCrawler(SeleniumBasedAirlineCrawler):
    AIRLINE = c.Airline.VirginAtlantic
    REQUIRED_LOGIN = False
    HOME_PAGE_URL = "https://www.virginatlantic.com/us/en"

    def _select_oneway(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//span[@aria-labelledby='selectTripType-label']",
            timeout=c.MEDIUM_SLEEP,
        )
        self.click_once_presence(
            by=By.XPATH,
            identifier="//ul[@id='selectTripType-desc']/li[@data='1']",
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_miles(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier='//a[contains(@class, "icon-advsearchtriangle")]',
            timeout=c.MEDIUM_SLEEP,
        )
        self.click_once_presence(
            by=By.XPATH,
            identifier='//label[@for="miles"]',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//a[@id='fromAirportName']",
            timeout=c.MEDIUM_SLEEP,
        )
        origin_input = self.driver.find_element(By.XPATH, "//input[@id='search_input']")
        origin_input.send_keys(Keys.CONTROL, "a")
        origin_input.clear()
        self.human_typing(origin_input, origin)

        time.sleep(c.LOW_SLEEP)
        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier=f"//div[@class='search-result-container']//ul/li[contains(@class, 'airport-list')][1]/a[./span[contains(text(), '{origin}')]]",
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
        destination_input = self.driver.find_element(By.XPATH, "//input[@id='search_input']")
        destination_input.send_keys(Keys.CONTROL, "a")
        destination_input.clear()
        self.human_typing(destination_input, destination)

        time.sleep(c.LOW_SLEEP)

        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier=f"//div[@class='search-result-container']//ul/li[contains(@class, 'airport-list')][1]/a[./span[contains(text(), '{destination}')]]",
                timeout=c.MEDIUM_SLEEP,
            )
        except (NoSuchElementException, TimeoutException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=destination)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        departure_date_str = departure_date.strftime("%m/%d/%Y")
        self.click_once_presence(
            by=By.XPATH,
            identifier="//div[@id='input_departureDate_1' or @id='input_returnDate_1']",
            timeout=c.MEDIUM_SLEEP,
        )

        next_mon_btn = self.wait_until_presence(
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
            except (TimeoutException, StaleElementReferenceException):
                self.click_element(next_mon_btn)

    def accept_cookie(self):
        try:
            self.click_once_clickable(
                by=By.XPATH,
                identifier='//button[@id="privacy-btn-reject-all"]',
                timeout=c.LOW_SLEEP,
            )
        except TimeoutException:
            pass

    def _submit(self) -> None:
        self.click_once_clickable(
            by=By.XPATH,
            identifier="//button[@id='btn-book-submit']",
            timeout=c.MEDIUM_SLEEP,
        )

    def continue_search(self) -> None:
        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//button[contains(@class, 'flexi-continue-btn')]",
                timeout=c.HIGH_SLEEP,
            )
        except (TimeoutException, NoSuchElementException):
            raise NoSearchResult(airline=self.AIRLINE)

    def load_more(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//button[contains(@class, 'flexi-continue-btn')]",
            timeout=c.HIGH_SLEEP,
        )

    def extract_points(
        self, flight_row_element: WebElement, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Tuple[str, float, CashFee]]:
        logger.info(f"{self.AIRLINE.value}: Extracting points...")
        airline_cabin_class = CabinClassCodeMapping[cabin_class]
        price_btn = flight_row_element.find_element(
            By.XPATH,
            f".//app-grid-fare-cell//div[contains(@class, 'brandWrapperVS{airline_cabin_class}')]"
            f"//div[contains(@class, 'farecelloffered')]",
        )

        try:
            fare_name_element = price_btn.find_element(
                By.XPATH,
                './/div[contains(@class, "cabinContainer")]'
                '//div[contains(@class, "flightcardDetails")][1]//a/span[1]',
            )
            fare_name = self.get_text(fare_name_element).strip(" +")
        except NoSuchElementException:
            return None

        try:
            miles_element = price_btn.find_element(
                By.XPATH,
                './/div[@class="priceContainer"]'
                '//div[contains(@class, "milesValue")]'
                '//span[contains(@class, "tblCntMileBigTxt")]',
            )
            points = self.get_text(miles_element)
            points = convert_k_to_float(points)

            cash_fee_element = price_btn.find_element(
                By.XPATH,
                './/div[@class="priceContainer"]//div[contains(@class, "milesValue")]'
                '//div[contains(@class, "tblCntMilesSmalltxt")]',
            )
            cash_fee = self.get_text(cash_fee_element)
            currency, amount = extract_currency_and_amount(cash_fee.replace("+", "").strip())
            return fare_name, points, CashFee(currency=currency, amount=amount)
        except NoSuchElementException:
            return None

    def extract_flight_detail(self, flight_row_element: WebElement) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Detail..")
        self.find_and_click_element(
            by=By.XPATH,
            identifier='.//div[contains(@class, "detailsInfo")]//div[contains(@class, "detailsRow")]'
            '//a[contains(@class, "detailslink")]//span[1]',
            from_element=flight_row_element,
        )
        flight_segments_elements = self.wait_until_all_visible(
            by=By.XPATH,
            identifier="//app-modal-dialog//div[contains(@class, 'modal-component-body')]"
            "//app-flight-specific-modal//div[contains(@class, 'flight-specific-page-view')]"
            "//app-flight-details-modal//div[contains(@class, 'flight-details-container')]",
            timeout=c.MEDIUM_SLEEP,
        )

        segments: List[FlightSegment] = []
        for segment_index, segment_element in enumerate(flight_segments_elements):
            segment_item_header_container = segment_element.find_element(
                By.XPATH, './/div[contains(@class, "flight-details-row")]'
            )
            segment_item_body_container = segment_element.find_element(
                By.XPATH,
                './/div[contains(@class, "flight-card-body")]//'
                'div[contains(@class, "flight-specific-details")]/div[contains(@class, "row")]',
            )

            segment_depart_time_element = segment_item_body_container.find_element(
                By.XPATH, './/div[contains(@class, "flight-depature-time")]/div'
            )
            segment_depart_time = self.get_text(segment_depart_time_element).strip()
            segment_departure_time = parse_time(segment_depart_time, "%I:%M %p")

            segment_arrival_time_element = segment_item_body_container.find_element(
                By.XPATH, './/div[contains(@class, "flight-arrival-time")]/div'
            )
            segment_arrival_time = self.get_text(segment_arrival_time_element).strip()
            segment_arrival_time = parse_time(segment_arrival_time, "%I:%M %p")

            depart_airline_info = segment_item_body_container.find_element(
                By.XPATH, './/div[contains(@class, "flight-depature-airport")]'
            )
            depart_airline_code_element = depart_airline_info.find_element(
                By.XPATH, './/div[contains(@class, "flight-depature-airport-code")]'
            )

            segment_origin = self.get_text(depart_airline_code_element).strip()

            arrival_airline_info = segment_item_body_container.find_element(
                By.XPATH, './/div[contains(@class, "flight-arrival-airport")]'
            )
            arrival_airline_code_element = arrival_airline_info.find_element(
                By.XPATH, './/div[contains(@class, "flight-arrival-airport-code")]'
            )

            segment_destination = self.get_text(arrival_airline_code_element)

            aircraft_element = segment_item_body_container.find_element(
                By.XPATH, './/div[contains(@class, "aircraft-type")]'
            )
            segment_aircraft = self.get_text(aircraft_element)

            airline_flight_number_element = segment_item_header_container.find_element(
                By.XPATH, './/div[contains(@class, "flight-number")]'
            )
            airline_flight_info = self.get_text(airline_flight_number_element)
            flight_infos = airline_flight_info.split("Operated by")
            segment_flight_number = flight_infos[0].strip()
            carrier = flight_infos[1]

            travel_date_element = segment_item_header_container.find_element(
                By.XPATH, './/div[contains(@class, "flight-number")]/div/span[@class="travelDate"]'
            )
            travel_date = self.get_text(travel_date_element)
            travel_date = parse_date(travel_date, "%a, %b %d")

            segments.append(
                FlightSegment(
                    origin=segment_origin,
                    destination=segment_destination,
                    departure_date=travel_date,
                    departure_time=segment_departure_time,
                    departure_timezone="",
                    arrival_date=travel_date,
                    arrival_time=segment_arrival_time,
                    arrival_timezone="",
                    aircraft=segment_aircraft,
                    flight_number=segment_flight_number,
                    carrier=carrier,
                )
            )
        return segments

    def extract(
        self, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        logger.info(f"{self.AIRLINE.value}: Extracting...")
        try:
            search_results = self.wait_until_all_visible(
                by=By.XPATH,
                identifier='//app-grid-flight-result-container/div[contains(@class, "flightcardContainer")]',
                timeout=c.MEDIUM_SLEEP * 2,
            )
        except (TimeoutException, StaleElementReferenceException):
            raise NoSearchResult(airline=self.AIRLINE)

        logger.info(f"{self.AIRLINE.value}: Found {len(search_results)} flights...")
        for index, flight_row_element in enumerate(search_results):
            try:
                fare = self.extract_points(flight_row_element, cabin_class=cabin_class)
                if fare is None:
                    continue

                fare_name, points, cash_fee = fare
                segments = self.extract_flight_detail(flight_row_element)
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

                self.click_once_presence(
                    by=By.XPATH,
                    identifier="//app-modal-dialog//div[contains(@class, 'modal-component-body')]"
                    "//app-flight-specific-modal//div[contains(@class, 'flight-specific-page-view')]"
                    "//div[contains(@class, 'flightmodalheader')]//button[contains(@class, 'exit-button')]",
                    timeout=c.LOW_SLEEP,
                )
            except Exception as e:
                logging.info(f"The detail of search item is not retrieved => index: {index}. error: {e}")
                continue

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
        for flight in self.extract(departure_date, cabin_class):
            yield flight


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = VirginAtlanticSeleniumBasedCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)

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

    # run("PVG", "PNG", c.CabinClass.Economy)
    # run("EWR", "LHR", c.CabinClass.Economy)
    # run("EWR", "LHR", c.CabinClass.PremiumEconomy)
    run("EWR", "LHR", c.CabinClass.Business)
