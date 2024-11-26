import datetime
import json
import logging
import re
import time
from typing import Dict, Iterator, List, Optional, Tuple

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlayWrightTimeoutError
from src import constants as c
from src.ac.constants import CabinClassCodeMapping
from src.exceptions import CannotContinueSearch, NoSearchResult
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    extract_digits,
    extract_flight_number,
    extract_iso_time,
)

logger = logging.getLogger(__name__)


class AirCanadaPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.AirCanada
    REQUIRED_LOGIN = False
    HOME_PAGE_URL = "https://www.aircanada.com"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Streaming

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

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-us",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }

    # def _select_miles(self, *args, **kwargs) -> None:
    #     page: Page = kwargs.get("page")
    #     # page.select('input#bkmgFlights_searchTypeToggle')
    #     if not page.locator("input#bkmgFlights_searchTypeToggle").is_checked():
    #         # unselect
    #         page.get_by_text("Book with points").click()
    #         time.sleep(0.5)

    #     # page.get_by_text("Book with points").click()
    #     time.sleep(2)

    # def _select_oneway(self, *args, **kwargs) -> None:
    #     page: Page = kwargs.get("page")
    #     page.get_by_label("One-way").check()
    #     time.sleep(0.5)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        self.origin = origin

    #     page: Page = kwargs.get("page")
    #     originEle = page.locator("//input[contains(@id, 'bkmgFlights_origin_trip_1')]")
    #     originEle.clear()
    #     self.human_typing(page, originEle, origin)
    #     originEle.click()
    #     time.sleep(0.5)

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        self.destination = destination

    #     page: Page = kwargs.get("page")
    #     destinationEle = page.locator('xpath=//input[contains(@id, "bkmgFlights_destination_trip")]')
    #     destinationEle.clear()
    #     self.human_typing(page, destinationEle, destination)
    #     time.sleep(0.5)
    #     destinationEle = page.locator('ul#bkmgFlights_destination_trip_1OptionsPanel li').nth(0)
    #     destinationEle.click()
    #     time.sleep(0.5)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        self.departure_date = departure_date

    #     page: Page = kwargs.get("page")
    #     page.click('input#bkmgFlights_travelDates_1')
    #     time.sleep(0.5)

    #     months_until_departure_date = self.months_until_departure_date(departure_date)
    #     if months_until_departure_date > 0:
    #         js_script_scroll_date = "document.getElementById('bkmgFlights_travelDates_1_nextMonth').click()"
    #         for _ in range(months_until_departure_date):
    #             page.evaluate(js_script_scroll_date)
    #             time.sleep(0.2)

    #     js_script_select_date = (
    #         """
    #         var element = document.getElementById("bkmgFlights_travelDates_1-date-%s");
    #         if (element) {
    #             element.click();
    #         }
    #     """
    #         % departure_date.isoformat()
    #     )
    #     page.evaluate(js_script_select_date)
    #     time.sleep(1)

    def _select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        self.adults = adults

    def _close_signin_popup_welcome(self, *args, **kwargs):
        try:
            page: Page = kwargs.get("page")
            page.get_by_role("button", name="Close").click()
        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: there is no signin popup {e}")

    # def continue_search(self, *args, **kwargs) -> None:
    #     page: Page = kwargs.get("page")
    #     try:
    #         page.click(
    #             "//abc-button//button[@id='confirmrewards']",
    #             timeout=c.MEDIUM_SLEEP * 1000,
    #         )
    #         logger.info(f"{self.AIRLINE.value}: Close primary cookie box...")

    #         page.click(
    #             "//mat-dialog-container//kilo-simple-lightbox//div[@id='mat-dialog-title-0']"
    #             "//span[@aria-label='Close']",
    #             timeout=c.HIGHEST_SLEEP * 3 * 1000,
    #         )
    #         logger.info(f"{self.AIRLINE.value}: Close secondary cookie box...")
    #     except Exception as e:
    #         logger.info(f"{self.AIRLINE.value}: continue_search exception {e}")
    def _browse_reward_page(self, *args, **kwargs):
        """
        Go direct reward page without need to submit
        """
        page: Page = kwargs.get("page")
        link = (
            f"https://www.aircanada.com/aeroplan/redeem/availability/outbound?org0={self.origin}"
            f"&dest0={self.destination}&departureDate0={self.departure_date.isoformat()}"
            f"&lang=en-CA&tripType=O&ADT={self.adults}&YTH=0&CHD=0&INF=0&INS=0&marketCode=DOM"
        )
        page.goto(link)

    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        # page.click("//button[@id='bkmgFlights_findButton']")
        # time.sleep(5)

        # self.continue_search(*args, **kwargs)
        self._browse_reward_page(*args, **kwargs)

        # maxium time to wait for data is 60s
        waited_time = max_time = 200
        while page.locator("//kilo-loading-spinner-pres").count() != 0 and max_time > 0:
            loading_spinner_count = page.locator("//kilo-loading-spinner-pres").count()
            logger.info(
                f"{self.AIRLINE.value}: spinner count: {loading_spinner_count} - "
                f"waiting for loading flights data, {max_time}s remaining"
            )
            time.sleep(1)
            max_time -= 1

        if max_time == 0:
            logger.error(f"{self.AIRLINE.value}: waited for {waited_time}s but no results, might get blocked")
            raise NoSearchResult(airline=self.AIRLINE)

        self._close_signin_popup_welcome(*args, **kwargs)
        time.sleep(2)

    def _login(self, *args, **kwargs):
        pass

    def extract_flight_detail(
        self,
        page,
        flight_row_element,
        departure_date: datetime.date,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []
        segment_departure_date = segment_arrival_date = ""

        # click detail element
        try:
            flight_row_element.locator("a.detail-link").click()
        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: click details exception: {e}")
        time.sleep(c.LOW_SLEEP)

        flight_segments_elements = page.locator(
            "//mat-dialog-container//kilo-simple-lightbox//"
            "kilo-flight-details-pres//kilo-flight-segment-details-cont",
        ).all()
        for segment_index, segment_element in enumerate(flight_segments_elements):
            logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
            segment_items = segment_element.locator("div.container").all()

            # Departure
            segment_depart_info_element = segment_items[0]
            try:
                segment_departure_time_element = segment_depart_info_element.locator("div.flight-timings").nth(0)
            except PlayWrightTimeoutError:
                time.sleep(c.DEFAULT_SLEEP)
                segment_departure_time_element = segment_depart_info_element.locator("div.flight-timings").nth(0)
            try:
                segment_departure_day_element = segment_depart_info_element.locator(
                    "div.flight-timings span.arrival-days"
                )
                segment_departure_day_element.wait_for(timeout=1000)
                departure_days_delta = self.get_text(segment_departure_day_element)
                if departure_days_delta:
                    departure_days_delta = int(extract_digits(departure_days_delta))
                    segment_departure_date = departure_date + datetime.timedelta(days=departure_days_delta)
            except Exception:
                segment_departure_date = departure_date
            segment_departure_time = extract_iso_time(self.get_text(segment_departure_time_element))

            segment_flights_detail_element = segment_depart_info_element.locator("div.flight-details-container")

            flight_detail_container = segment_flights_detail_element.locator("div.d-flex").all()

            depart_airline_info = flight_detail_container[0]
            depart_airline_city_code_element = depart_airline_info.locator("span").nth(0)
            depart_airline_city = depart_airline_city_code_element.locator("strong")
            depart_airline_city = self.get_text(depart_airline_city)
            segment_origin = self.get_text(depart_airline_city_code_element).replace(depart_airline_city, "").strip()
            airline_attributes = flight_detail_container[1]
            airline_info = airline_attributes.locator("div.airline-info div.airline-details span").all()
            segment_flight_number = self.get_text(airline_info[0])
            segment_carrier, segment_flight_number = extract_flight_number(segment_flight_number)
            # segment_carrier = self.get_text(airline_info[1]).replace("| Operated by", "").strip()
            segment_aircraft = self.get_text(airline_info[2])

            # Arrival
            segment_arrival_info_element = segment_items[1]
            segment_arrival_time_element = segment_arrival_info_element.locator("div.flight-timings span").nth(0)
            segment_arrival_time = extract_iso_time(self.get_text(segment_arrival_time_element))
            try:
                segment_arrival_day_element = segment_depart_info_element.locator(
                    "div.flight-timings span.arrival-days",
                )
                segment_arrival_day_element.wait_for(timeout=1000)
                arrival_days_delta = self.get_text(segment_arrival_day_element)
                if arrival_days_delta:
                    arrival_days_delta = int(extract_digits(arrival_days_delta))
                    segment_arrival_date = departure_date + datetime.timedelta(days=arrival_days_delta)
            except Exception:
                segment_arrival_date = departure_date
            arrival_airline_city_code_element = segment_arrival_info_element.locator(
                "div.flight-details-container span"
            ).nth(0)

            arrival_airline_city = arrival_airline_city_code_element.locator("strong")
            arrival_airline_city = self.get_text(arrival_airline_city)

            segment_destination = (
                self.get_text(arrival_airline_city_code_element).replace(arrival_airline_city, "").strip()
            )
            flight_segments.append(
                FlightSegment(
                    origin=segment_origin,
                    destination=segment_destination,
                    departure_date=segment_departure_date and segment_departure_date.isoformat(),
                    departure_time=segment_departure_time,
                    departure_timezone="",
                    arrival_date=segment_arrival_date and segment_arrival_date.isoformat(),
                    arrival_time=segment_arrival_time,
                    arrival_timezone="",
                    aircraft=segment_aircraft,
                    flight_number=segment_flight_number,
                    carrier=segment_carrier,
                )
            )
        try:
            page.get_by_text("Close").click()
        except Exception:
            pass

        return flight_segments

    def extract_sub_classes_points(
        self, page, flight_row_element, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        cabin_class_code = CabinClassCodeMapping[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        found_available_points = False
        try:
            target_cabin_class_cell = flight_row_element.locator(
                f"//kilo-cabin-cell-pres[contains(@data-analytics-val, '{cabin_class_code}')]/div"
            )
            target_cabin_class_cell.wait_for(timeout=200)
            target_cabin_class_cell.click()
            found_available_points = True
            time.sleep(1)
        except Exception as e:
            logger.error(f"{self.AIRLINE.value}: click detail sub points exception {e}")
            return None

        fare_names_elements = page.locator("div.fare-headers span").all()
        fare_details_elements = page.locator("div.fare-list div.fare-list-item").all()
        for fare_name_element, fare_details_element in zip(fare_names_elements, fare_details_elements):
            try:
                fare_name = self.get_text(fare_name_element)
                not_available = False
                try:
                    not_available_ele = fare_details_element.locator("div.fare-button-price-space")
                    not_available_str = self.get_text(not_available_ele)
                    if "Not available" == not_available_str:
                        not_available = True
                except Exception:
                    logger.info(f"{self.AIRLINE.value}: Not available {fare_name}")
                    pass

                if not_available:
                    points_by_fare_names[fare_name] = {
                        "points": -1,
                        "cash_fee": CashFee(
                            amount=0,
                            currency="",
                        ),
                    }
                    continue

                point_element = fare_details_element.locator("div.price-container div.points span")
                points = self.get_text(point_element)
                cash_fee_element = fare_details_element.locator(
                    "div.price-container kilo-price span",
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
            except PlayWrightTimeoutError:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points PlayWrightTimeoutError")
                continue
            except Exception as e:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")
        try:
            # flight_row_element.get_by_role(
            #     "button",
            #     name=re.compile(f"{cabin_class_code}", re.IGNORECASE)
            # ).click()
            if found_available_points:
                flight_row_element.locator(
                    f"//kilo-cabin-cell-pres[contains(@data-analytics-val, '{cabin_class_code}')]/div"
                ).click()
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"{self.AIRLINE.value}: >>>>>>>> closing sub points exception {e}")
            return None
        return points_by_fare_names

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        logger.info(f"{self.AIRLINE.value}: Searching results...")
        provided_cabin_classes = [
            self.get_text(element).lower() for element in page.locator("//div[@class='cabin-heading']").all()
        ]
        if CabinClassCodeMapping[cabin_class] not in provided_cabin_classes:
            raise NoSearchResult(airline=self.AIRLINE)

        try:
            # clicking filter by stops option
            page.click(
                "//button[@aria-label='Stops']",
                timeout=c.HIGH_SLEEP * 1000,
            )
            time.sleep(0.5)
        except Exception as e:
            raise CannotContinueSearch(airline=self.AIRLINE, reason=f"{e}")

        try:
            # selecting onestop option
            page.click(
                "//mat-radio-button[@name='oneStop']/label",
                timeout=c.HIGH_SLEEP * 1000,
            )
            time.sleep(1)
        except Exception as e:
            raise CannotContinueSearch(airline=self.AIRLINE, reason=f"{e}")

        try:
            page.click("//div[@class='close-icon-container']", timeout=c.LOWEST_SLEEP * 1000)
            flight_search_results = page.locator(
                '//div[@class="page-container"]//kilo-upsell-cont//kilo-upsell-pres'
                "//kilo-upsell-row-cont/kilo-upsell-row-pres",
            ).all()
        except TimeoutError:
            raise NoSearchResult(airline=self.AIRLINE)

        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

            points_by_fare_names = self.extract_sub_classes_points(page, flight_search_result, cabin_class)
            if not points_by_fare_names:
                continue

            try:
                segments = self.extract_flight_detail(page, flight_search_result, departure_date)
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
                if not segments:
                    continue
                flight = Flight(
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
                yield flight


if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults=1):
        start_time = time.perf_counter()
        crawler = AirCanadaPlaywrightCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=8, day=27)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                cabin_class=cabin_class,
                adults=adults,
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
    # run("LAX", "JFK", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    run("YVR", "YYZ", c.CabinClass.Economy, 2)
    # run("KUL", "YYZ", c.CabinClass.First)
