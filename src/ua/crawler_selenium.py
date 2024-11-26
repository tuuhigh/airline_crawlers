import datetime
import logging
import re
import time
from typing import Iterator, List, Optional, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement

from src import constants as c
from src.base import SeleniumBasedAirlineCrawler
from src.exceptions import NoSearchResult
from src.schema import CashFee, Flight, FlightSegment
from src.ua.constants import CabinClassCodeMapping
from src.utils import convert_k_to_float, extract_currency_and_amount, parse_time

logger = logging.getLogger(__name__)


class UnitedAirlineSeleniumBasedCrawler(SeleniumBasedAirlineCrawler):
    AIRLINE = c.Airline.UnitedAirline
    REQUIRED_LOGIN = False
    HOME_PAGE_URL = "https://www.united.com/en/us"

    def _select_oneway(self) -> None:
        self.click_once_presence(by=By.XPATH, identifier='//label[@for="oneway"]', timeout=c.HIGH_SLEEP * 3)
        time.sleep(c.LOW_SLEEP)

    def _select_miles(self) -> None:
        self.click_once_presence(by=By.XPATH, identifier='//label[@for="award"]', timeout=c.MEDIUM_SLEEP)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        origin_input = self.wait_until_presence(
            by=By.XPATH,
            identifier='//input[@id="bookFlightOriginInput"]',
            timeout=c.MEDIUM_SLEEP,
        )
        origin_input.send_keys(Keys.CONTROL, "a")
        origin_input.send_keys(origin)

        self.click_once_presence(
            by=By.XPATH,
            identifier='//ul[@id="bookFlightOriginInput-menu"]/li[contains(@id, "autocomplete-item")][1]//button',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        destination_input = self.wait_until_presence(
            by=By.XPATH,
            identifier='//input[@id="bookFlightDestinationInput"]',
            timeout=c.MEDIUM_SLEEP,
        )
        destination_input.send_keys(Keys.CONTROL, "a")
        destination_input.send_keys(destination)

        self.click_once_presence(
            by=By.XPATH,
            identifier='//ul[@id="bookFlightDestinationInput-menu"]/li[contains(@id, "autocomplete-item")][1]//button',
            timeout=c.MEDIUM_SLEEP,
        )

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        calendar_depart_date = departure_date.strftime("%b %d")
        depart_date_input = self.wait_until_presence(
            by=By.XPATH,
            identifier='//input[@id="DepartDate"]',
            timeout=c.MEDIUM_SLEEP,
        )
        depart_date_input.send_keys(Keys.CONTROL, "a")
        depart_date_input.send_keys(calendar_depart_date)

    def accept_cookie(self):
        pass

    def _submit(self) -> None:
        self.click_once_clickable(
            by=By.XPATH,
            identifier='//form[@id="bookFlightForm"]//button[@type="submit"]',
            timeout=c.HIGH_SLEEP * 3,
        )

    def continue_search(self) -> None:
        wait_xpath_s = (
            '//div[contains(@class, "ResultFooter-styles__displayCountLabel")][contains(text(), "Displaying")]'
        )
        wait_xpath_f = '//button[contains(@class, "app-containers-TimeoutModal-timeoutmodal__btnDefault")]'
        try:
            self.wait_until_presence(
                by=By.XPATH,
                identifier=f"{wait_xpath_s} | {wait_xpath_f}",
                timeout=c.HIGH_SLEEP,
            )
        except (NoSuchElementException, TimeoutException):
            raise NoSearchResult(airline=self.AIRLINE)

        try:
            self.driver.find_element(By.XPATH, wait_xpath_f)
            self.click_once_clickable(
                by=By.XPATH,
                identifier=wait_xpath_f,
                timeout=c.LOW_SLEEP,
            )
            time.sleep(c.LOW_SLEEP * 2)
        except (NoSuchElementException, TimeoutException):
            raise NoSearchResult(airline=self.AIRLINE)

    def close_login_dialog(self):
        try:
            self.find_and_click_element(by=By.XPATH, identifier="//button[@id='closeBtn']")
        except NoSuchElementException:
            pass

    def load_more(self) -> None:
        count_ele = self.wait_until_presence(
            by=By.XPATH,
            identifier='//div[contains(@class, "ResultFooter-styles__displayCountLabel")]'
            '[contains(text(), "Displaying")]',
            timeout=c.MEDIUM_SLEEP,
        )
        display_count = self.get_text(count_ele)
        match = re.search(r"\s+(fd+)\s+of\s+(\d+)", display_count)
        if match:
            showing_count, total_count = map(int, match.groups())
            if showing_count < total_count:
                self.click_once_clickable(
                    by=By.XPATH,
                    identifier='//div[contains(@class, "ResultFooter-styles__buttonContainer")]'
                    '/button[span[contains(text(), "all")]]',
                    timeout=c.MEDIUM_SLEEP,
                )

    def extract_points(
        self, flight_row_element: WebElement, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Tuple[str, float, CashFee]]:
        try:
            cabin_class_code = CabinClassCodeMapping[cabin_class]
            price_container = self.find_element(
                by=By.XPATH,
                identifier=f'.//div[contains(@class, "PriceCard-styles__priceCardWrapper")]'
                f'[@aria-describedby="{cabin_class_code}"]',
                from_element=flight_row_element,
            )
            cabin_class_element = self.find_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "app-components-Shopping-PriceCard-styles__bottom")]//'
                'div[contains(@class, "cabinDescription")]',
                from_element=price_container,
            )
            fare_name = self.get_text(cabin_class_element)

            points_ele = self.find_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "app-components-Shopping-Miles-styles")]',
                from_element=price_container,
            )
            points = convert_k_to_float(self.get_text(points_ele))

            cash_fee_element = self.find_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "PriceCard-styles__moneyContainer")]'
                '//div[contains(@class, "PriceCard-styles__priceValue")]/span',
                from_element=price_container,
            )
            cash_fee = self.get_text(cash_fee_element)
            currency, amount = extract_currency_and_amount(cash_fee)

            return fare_name, points, CashFee(currency=currency, amount=amount)
        except NoSuchElementException:
            return None

    def extract_flight_detail(
        self, flight_row_element: WebElement, departure_date: datetime.date
    ) -> List[FlightSegment]:
        segments = []
        flight_details_link = None
        try:
            flight_details_link = self.find_element(
                by=By.XPATH,
                identifier='.//div[contains(@class, "FlightBaseCard-styles__flightBaseCardContainer__footer")]'
                '//button[@aria-label="Details"][@aria-expanded="false"]',
                from_element=flight_row_element,
            )
            self.click_element(flight_details_link)

            segment_rows = self.wait_until_all_visible(
                by=By.XPATH,
                identifier='.//div[contains(@class, "FlightDetailCard-styles__segments")]'
                '//div[contains(@class, "FlightDetailCard-styles__detailflightInfo")]',
                timeout=c.MEDIUM_SLEEP,
            )

            for segment_index, segment_row in enumerate(segment_rows):
                origin_ele = self.find_element(
                    by=By.XPATH,
                    identifier='.//div[contains(@class, "FlightInfoBlock-styles__departAirport")]//span[1]',
                    from_element=segment_row,
                )
                segment_origin = self.get_text(origin_ele)

                destination_ele = self.find_element(
                    by=By.XPATH,
                    identifier='.//div[contains(@class, "FlightInfoBlock-styles__arrivalAirport")]//span[1]',
                    from_element=segment_row,
                )
                segment_destination = self.get_text(destination_ele)

                if segment_index == 0:
                    segment_departure_date = departure_date.isoformat()
                else:
                    segment_departure_date = ""

                depart_time_element = self.find_element(
                    by=By.XPATH,
                    identifier='.//div[contains(@class, "FlightInfoBlock-styles__departTime")]//span[1]',
                    from_element=segment_row,
                )
                depart_time = self.get_text(depart_time_element)
                segment_departure_time = parse_time(depart_time, "%I:%M %p")

                # TODO: getting arrival time should be updated
                if segment_index == 0:
                    segment_arrival_date = segment_departure_date
                else:
                    segment_arrival_date = segment_departure_date

                arrival_time_element = self.find_element(
                    by=By.XPATH,
                    identifier='.//div[contains(@class, "FlightInfoBlock-styles__arrivalTime")]//span[1]',
                    from_element=segment_row,
                )
                arrival_time = self.get_text(arrival_time_element)
                segment_arrival_time = parse_time(arrival_time, "%I:%M %p")

                carrier_info_xpath = './/div[contains(@class, "FlightDetailCard-styles__aircraftInfo")]'
                carrier_info_ele = self.find_element(carrier_info_xpath)
                carrier_info = self.get_text(carrier_info_ele)
                segment_flight_number = carrier_info.split("(")[0].strip()
                aircraft = carrier_info.split("(", 2)[1]
                segment_aircraft = aircraft.strip(" ()")

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
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier="",
                    )
                )
            return segments
        except Exception:
            # TODO: error handling
            pass
        finally:
            if flight_details_link:
                self.click_element(flight_details_link)

    def extract(
        self, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flight_rows = self.driver.find_elements(By.XPATH, '//div[contains(@class, "GridItem-styles__flightRow")]')

        for flight_index, flight_row_element in enumerate(flight_rows):
            try:
                self.scroll_to(flight_row_element)

                fare = self.extract_points(flight_row_element, cabin_class=cabin_class)
                if fare is None:
                    continue

                fare_name, points, cash_fee = fare
                segments = self.extract_flight_detail(flight_row_element, departure_date)
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
            except Exception:
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
        self.close_login_dialog()
        self.load_more()
        for flight in self.extract(departure_date=departure_date, cabin_class=cabin_class):
            yield flight


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = UnitedAirlineSeleniumBasedCrawler()
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
        if flights is not None:
            with open(f"{crawler.AIRLINE.value}_{cabin_class.value}.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    # run("PVG", "PEK", c.CabinClass.Economy)
    run("DFW", "JFK", c.CabinClass.Economy)
