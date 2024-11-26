import asyncio
import datetime
import json
import logging
import random
import re
import time
from typing import Dict, Iterator, List, Tuple, TypedDict

import requests
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from isodate import duration_isoformat, parse_duration

from src import constants as c
from src.base import RequestsBasedAirlineCrawler
from src.dl.constants import AirCraftIATACode, CabinClassMapping
from src.exceptions import ZenRowFailed
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_human_time_to_seconds,
    convert_time_string_to_iso_format,
    extract_digits,
    extract_flight_number,
    sanitize_text,
)

logger = logging.getLogger(__name__)

REGION_URLS = [
    {"us": "https://www.delta.com"},
    {"ca": "https://www.delta.com/ca/en"},
    {"gb": "https://www.delta.com/gb/en"},
    {"de": "https://www.delta.com/eu/en"},
    {"fr": "https://www.delta.com/fr/en"},
    {"mx": "https://www.delta.com/mx/en"},
    {"br": "https://www.delta.com/br/en"},
]


class DeltaFlightDetailRequestPayload(TypedDict):
    originAirportCode: str
    destinationAirportCode: str
    schedLocalDepartDate: str
    marketingAirlineCode: str
    operatingAirlineCode: str
    classOfServiceList: List[str]
    flightNumber: str


class DeltaAirlineZenrowCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = c.Airline.DeltaAirline

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fare_codes: Dict[str, str] = {}

    @staticmethod
    def months_until_target(departure_date: datetime.date):
        current_date = datetime.date.today()
        months_until = (departure_date.year - current_date.year) * 12 + (departure_date.month - current_date.month)
        return months_until

    @staticmethod
    def get_evaluate_param(
        origin: str, destination: str, departure_date: datetime.date, adults: int, shop_miles: bool
    ):
        evaluate_param = """[
            {"click": ".btn-danger.gdpr-banner-btn.gdpr-banner-accept-btn"},
            {"wait": 1000},
            {"click": ".btn-keep.btn.btn-outline-secondary-cta.rounded-0"},
            {"wait": 1000},
            {"evaluate": "document.querySelector('#fromAirportName').click()"},
            {"wait": 750},
            {"evaluate": "const searchInput = document.getElementById('search_input'); if (searchInput) {searchInput.value = '%s';} const closeButton = document.querySelector('.search-flyout-close.float-right.d-none.d-lg-block.circle-outline.icon-moreoptionsclose'); if (closeButton) {closeButton.click();}"},
            {"wait": 1200},
            {"evaluate": "const anchorElement = document.querySelector('#toAirportName'); if (anchorElement) {anchorElement.click();}"},
            {"wait": 750},
            {"evaluate": "const searchInput = document.getElementById('search_input'); if (searchInput) {searchInput.value = '%s';} const closeButton = document.querySelector('.search-flyout-close.float-right.d-none.d-lg-block.circle-outline.icon-moreoptionsclose'); if (closeButton) {closeButton.click();}"},
            {"wait": 1200},
            {"click": ".trip-type-container .select-ui-wrapper"},
            {"wait": 1100},
            {"click": "#ui-list-selectTripType1"},
            {"wait": 1100},
            {"click": ".calenderDepartSpan"},
            {"wait": 900},
            """ % (
            origin,
            destination,
        )

        months_until = DeltaAirlineZenrowCrawler.months_until_target(departure_date) - 1

        click_string = ""
        if months_until > 0:
            for _ in range(months_until):
                click_string += """
                        {"evaluate": "document.querySelectorAll('.monthSelector')[1].click()"},
                        {"wait": 200},
                    """

        evaluate_param += click_string

        select_date_string = """
            {"click": "[data-date*='%s']"},
            {"wait": 800},
        """ % departure_date.strftime(
            "%m/%d/%Y"
        )

        evaluate_param += select_date_string

        if adults > 1:
            evaluate_param += """
                {"click": ".passenger-booking-element .select-ui-wrapper"},
                {"wait": 200},
                {"click": "#ui-list-passengers%s"},
            """ % (
                adults - 1
            )

        if shop_miles:
            click_shop_miles_string = """
                {"click": "label[for='shopWithMiles']"},
                {"wait": 500},
                {"click": "label[for='chkFlexDate']"},
                {"wait": 500},
            """
            evaluate_param += click_shop_miles_string

        # press_submit = """
        #     {"click": "button[id='btn-book-submit']"},
        #     {"wait": 22000},
        # """
        press_submit = """
            {"evaluate": "document.querySelector('#btn-book-submit').click()"},
            {"wait_for": ".search-results__grid container-lg-up"},
            {"wait": 3000},
        """

        evaluate_param += press_submit

        press_accept_cookies = """
            {"click": ".btn-danger.gdpr-banner-btn.gdpr-banner-accept-btn"},
            {"wait": 2000},
        """
        evaluate_param += press_accept_cookies

        # press_to_see_more = """
        #     {"click": ".idp-btn"},
        #     {"wait": 4000},
        #     {"click": ".idp-btn"},
        #     {"wait": 4000}
        # """

        press_to_see_more = """
            {"click": ".idp-btn"},
            {"wait": 10000}
        """

        evaluate_param += press_to_see_more

        evaluate_param += "]"

        return evaluate_param

    @staticmethod
    def parse_cabin_classes(soup: BeautifulSoup):
        search_result_class_header = soup.find("idp-brand-cabin-types")
        all_class_header = search_result_class_header.find_all("a")

        cabin_classes = []

        for airline_cabin_class in all_class_header:
            airline_cabin_class = airline_cabin_class.text.strip()
            cabin_classes.append(airline_cabin_class)

        return cabin_classes

    @staticmethod
    def parse_flight_info(flight_row_element):
        try:
            flight_card_info = flight_row_element.find("idp-flight-card-info")

            flights = flight_card_info.select_one('div[class*="flight-number"]').find_all("a")
            flight_numbers = []
            for flight in flights:
                flight_no = flight.span.contents[0].strip()
                flight_numbers.append(flight_no)
            flight_duration = sanitize_text(flight_card_info.select_one('div[class*="flight-duration"]').text)
            flight_duration = duration_isoformat(
                datetime.timedelta(seconds=convert_human_time_to_seconds(flight_duration))
            )
            return flight_numbers, flight_duration
        except Exception as e:
            print(">>>>> parse_flight_info:", e)

    @staticmethod
    def parse_flight_schedule(flight_row_element, departure_date: datetime.date):
        flight_card_schedule = flight_row_element.find("idp-flight-card-schedule")

        schedule = flight_card_schedule.select_one('div[class*="schedule-time-container"]').find_all("div")
        departure_time = convert_time_string_to_iso_format(schedule[0].text.strip())
        arrival_time = convert_time_string_to_iso_format(schedule[1].text.strip())

        arrival_date = flight_card_schedule.select_one("div[class*=next-day-schedule]")
        if arrival_date:
            arrival_date = arrival_date.text.strip()
            arrival_date = datetime.datetime.strptime(arrival_date, "%a %d %b")
            # TODO: this logic might not work when arrival date is next year
            arrival_date = arrival_date.replace(year=departure_date.year)
            arrival_date = arrival_date.date()

        return departure_time, arrival_date, arrival_time

    @staticmethod
    def parse_airports(flight_row_element) -> Tuple[list[str], list[str]]:
        try:
            airports = []
            layover_times = []
            flight_card_path = flight_row_element.find("idp-flight-card-path")

            origin = flight_card_path.select_one('div[class*="flight-card-path__start"]').text.strip()
            airports.append(origin)
            destination = flight_card_path.select_one('div[class*="flight-card-path__end"]').text.strip()

            layovers = flight_card_path.select('span[class*="flight-card-path__layover"]')

            for layover in layovers:
                layover_str = layover.text.strip()
                layover_detail = layover_str.split()
                layover_airport = layover_detail[0]
                layover_time = layover_str.replace(layover_airport, "").strip()
                airports.append(layover_airport)
                layover_time = sanitize_text(layover_time)
                layover_time = duration_isoformat(
                    datetime.timedelta(seconds=convert_human_time_to_seconds(layover_time))
                )
                layover_times.append(layover_time)

            airports.append(destination)
            return airports, layover_times
        except Exception as e:
            print(f">>>>>>> parse_airports: {e}")

    @staticmethod
    def parse_flight_points(flight_row_element, cabin_classes) -> dict[str, Tuple[float, CashFee]]:
        flight_fare_row = flight_row_element.find("idp-fare-cell-desktop-row")
        miles_cells = flight_fare_row.find_all("idp-fare-cell-desktop")

        pricing_data = {}

        for i, miles_data in enumerate(miles_cells):
            cabin_class = cabin_classes[i]

            points = miles_data.select_one('div[class*="fare-cell-miles-value"]')
            if points:
                points = float(extract_digits(points.text.strip()))
                currency = miles_data.select_one('span[class*="fare-cell-currency"]').text.strip()
                amount = miles_data.select_one('span[class*="fare-cell-rounded-amount"]').text.strip()
                pricing_data[cabin_class] = (points, CashFee(amount=float(amount), currency=currency))

        return pricing_data

    @staticmethod
    def parse_flight_pricing(flight_row_element, cabin_classes) -> dict[str, float]:
        flight_fare_row = flight_row_element.find("idp-fare-cell-desktop-row")
        miles_cells = flight_fare_row.find_all("idp-fare-cell-desktop")

        pricing_data = {}

        for i, miles_data in enumerate(miles_cells):
            cabin_class = cabin_classes[i]

            pricing_element = miles_data.select_one('div[class*="fare-cell-amount"]')
            if pricing_element:
                amount = float(extract_digits(pricing_element.text.strip()))
                # currency = miles_data.select_one('span[class*="fare-cell-currency"]').text.strip()
                pricing_data[cabin_class] = amount

        return pricing_data

    @staticmethod
    def parse_fare_code(flight_row_element) -> list[str]:
        try:
            flight_card = flight_row_element.find("idp-flight-card")
            fare_code_element = flight_card.select_one('div[class*="brand-name ng-star-inserted"]')
            fare_codes = []
            if fare_code_element:
                fare_codes = fare_code_element.text.strip()
                match = re.search(r"\((.*?)\)", fare_codes)
                if match:
                    fare_codes = match.group(1).split(",")
                    fare_codes = list(map(str.strip, fare_codes))
            return fare_codes
        except Exception as e:
            logger.error(f">> parse_fare_code error: {e}")

    def parse_flight(self, flight_row_element, cabin_class: c.CabinClass, departure_date: datetime.date) -> Flight:
        fare_codes = self.parse_fare_code(flight_row_element)
        flight_numbers, flight_duration = self.parse_flight_info(flight_row_element)
        airports, layover_times = self.parse_airports(flight_row_element)
        departure_time, arrival_date, arrival_time = self.parse_flight_schedule(flight_row_element, departure_date)
        if arrival_date is None:
            arrival_date = departure_date

        segments = []
        has_overlay = len(flight_numbers) > 1
        for segment_index, flight_number in enumerate(flight_numbers):
            if segment_index == 0:
                segment_departure_date = departure_date.isoformat()
                segment_departure_time = departure_time
            else:
                segment_departure_date = segment_departure_time = None

            if segment_index == len(flight_numbers) - 1:
                segment_arrival_date = arrival_date.isoformat()
                segment_arrival_time = arrival_time
            else:
                segment_arrival_date = segment_arrival_time = None

            layover_time = None
            if has_overlay and segment_index < len(flight_numbers) - 1:
                layover_time = layover_times[segment_index]
            segment_carrier, segment_flight_number = extract_flight_number(flight_number)

            segment = FlightSegment(
                origin=airports[segment_index],
                destination=airports[segment_index + 1],
                departure_date=segment_departure_date,
                departure_time=segment_departure_time,
                arrival_date=segment_arrival_date,
                arrival_time=segment_arrival_time,
                flight_number=segment_flight_number,
                layover_time=layover_time,
                carrier=segment_carrier,
            )
            segments.append(segment)
            try:
                self.fare_codes[segment.id] = fare_codes[segment_index]
            except IndexError:
                # Take a look at https://www.pointsfeed.com/blog/delta-fare-classes/
                # if you are not good at fare code
                self.fare_codes[segment.id] = "M"

        return Flight(
            airline=str(self.AIRLINE.value),
            origin=segments[0].origin,
            destination=segments[-1].destination,
            cabin_class=str(cabin_class.value),
            segments=segments,
            duration=flight_duration,
        )

    @staticmethod
    def get_flight_segments(segments: List[DeltaFlightDetailRequestPayload]):
        headers = {
            "authority": "flightspecific-api.delta.com",
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,vi;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": "https://www.delta.com",
            "pragma": "no-cache",
            "referer": "https://www.delta.com/",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        json_data = {
            "legList": segments,
            "pageId": "dynamic-modal",
            "appId": "sho",
            "channelId": "ecomm",
            "brandAPIResponse": True,
        }
        response = requests.post(
            "https://flightspecific-api.delta.com/shopping/v1/flight-details", headers=headers, json=json_data
        )
        response_json = response.json()
        return response_json

    def fill_missing_segment_info(self, flight_segments: List[FlightSegment]):
        payloads = [
            DeltaFlightDetailRequestPayload(
                originAirportCode=segment.origin,
                destinationAirportCode=segment.destination,
                schedLocalDepartDate=f"{segment.departure_date}T{segment.departure_time}",
                marketingAirlineCode=segment.carrier,
                operatingAirlineCode=segment.carrier,
                classOfServiceList=[self.fare_codes[segment.id]],
                flightNumber=segment.flight_number,
            )
            for segment in flight_segments
        ]
        data = self.get_flight_segments(payloads)
        flight_segments_dict = {
            f"{fs.get('operatingFlightNum')}_{fs.get('schedDepartLocalTs')}": fs
            for fs in data.get("flightSegment", [])
        }
        for segment in flight_segments:
            key = f"{segment.flight_number}_{segment.departure_date}T{segment.departure_time}:00"
            flight_segment = flight_segments_dict.get(key, {})
            flight_legs = flight_segment.get("flightLeg", [])
            flight_leg = flight_legs and flight_legs[0] or {}
            aircraft = flight_legs and flight_legs[0].get("aircraft", {}) or {}
            fleet_type_code = aircraft.get("fleetTypeCode", "")
            aircraft = AirCraftIATACode.get(fleet_type_code)
            if aircraft:
                segment.aircraft = aircraft

            if not segment.arrival_date and not segment.arrival_time:
                arrival_dt = flight_leg.get("schedArrivalLocalTs", "")
                arrival_date_and_time = arrival_dt and arrival_dt.split("T")
                if arrival_date_and_time:
                    segment.arrival_date = arrival_date_and_time[0]
                    segment.arrival_time = arrival_date_and_time[1][:5]

    def fill_missing_flight_info(self, flights: List[Flight]):
        segment_index = 0
        while True:
            flight_segments = []
            for flight in flights:
                if len(flight.segments) <= segment_index:
                    continue

                flight_segment = flight.segments[segment_index]
                if segment_index >= 1:
                    previous_segment = flight.segments[segment_index - 1]
                    if (
                        previous_segment.arrival_date
                        and previous_segment.arrival_time
                        and previous_segment.layover_time
                    ):
                        previous_arrival = f"{previous_segment.arrival_date} {previous_segment.arrival_time}:00"
                        previous_arrival_dt = datetime.datetime.fromisoformat(previous_arrival)
                        next_departure_dt = previous_arrival_dt + parse_duration(previous_segment.layover_time)
                        flight_segment.departure_date = next_departure_dt.strftime("%Y-%m-%d")
                        flight_segment.departure_time = next_departure_dt.strftime("%H:%M")
                flight_segments.append(flight_segment)

            if not flight_segments:
                break

            segment_index += 1
            self.fill_missing_segment_info(flight_segments)

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        flights = asyncio.run(self.get_flights(origin, destination, departure_date, cabin_class, adults))
        self.fill_missing_flight_info(flights)
        for flight in flights:
            yield flight

    async def get_flights(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:
        async with ClientSession() as session:
            tasks = [
                self.get_flights_pricing(session, origin, destination, departure_date, cabin_class, adults),
                self.get_flights_points(session, origin, destination, departure_date, cabin_class, adults),
            ]
            flights_pricing, flights_points = await asyncio.gather(*tasks, return_exceptions=True)
            if isinstance(flights_pricing, Exception) and isinstance(flights_points, Exception):
                print(f">>>>>>>>>>>>flights_pricing: {flights_pricing}")
                print(f">>>>>>>>>>>>flights_points: {flights_points}")
                raise ZenRowFailed(airline=self.AIRLINE, reason="Pricing & Points requests all failed")
            elif isinstance(flights_pricing, list) and isinstance(flights_points, list):
                flights_points_by_finger_print: dict[str, Flight] = {
                    flight.finger_print: flight for flight in flights_points
                }
                flights = []
                for flight in flights_pricing:
                    finger_print = flight.finger_print
                    if finger_print in flights_points_by_finger_print:
                        flight_point_data = flights_points_by_finger_print.pop(finger_print)
                        flight.points = flight_point_data.points
                        flight.cash_fee = flight_point_data.cash_fee

                    flights.append(flight)

                for flight in flights_points_by_finger_print.values():
                    flights.append(flight)

                return flights
            else:
                return flights_pricing if isinstance(flights_pricing, list) else flights_points

    async def get_flights_pricing(
        self,
        session: ClientSession,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:
        # Zenrow is vulnerable to concurrent requests, We make 2 concurrent zenrow requests,
        # one for pricing, one for points, So adding time delay might be helpful
        # await asyncio.sleep(5)

        flights = []
        eval_param = self.get_evaluate_param(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            shop_miles=False,
            adults=adults,
        )

        region = random.choice(REGION_URLS)
        proxy_region, url = next(iter(region.items()))

        params = {
            "url": url,
            "apikey": c.ZENROWS_API_KEY,
            "js_render": "true",
            "antibot": "true",
            "wait_for": "#booking.book-widget-container.container-padding-x",
            "premium_proxy": "true",
            "proxy_country": proxy_region,
            "json_response": "true",
            # "window_width": "1920",
            # "window_height": "1080",
            "js_instructions": eval_param,
        }
        logger.info(f"{self.AIRLINE}: Making Zenrows calls for prices...")
        logger.info(f"{self.AIRLINE}: Region being used... {proxy_region} with url {url}")
        # with open("/home/dev/Downloads/dl_pricings.html", "r") as f:
        #     content = f.read()
        async with session.get("https://api.zenrows.com/v1/", params=params) as response:
            print(f">>>>>>>>>>>..get_flights_pricing: {await response.text()}")
            content = await response.text()
            soup = BeautifulSoup(content, "html.parser")

            cabin_classes = self.parse_cabin_classes(soup)
            search_result_grid = soup.find("idp-flight-grid").select('div[id*="flight-results-grid"]')
            for flight_row_element in search_result_grid:
                flight = self.parse_flight(flight_row_element, cabin_class, departure_date)
                prices = self.parse_flight_pricing(flight_row_element, cabin_classes)
                prices = {
                    airline_cabin_class: price
                    for airline_cabin_class, price in prices.items()
                    if airline_cabin_class in CabinClassMapping[cabin_class]
                }
                if not prices:
                    continue

                for airline_cabin_class, price in prices.items():
                    flight.airline_cabin_class = airline_cabin_class
                    flight.amount = price
                    flights.append(flight)
            return flights

    async def get_flights_points(
        self,
        session: ClientSession,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
    ) -> List[Flight]:
        flights = []
        eval_param = self.get_evaluate_param(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            shop_miles=True,
            adults=adults,
        )

        region = random.choice(REGION_URLS)
        proxy_region, url = next(iter(region.items()))

        params = {
            "url": url,
            "apikey": c.ZENROWS_API_KEY,
            "js_render": "true",
            "antibot": "true",
            "wait_for": "#booking.book-widget-container.container-padding-x",
            "premium_proxy": "true",
            "proxy_country": proxy_region,
            "json_response": "true",
            # "window_width": "1920",
            # "window_height": "1080",
            "js_instructions": eval_param,
        }
        logger.info(f"{self.AIRLINE}: Making Zenrows calls for points...")
        logger.info(f"{self.AIRLINE}: Region being used... {proxy_region} with url {url}")
        # with open("/home/dev/Downloads/dl_points.html", "r") as f:
        #     html_content = f.read()
        async with session.get("https://api.zenrows.com/v1/", params=params) as response:
            print(f">>>>>>>>>>>..get_flights_points: {await response.text()}")
            html_content = await response.text()
            soup = BeautifulSoup(html_content, "html.parser")

            cabin_classes = self.parse_cabin_classes(soup)
            search_result_grid = soup.find("idp-flight-grid").select('div[id*="flight-results-grid"]')
            for flight_row_element in search_result_grid:
                flight = self.parse_flight(flight_row_element, cabin_class, departure_date)
                points_data = self.parse_flight_points(flight_row_element, cabin_classes)
                points_data = {
                    airline_cabin_class: point_data
                    for airline_cabin_class, point_data in points_data.items()
                    if airline_cabin_class in CabinClassMapping[cabin_class]
                }
                if not points_data:
                    continue

                for airline_cabin_class, point_data in points_data.items():
                    points, cash_fee = point_data
                    flight.airline_cabin_class = airline_cabin_class
                    flight.cash_fee = cash_fee
                    flight.points = points
                    flights.append(flight)

            return flights


if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = DeltaAirlineZenrowCrawler()
        travel_departure_date = datetime.date.today() + datetime.timedelta(days=14)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=travel_departure_date.isoformat(),
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

    # run("PVG", "PNG", c.CabinClass.Economy)
    # run("JFK", "LAX", c.CabinClass.Economy)
    # run("JFK", "LAX", c.CabinClass.PremiumEconomy)
    run("JFK", "LAX", c.CabinClass.Economy, 1)
    # run("JFK", "LAX", c.CabinClass.First)
    #
    # segments = [
    #     DeltaFlightDetailRequestPayload(
    #         originAirportCode="JFK",
    #         destinationAirportCode="BOS",
    #         schedLocalDepartDate="2024-02-15T16:59:00",
    #         marketingAirlineCode="DL",
    #         operatingAirlineCode="DL",
    #         classOfServiceList=["H"],
    #         flightNumber="5695",
    #     )
    # ]
    # response = DeltaAirlineZenrowCrawler.get_flight_segments(segments)
    # with open("c.json", "w") as f:
    #     json.dump(response, f, indent=2)
