import datetime
import logging
import random
import re
import time
from typing import Iterator, List, Optional, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from src import constants as c
from src.base import SeleniumBasedAirlineCrawler
from src.exceptions import AirportNotSupported, LoginFailed, NoSearchResult
from src.ha.constants import CabinClassCodeMapping
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    parse_date,
    parse_time,
)

logger = logging.getLogger(__name__)


HawaiianAirlineCredentials = c.Credentials[c.Airline.HawaiianAirline]


class HawaiianAirlineCrawler(SeleniumBasedAirlineCrawler):
    AIRLINE = c.Airline.HawaiianAirline
    REQUIRED_LOGIN = True
    HOME_PAGE_URL = "https://www.hawaiianairlines.com/my-account/login/?ReturnUrl=%2fmy-account"

    def __init__(self):
        super().__init__()
        self.credentials: List[c.AirlineCredential] = HawaiianAirlineCredentials.copy()
        random.shuffle(self.credentials)

    def _select_oneway(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier="//a[contains(@id, 'triptype1')]",
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_miles(self) -> None:
        self.click_once_presence(
            by=By.XPATH,
            identifier='//input[@id="type1"]',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        origin_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[@id='origin']",
            timeout=c.MEDIUM_SLEEP,
        )
        origin_input.send_keys(Keys.CONTROL, "a")
        self.human_typing(origin_input, origin)

        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//div[@class='location-dropdown']//" "ul/li[contains(@class, 'match')][1]/div",
                timeout=c.MEDIUM_SLEEP,
            )
        except (NoSuchElementException, TimeoutException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=origin)

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        destination_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[@id='destination']",
            timeout=c.MEDIUM_SLEEP,
        )
        destination_input.send_keys(Keys.CONTROL, "a")
        self.human_typing(destination_input, destination)

        try:
            self.click_once_presence(
                by=By.XPATH,
                identifier="//div[@class='location-dropdown']//" "ul/li[contains(@class, 'match')][1]/div",
                timeout=c.MEDIUM_SLEEP,
            )
        except (TimeoutException, NoSuchElementException):
            raise AirportNotSupported(airline=self.AIRLINE, airport=destination)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        departure_date_str = departure_date.strftime("%m/%d/%Y")
        calender_element = self.wait_until_clickable(
            by=By.XPATH,
            identifier="//input[@id='DepartureDate']",
            timeout=c.MEDIUM_SLEEP,
        )
        calender_element.click()
        calender_element.send_keys(Keys.CONTROL, "a")
        self.human_typing(calender_element, departure_date_str)

    def accept_cookie(self):
        pass

    def _submit(self) -> None:
        self.find_and_click_element(
            by=By.XPATH,
            identifier="//button[contains(@class, 'btn-cta-search')]",
        )

    def continue_search(self) -> None:
        pass

    def extract_flight_detail(self, flight_row_element: WebElement) -> List[FlightSegment]:
        segments: List[FlightSegment] = []

        try:
            self.find_and_click_element(
                by=By.XPATH, identifier='.//a[contains(@class, "link-details")]', from_element=flight_row_element
            )

            flight_segments = self.wait_until_all_visible(
                by=By.XPATH,
                identifier="//ha-modal-dialog//div[contains(@class, 'ha-modal-body')]"
                "//app-flight-details-modal//div[contains(@class, 'flight-details-modal')]"
                "/div[contains(@class, 'flight-section') or contains(@class, 'ng-star-inserted')]",
                timeout=c.MEDIUM_SLEEP,
            )
            for segment_index, segment_element in enumerate(flight_segments):
                time_elements = segment_element.find_elements(By.XPATH, ".//span[@class='time-subheader']")
                if len(time_elements) != 2:
                    # skip if there is a component that showing overlay
                    continue
                depart_info = self.get_text(time_elements[0])
                segment_departure_time = parse_time(depart_info, "%I:%M %p, %a, %b %d, %Y")
                segment_departure_date = parse_date(depart_info, "%I:%M %p, %a, %b %d, %Y")

                arrival_info = self.get_text(time_elements[1])
                segment_arrival_time = parse_time(arrival_info, "%I:%M %p, %a, %b %d, %Y")
                segment_arrival_date = parse_date(arrival_info, "%I:%M %p, %a, %b %d, %Y")

                airline_elements = segment_element.find_elements(By.XPATH, ".//span[@class='location']/div[1]")
                depart_airline = self.get_text(airline_elements[0]).strip()
                segment_origin = re.search(r"\((.*?)\)", depart_airline).group(1)
                destination_airline = self.get_text(airline_elements[1]).strip()
                segment_destination = re.search(r"\((.*?)\)", destination_airline).group(1)

                segment_aircraft = self.get_text_from_element(
                    by=By.XPATH,
                    identifier=".//*[contains(@id, 'ha-aircraft-num')]",
                    from_element=segment_element,
                )
                segment_aircraft = segment_aircraft.replace("Aircraft: ", "")

                segment_flight_number = self.get_text_from_element(
                    by=By.XPATH,
                    identifier=".//div[@class='flight-info-number']",
                    from_element=segment_element,
                )
                segment_flight_number = segment_flight_number.replace("Flight ", "")
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
                identifier="//ha-modal-dialog//div[contains(@class, 'icon-close')]",
            )
            return segments
        except NoSuchElementException:
            pass

    def extract_points(
        self, flight_row_element: WebElement, cabin_class: c.CabinClass
    ) -> Optional[Tuple[str, float, CashFee]]:
        airline_cabin_class = CabinClassCodeMapping[cabin_class]
        try:
            price_container = flight_row_element.find_element(
                By.XPATH,
                f".//div[contains(@class, 'award-{airline_cabin_class}')]"
                f"/div[contains(@class, 'flight-results-column')]",
            )
            fare_name = self.get_text_from_element(
                by=By.XPATH,
                identifier=".//span[@class='flight-results-column__cabin-type']",
                from_element=price_container,
            )

            mile_and_cost_elements = price_container.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'flight-results-column__fare-cost')]/"
                "div[contains(@class, 'flight-results-column__fare-cost--miles')]/span",
            )
            points = self.get_text(mile_and_cost_elements[0]).replace(" mi", "")
            points = convert_k_to_float(points)

            price_text = self.get_text(mile_and_cost_elements[1])
            currency, amount = extract_currency_and_amount(price_text.strip("+"))
            return fare_name, points, CashFee(currency=currency, amount=amount)
        except (IndexError, NoSuchElementException):
            pass

    def extract(
        self,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
    ) -> Iterator[Flight]:
        try:
            search_results = self.wait_until_all_visible(
                by=By.XPATH,
                identifier="//app-flight-results/div[contains(@class, 'flight-results')]"
                "/div[contains(@class, 'flight-row')]",
                timeout=60,
            )
        except (NoSuchElementException, TimeoutException):
            raise NoSearchResult(airline=self.AIRLINE)

        for index, flight_row_element in enumerate(search_results):
            fare = self.extract_points(flight_row_element, cabin_class)
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

    def _login(self):
        credential = self.credentials.pop(0)
        username_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[@id='user_name']",
            timeout=c.HIGH_SLEEP,
        )
        username_input.send_keys(Keys.CONTROL, "a")
        username_input.send_keys(credential.username)

        # Input Password
        password_input = self.wait_until_presence(
            by=By.XPATH,
            identifier="//input[@id='password']",
            timeout=c.HIGH_SLEEP,
        )
        password_input.send_keys(Keys.CONTROL, "a")
        password_input.send_keys(credential.password)

        # Click Sign In button
        self.click_once_presence(
            by=By.XPATH,
            identifier="//button[contains(@id, 'submit_login_button')]",
            timeout=c.HIGH_SLEEP,
        )

        try:
            WebDriverWait(self.driver, c.MEDIUM_SLEEP).until(lambda driver: "book/flights" in self.driver.current_url)

            if "book/flights" in self.driver.current_url:
                self.wait_until_presence(
                    by=By.XPATH,
                    identifier="//span[@class='nav-account-name']",
                    timeout=c.HIGH_SLEEP * 3,
                )
        except (NoSuchElementException, TimeoutException):
            raise LoginFailed(airline=self.AIRLINE)

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        for flight in self.extract(cabin_class):
            yield flight


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = HawaiianAirlineCrawler()
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

    # run("HNL", "PEK", c.CabinClass.Economy)
    run("HNL", "LAX", c.CabinClass.Economy)
