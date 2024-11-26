import datetime
import logging
import random
import json
from typing import Dict, Iterator, List, Optional, Tuple

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

from src.vs.constants import (
    AirlineCabinClassCodeMapping,
    CabinClassCodeMappingForHybrid,
)
from isodate import duration_isoformat

from src.vs.constants import CabinClassCodeMapping

logger = logging.getLogger(__name__)


class VirginAtlanticZenrowXHRCrawler(RequestsBasedAirlineCrawler):
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
        departure_date_str = departure_date.strftime("%m/%d/%Y").replace("/", "%2F")
        # # {"evaluate": "const containerDiv = document.querySelector('.search-result-container'); var firstChild = containerDiv.firstElementChild; var firstchild2 = firstChild.firstElementChild; var li = firstchild2.firstElementChild; var abtn = li.firstElementChild; abtn.click();"},
        # evaluate_param = """[
        #     {"evaluate": "document.querySelector('#privacy-btn-reject-all').click();"},
        #     {"wait_for": "#fromAirportName"},
        #     {"evaluate": "const originButton = document.getElementById('fromAirportName'); originButton.click();"},
        #     {"evaluate": "document.getElementById('search_input').value = '';"},
        #     {"evaluate": "const inputElement = document.querySelector('#search_input'); inputElement.value = '%s'; inputElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));"},
        #     {"wait_for": ".airportLookup-list"},
        #     {"evaluate": "const containerDiv = document.querySelector('.search-result-container'); const listItems = containerDiv.querySelectorAll('li'); listItems.forEach(item => { if (item.querySelector('span').innerText.includes('%s')) { item.querySelector('a').click(); } });"},
        #     {"evaluate": "const destinationButton = document.getElementById('toAirportName'); destinationButton.click();"},
        #     {"evaluate": "document.getElementById('search_input').value = '';"},
        #     {"evaluate": "const inputElement = document.querySelector('#search_input'); inputElement.value = '%s'; inputElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));"},
        #     {"wait_for": ".airportLookup-list"},
        #     {"evaluate": "const containerDiv = document.querySelector('.search-result-container'); const listItems = containerDiv.querySelectorAll('li'); listItems.forEach(item => { if (item.querySelector('span').innerText.includes('%s')) { item.querySelector('a').click(); } });"},
        #     {"evaluate": "const tripTypeButton = document.querySelector('.select-ui-wrapper.ng-tns-c1-2'); tripTypeButton.click();"},
        #     {"evaluate": "document.getElementById('ui-list-selectTripType1').click();"},
        #     {"click": "#input_departureDate_1"},
        #     {"wait_for": ".dl-state-default"},
        # """
        # months_until = VirginAtlanticZenrowXHRCrawler.months_until_target(departure_date) - 1
        # if months_until > 0:
        #     for _ in range(months_until):
        #         evaluate_param += """
        #             {"evaluate": "document.querySelector('.dl-datepicker-1').click()"},
        #             {"wait": 200},
        #         """

        # evaluate_param += """
        #     {"click": "[data-date*='%s']"},
        # """

        # if adults > 1:
        #     evaluate_param += """
        #             {"click": "#passenger"},
        #             {"wait_for": ".pax-optionList"},
        #         """
        #     for _ in range(adults - 1):
        #         evaluate_param += """
        #             {"evaluate": "document.querySelector('.pax-optionList.pax-ADT .add-pax a').click();"},
        #             {"wait": 200},
        #             """

        # evaluate_param += """
        #     {"evaluate": "const searchButton = document.getElementById('btn-book-submit'); searchButton.click();"},
        #     {"wait": 13000},
        #     {"wait_for": ".btn.btn-moneymiles.ng-star-inserted"},
        #     {"evaluate": "const parentDiv = document.querySelectorAll('.btn.btn-moneymiles.ng-star-inserted');parentDiv[1].click();"},
        #     {"wait": 20000}
        # ]"""
    
        evaluate_param = """[
            {"wait": 5000},
            {"evaluate": "navigation.navigate('%s')"},
            {"wait": 10000},
            {"wait_for": "section[@data-testid='flights-list']"},
            {"wait": 10000}
        ]"""
        # 06%2F08%2F2024
        link = f"https://book.virginatlantic.com/flights/search/slice?origin={origin}&destination={destination}&departing={departure_date_str}&passengers=a1t0c0i0"
        # link = f"https://www.virginatlantic.com/flight-search/search?action=findFlights&searchByCabin=true&deltaOnlySearch=false&deltaOnly=off&go=Find%20Flights&tripType=ONE_WAY&passengerInfo=ADT:1%7CGBE:0%7CCNN:0%7CINF:0&pricedeparture_date_strSchedule=price&awardTravel=false&originCity={origin}&destinationCity={destination}&departureDate={departure_date_str}&returnDate=&forceMiles=true"
        return  evaluate_param % (link)

        # return evaluate_param % (origin, origin, origin, destination, destination, destination, departure_date_str)
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

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["trip"][0]["flightSegment"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")

                connection_time = 0
                layover = segment_element.get("layover", {})
                if layover:
                    layover_duration = layover.get('duration', {})
                    layover_hour = layover_duration.get('hour', 0)
                    layover_min = layover_duration.get('minute', 0)
                    connection_time = layover_hour * 3600 + layover_min * 60

                segment_origin = segment_element["originAirportCode"]
                segment_destination = segment_element["destAirportCode"]
                segment_departure_datetime = segment_element["schedDepartLocalTs"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment_element["schedArrivalLocalTs"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                segment_aircraft = segment_element["flightLeg"][0]["aircraft"]["fleetName"]
                segment_carrier = segment_element.get('marketingCarrier', {}).get('code', '')
                if not segment_carrier:
                    segment_carrier = segment_element.get('operatingCarrier', {}).get('code', '')
                segment_flight_number = segment_element.get('operatingFlightNum', '')
                if not segment_flight_number:
                    segment_flight_number = segment_element.get('operatingFlightNum', '')

                # duration_day = segment_element["totalAirTime"]["day"]
                duration_hour = segment_element["totalAirTime"]["hour"]
                duration_min = segment_element["totalAirTime"]["minute"]
                segment_duration = 3600 * duration_hour + 60 * duration_min

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_datetime.date().isoformat(),
                        departure_time=segment_departure_datetime.time().isoformat()[:5],
                        departure_timezone="",
                        arrival_date=segment_arrival_datetime.date().isoformat(),
                        arrival_time=segment_arrival_datetime.time().isoformat()[:5],
                        arrival_timezone="",
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=duration_isoformat(datetime.timedelta(seconds=segment_duration)),
                        layover_time=duration_isoformat(datetime.timedelta(seconds=connection_time))
                        if connection_time
                        else None,
                    )
                )
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def extract_sub_classes_points(
        self, flight_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        cabin_class_code = CabinClassCodeMappingForHybrid[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        for air_bound in flight_data["fare"]:
            try:
                if cabin_class_code != str(air_bound["fareId"]):
                    continue

                fare_name = AirlineCabinClassCodeMapping[str(air_bound["fareId"])]
                if air_bound["soldOut"]:
                    points_by_fare_names[fare_name] = {
                        "points": -1,
                        "cash_fee": CashFee(
                            amount=0,
                            currency="",
                        ),
                    }
                else:
                    points = air_bound["totalPrice"]["miles"]["miles"]
                    amount = air_bound["totalPrice"]["currency"]["formattedAmount"]
                    currency = air_bound["totalPrice"]["currency"]["code"]
                    points_by_fare_names[fare_name] = {
                        "points": points,
                        "cash_fee": CashFee(
                            amount=float(amount.replace(",", "")),
                            currency=currency,
                        ),
                    }
            except Exception as e:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return points_by_fare_names

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
            url = "https://www.virginatlantic.com/ca/en"
            evaluate_param = self.get_evaluate_param(origin, destination, departure_date, adults)
            params = {
                "url": url,
                "apikey": c.ZENROWS_API_KEY,
                "js_render": "true",
                "antibot": "true",
                "wait_for": "section[@data-testid='flights-list']",
                "premium_proxy": "true",
                "proxy_country": random.choice(["ca"]),
                "json_response": "true",
                "js_instructions": evaluate_param,
            }
            logger.info(f"{self.AIRLINE.value}: Making Zenrows calls...")
            response = requests.get("https://api.zenrows.com/v1/", params=params)
            # print("response =====>", response)
            # print("response.headers =====>", response.headers)
            # print("response tedt =====>", response.text)
            if response.status_code != 200:
                raise ZenRowFailed(airline=self.AIRLINE, reason=response.text)

            json_data = response.json()
            # print(f">>>>>>>> json_data: {json_data}")
            html_content = json_data.get("html", "")
            xhrs = json_data.get("xhr", [])
            flights_data = None
            for xhr in xhrs:
                # print("xhrs ===========>", xhr.get('url', ''))
                if '/shop/ow/search' in xhr.get('url', ''):
                    flights_data = xhr.get("body", {})
                    
                    if flights_data:
                        flights_data = isinstance(flights_data, str) and json.loads(flights_data) or flights_data
                        flight_search_results = flights_data.get("itinerary", [])
                        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
                        all_cabins = []
                        
                        if cabin_class == c.CabinClass.All:
                            all_cabins = [
                                c.CabinClass.Economy, 
                                c.CabinClass.PremiumEconomy, 
                                c.CabinClass.Business
                            ]
                        else:
                            all_cabins = [cabin_class]

                        for index, flight_search_result in enumerate(flight_search_results):
                            is_miles_flight = False
                            for air_bound in flight_search_result["fare"]:
                                try:
                                    _ = air_bound["totalPrice"]["miles"]["miles"]
                                    is_miles_flight = True
                                    break
                                except KeyError:
                                    is_miles_flight = False

                            if not is_miles_flight:
                                continue
                            # if not flight_search_result["fare"][0]["totalPrice"]["miles"]["miles"]:
                            #     return
                            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")
                            
                            for cabin_item in all_cabins:
                                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_item)
                                if not points_by_fare_names:
                                    continue

                                try:
                                    segments = self.extract_flight_detail(flight_search_result)
                                except Exception as e:
                                    logger.info(f"{self.AIRLINE.value}: extract_flight_detail error: {e}...")
                                    continue

                                duration_hour = flight_search_result["trip"][0]["totalTripTime"]["hour"]
                                duration_min = flight_search_result["trip"][0]["totalTripTime"]["minute"]
                                duration = 3600 * duration_hour + 60 * duration_min  # Duration in seconds

                                for fare_name, points_and_cash in points_by_fare_names.items():
                                    if not segments:
                                        continue
                                    flight = Flight(
                                        airline=str(self.AIRLINE.value),
                                        origin=segments[0].origin,
                                        destination=segments[-1].destination,
                                        cabin_class=str(cabin_item.value),
                                        airline_cabin_class=fare_name,
                                        points=points_and_cash["points"],
                                        cash_fee=points_and_cash["cash_fee"],
                                        segments=segments,
                                        duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                                    )
                                    yield flight
            # print("flights_data =========>", flights_data)
            if not flights_data:
                raise ZenRowFailed(airline=self.AIRLINE, reason="Mostly like the zenrow was blocked.")
                
            if not xhrs:
                raise LiveCheckerException(f"{self.AIRLINE.value}: Zenrows returned no datas from api endpoints")
        except (LiveCheckerException, Exception) as e:
            raise e


if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = VirginAtlanticZenrowXHRCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=40)
        departure_date = datetime.date(year=2024, month=12, day=21)
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

    # run("IAD", "AMS", c.CabinClass.Economy, 1)
    run("JFK", "LHR", c.CabinClass.All, 1)
    # run("JFK", "LHR", CabinClass.Economy, 1)
    # run("DFW", "JFK", CabinClass.Economy)
