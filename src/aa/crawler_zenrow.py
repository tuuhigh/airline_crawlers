# TODO: Properly handle routes that AA does not operate.
#
import datetime
import random
import re
from collections import namedtuple
from typing import Iterator, List, Optional

import requests
from bs4 import BeautifulSoup

from src import constants as c
from src.aa.constants import CabinClassMap
from src.base import RequestsBasedAirlineCrawler, logger
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, ZenRowFailed
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_k_to_float,
    convert_time_string_to_iso_format,
    extract_digits_before_text,
    extract_flight_number,
)

FlightTime = namedtuple("FlightTime", ["date", "time", "timezone"])


class AmericanAirlineZenrowCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.AmericanAirline

    def parse_flight(
        self, flight_row_element, departure_date: datetime.date, cabin_class: CabinClass = CabinClass.Economy
    ) -> Optional[Flight]:
        airline_cabin_class = CabinClassMap[cabin_class]
        cabin_element = flight_row_element.find("span", class_="hidden-product-type", string=f"{airline_cabin_class}")
        if cabin_element is None:
            return None

        if airline_cabin_class == "Main":
            airline_cabin_class = "Main Cabin"

        origin = flight_row_element.find("div", class_="origin").find("div", class_="city-code").text.strip()
        destination = flight_row_element.find("div", class_="destination").find("div", class_="city-code").text.strip()

        point_element = cabin_element.find_parent()
        miles_cost_str = point_element.find("span", class_="per-pax-amount").text.strip()
        points = convert_k_to_float(miles_cost_str)
        price_currency = point_element.find("div", class_="per-pax-addon").text.strip()
        pattern_for_price = re.compile(r"\$\s*([\d.]+)")
        # Search for the pattern in the input string
        match = pattern_for_price.search(price_currency)
        currency_price = match.group(0)  # The entire matched string (including $)
        amount = match.group(1)
        currency = currency_price.replace(amount, "")
        departure_time = flight_row_element.select_one(".origin .flt-times").text.strip()
        departure_time = convert_time_string_to_iso_format(departure_time)
        arrival_time = flight_row_element.select_one(".destination .flt-times").text.strip()

        if len(arrival_time.split("+")) > 1:
            days_delta = int(extract_digits_before_text(arrival_time.split("+")[-1]))
            arrival_date = departure_date + datetime.timedelta(days=days_delta)
        else:
            arrival_date = departure_date

        arrival_time = convert_time_string_to_iso_format(arrival_time)
        duration = flight_row_element.find("div", class_="duration").text.strip()
        if duration:
            duration = 'PT' + duration.replace(' ', '').upper()
        flight_aircraft_elements = flight_row_element.find_all("div", class_="leg-info")
        segments: List[FlightSegment] = []

        for segment_index, flight_aircraft_row in enumerate(flight_aircraft_elements):
            flight_number = flight_aircraft_row.select_one(".flight-number").text.strip()
            carrier, flight_number = extract_flight_number(flight_number)
            aircraft_name = flight_aircraft_row.select_one(".aircraft-name").text.strip()
            origin_dest = flight_aircraft_row.select_one(".cities")
            if origin_dest:
                origin_dest = origin_dest.text.strip()
                segment_origin, segment_destination = origin_dest.split(" - ")
            else:
                segment_origin = origin
                segment_destination = destination

            segment_departure_date = departure_date.isoformat() if segment_index == 0 else None
            segment_departure_time = departure_time if segment_index == 0 else None
            segment_arrival_date = (
                arrival_date.isoformat() if segment_index == len(flight_aircraft_elements) - 1 else None
            )
            segment_arrival_time = arrival_time if segment_index == len(flight_aircraft_elements) - 1 else None

            segments.append(
                FlightSegment(
                    origin=segment_origin,
                    destination=segment_destination,
                    departure_date=segment_departure_date,
                    departure_time=segment_departure_time,
                    arrival_date=segment_arrival_date,
                    arrival_time=segment_arrival_time,
                    carrier=carrier,
                    flight_number=flight_number,
                    aircraft=aircraft_name,
                )
            )

        return Flight(
            airline=str(self.AIRLINE.value),
            origin=origin,
            destination=destination,
            cabin_class=str(cabin_class.value),
            airline_cabin_class=airline_cabin_class,
            points=points,
            cash_fee=CashFee(currency=currency, amount=float(amount)),
            segments=segments,
            duration=duration,
        )

    def parse_flight_segment(self) -> FlightSegment:
        pass

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
            url = (
                f"https://www.aa.com/booking/search?locale=en_US&pax=1&adult={adults}"
                "&type=OneWay&searchType=Award&cabin=&carriers=ALL"
                f"&slices=%5B%7B%22orig%22:%22{origin}%22,%22origNearby%22:false,"
                f"%22dest%22:%22{destination}%22,%22destNearby%22:false,"
                f"%22date%22:%22{departure_date.isoformat()}%22%7D%5D"
            )
            params = {
                "url": url,
                "apikey": c.ZENROWS_API_KEY,
                "js_render": "true",
                "antibot": "true",
                "premium_proxy": "true",
                "wait_for": ".grid-padding-x",
                "block_resources": "image,media,font",
                "json_response": "true",
                "proxy_country": random.choice(["us", "ca"]),
            }
            response = requests.get("https://api.zenrows.com/v1/", params=params)
            if response.status_code != 200:
                raise ZenRowFailed(airline=self.AIRLINE, reason=response.text)

            logger.info(f"{self.AIRLINE.value} Got Zenrows response...")
            json_data = response.json()
            html_content = json_data.get("html", "")
            soup = BeautifulSoup(html_content, "lxml")
            flight_cards = soup.find_all("div", class_="grid-padding-x")
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_cards)} flights...")
            
            all_cabins = []
            if cabin_class == CabinClass.All:
                all_cabins = [
                    CabinClass.Economy,
                    CabinClass.PremiumEconomy,
                    CabinClass.Business,
                    CabinClass.First
                ]
            else:
                all_cabins = [cabin_class]
                
            for index, flight_row_element in enumerate(flight_cards):
                for cabin in all_cabins:
                    flight = self.parse_flight(flight_row_element, departure_date, cabin)
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
        crawler = AmericanAirlineZenrowCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=8, day=29)
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
            with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}_zenrow.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    # run("CPT", "HAV", CabinClass.Economy)
    # run("LAX", "HND", CabinClass.Economy)
    # run("LAX", "HND", CabinClass.PremiumEconomy)
    # run("LAX", "HND", CabinClass.Business)
    # run("JFK", "LHR", CabinClass.Economy, 1)
    run("ORD", "BCN", CabinClass.All, 1)
