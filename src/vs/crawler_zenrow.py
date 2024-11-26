import datetime
import logging
import random
from typing import Iterator, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from src import constants as c
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, ZenRowFailed
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_time_string_to_iso_format,
    extract_currency_and_amount,
    extract_flight_number,
)
from src.vs.constants import CabinClassCodeMapping

logger = logging.getLogger(__name__)


class VirginAtlanticZenrowCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.VirginAtlantic

    @staticmethod
    def months_until_target(departure_date: datetime.date):
        current_date = datetime.date.today()
        months_until = (departure_date.year - current_date.year) * 12 + (departure_date.month - current_date.month)
        return months_until

    @staticmethod
    def extract_points(flight_row_element, cabin_class: CabinClass) -> Optional[Tuple[str, float, CashFee]]:
        airline_cabin_class = CabinClassCodeMapping[cabin_class]
        price_btn = flight_row_element.select_one(f".brandWrapperVS{airline_cabin_class} .farecelloffered")
        if not price_btn:
            return None
        fare_name_element = price_btn.select_one(".cabinContainer .flightcardDetails a span:first-child")
        if not fare_name_element:
            return None

        fare_name = fare_name_element.get_text(strip=True).strip(" +")
        try:
            points_element = price_btn.select_one(".tblCntMileBigTxt")
            points = points_element.get_text(strip=True)
            points = int(points.replace(",", ""))
            cash_fee_element = price_btn.select_one(".tblCntMilesSmalltxt")
            cash_fee = cash_fee_element.get_text(strip=True)
            currency, amount = extract_currency_and_amount(cash_fee.replace("+", "").strip())
            return fare_name, points, CashFee(currency=currency, amount=amount)
        except AttributeError:
            return None

    @staticmethod
    def get_evaluate_param(origin: str, destination: str, departure_date: datetime.date, adults: int = 1):
        departure_date_str = departure_date.strftime("%m/%d/%Y")
        # {"evaluate": "const containerDiv = document.querySelector('.search-result-container'); var firstChild = containerDiv.firstElementChild; var firstchild2 = firstChild.firstElementChild; var li = firstchild2.firstElementChild; var abtn = li.firstElementChild; abtn.click();"},
        evaluate_param = """[
            {"evaluate": "document.querySelector('#privacy-btn-reject-all').click();"},
            {"wait_for": "#fromAirportName"},
            {"evaluate": "const originButton = document.getElementById('fromAirportName'); originButton.click();"},
            {"evaluate": "document.getElementById('search_input').value = '';"},
            {"evaluate": "const inputElement = document.querySelector('#search_input'); inputElement.value = '%s'; inputElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));"},
            {"wait_for": ".airportLookup-list"},
            {"evaluate": "const containerDiv = document.querySelector('.search-result-container'); const listItems = containerDiv.querySelectorAll('li'); listItems.forEach(item => { if (item.querySelector('span').innerText.includes('%s')) { item.querySelector('a').click(); } });"},
            {"evaluate": "const destinationButton = document.getElementById('toAirportName'); destinationButton.click();"},
            {"evaluate": "document.getElementById('search_input').value = '';"},
            {"evaluate": "const inputElement = document.querySelector('#search_input'); inputElement.value = '%s'; inputElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));"},
            {"wait_for": ".airportLookup-list"},
            {"evaluate": "const containerDiv = document.querySelector('.search-result-container'); const listItems = containerDiv.querySelectorAll('li'); listItems.forEach(item => { if (item.querySelector('span').innerText.includes('%s')) { item.querySelector('a').click(); } });"},
            {"evaluate": "const tripTypeButton = document.querySelector('.select-ui-wrapper.ng-tns-c1-2'); tripTypeButton.click();"},
            {"evaluate": "document.getElementById('ui-list-selectTripType1').click();"},
            {"click": "#input_departureDate_1"},
            {"wait_for": ".dl-state-default"},
        """
        months_until = VirginAtlanticZenrowCrawler.months_until_target(departure_date) - 1
        if months_until > 0:
            for _ in range(months_until):
                evaluate_param += """
                    {"evaluate": "document.querySelector('.dl-datepicker-1').click()"},
                    {"wait": 200},
                """

        evaluate_param += """
            {"click": "[data-date*='%s']"},
        """

        if adults > 1:
            evaluate_param += """
                    {"click": "#passenger"},
                    {"wait_for": ".pax-optionList"},
                """
            for _ in range(adults - 1):
                evaluate_param += """
                    {"evaluate": "document.querySelector('.pax-optionList.pax-ADT .add-pax a').click();"},
                    {"wait": 200},
                    """

        evaluate_param += """
            {"evaluate": "const searchButton = document.getElementById('btn-book-submit'); searchButton.click();"},
            {"wait": 13000},
            {"wait_for": ".btn.btn-moneymiles.ng-star-inserted"},
            {"evaluate": "const parentDiv = document.querySelectorAll('.btn.btn-moneymiles.ng-star-inserted');parentDiv[1].click();"},
            {"wait": 20000}
        ]"""

        return evaluate_param % (origin, origin, destination, destination, departure_date_str)

    def parse_flight(
        self, flight_row_element, departure_date: datetime.date, cabin_class: CabinClass.Economy
    ) -> Optional[Flight]:
        segments: List[FlightSegment] = []
        fare = self.extract_points(flight_row_element, cabin_class=cabin_class)
        if fare is None:
            return None

        fare_name, points, cash_fee = fare
        departure_time = flight_row_element.find("span", class_="trip-time pr0-sm-down").text.strip()
        departure_time = convert_time_string_to_iso_format(departure_time)
        arriving_info = flight_row_element.find("span", class_="trip-time pl0-sm-down").text.strip()
        arrival_date = flight_row_element.find("span", class_="travelDate")
        if arrival_date:
            arrival_date = arrival_date.text.strip()
            arrival_time = arriving_info.replace(arrival_date, "")
            arrival_date = datetime.datetime.strptime(arrival_date, "%a %d %b")
            # TODO: This might be incorrect when the departure_date is last day of the year
            #  and the arrival date is in next year, should be fixed
            arrival_date = arrival_date.replace(year=departure_date.year).date()
        else:
            arrival_date = departure_date
            arrival_time = arriving_info

        arrival_time = convert_time_string_to_iso_format(arrival_time)
        airport_elements = flight_row_element.find_all("div", class_="flightSecFocus")
        airports = [
            "".join([content.strip() for content in airport_element.contents if isinstance(content, str)])
            for airport_element in airport_elements
        ]
        flight_number_divs = flight_row_element.find_all("div", class_="d-inline-block ng-star-inserted")
        flight_numbers = [div.find("a").text.strip() for div in flight_number_divs]

        for segment_index, flight in enumerate(flight_numbers):
            carrier, flight_number = extract_flight_number(flight)
            segment_departure_date = departure_date.isoformat() if segment_index == 0 else None
            segment_departure_time = departure_time if segment_index == 0 else None
            segment_arrival_date = arrival_date.isoformat() if segment_index == len(flight_numbers) - 1 else None
            segment_arrival_time = arrival_time if segment_index == len(flight_numbers) - 1 else None

            segments.append(
                FlightSegment(
                    origin=airports[segment_index],
                    destination=airports[segment_index + 1],
                    departure_date=segment_departure_date,
                    departure_time=segment_departure_time,
                    arrival_date=segment_arrival_date,
                    arrival_time=segment_arrival_time,
                    flight_number=flight_number,
                    carrier=carrier,
                )
            )

        return Flight(
            airline=str(self.AIRLINE.value),
            origin=airports[0],
            destination=airports[-1],
            cabin_class=cabin_class.value,
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
        cabin_class: CabinClass = CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        try:
            url = "https://www.virginatlantic.com/us/en"
            evaluate_param = self.get_evaluate_param(origin, destination, departure_date, adults)
            params = {
                "url": url,
                "apikey": c.ZENROWS_API_KEY,
                "js_render": "true",
                "antibot": "true",
                "wait_for": ".container.booking-widget_container-mobile",
                "premium_proxy": "true",
                "proxy_country": random.choice(["us", "ca"]),
                "json_response": "true",
                "js_instructions": evaluate_param,
            }
            logger.info(f"{self.AIRLINE.value}: Making Zenrows calls...")
            response = requests.get("https://api.zenrows.com/v1/", params=params)
            if response.status_code != 200:
                raise ZenRowFailed(airline=self.AIRLINE, reason=response.text)

            json_data = response.json()
            html_content = json_data.get("html", "")
            soup = BeautifulSoup(html_content, "lxml")
            flight_cards = soup.find_all("div", class_="shadow-sm")
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_cards)} flights...")
            for index, flight_row_element in enumerate(flight_cards):
                flight = self.parse_flight(flight_row_element, departure_date, cabin_class)
                if flight:
                    yield flight

        except (LiveCheckerException, Exception) as e:
            raise e


if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = VirginAtlanticZenrowCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=40)
        departure_date = datetime.date(year=2024, month=8, day=23)
        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
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

    run("IAD", "AMD", CabinClass.Economy, 1)
    # run("JFK", "LHR", CabinClass.Economy, 1)
    # run("DFW", "JFK", CabinClass.Economy)
