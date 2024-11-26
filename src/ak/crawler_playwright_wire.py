import datetime
import json
import logging
import time
from typing import Dict, Iterator, List, Optional

from isodate import duration_isoformat

from playwright.sync_api import Page
from src import constants as c
from src.ak.constants import (
    AirlineCabinClassCodeMapping,
    CabinClassCodeMapping
)
from src.exceptions import NoSearchResult
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.db import insert_target_headers

logger = logging.getLogger(__name__)

class AlaskaPlaywrightWireCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.Alaska
    REQUIRED_LOGIN = False
    BLOCK_RESOURCE = True
    TARGET = 'alaska'
    HOME_PAGE_URL = "https://www.alaskaair.com"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered
    intercepted_response = {}
    intercepted = False

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        self.origin = origin

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        self.destination = destination

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        self.departure_date = departure_date

    def _select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        self.adults = adults

    def handle_response(self, response):
        # self.intercepted_response = {}
        # self.intercepted = False
        
        if "/search/api/flightresults" in response.url and response.status == 200:
            # time.sleep(5)
            try:
                response_body = response.json()
                as_headers = response.all_headers()
                insert_target_headers(as_headers, self.TARGET)
                status_code = response.status
                logger.info(f"{self.AIRLINE.value}: Response from {response.url}: Status Code - {status_code}")

                if response_body:
                    self.intercepted_response = response_body
                    return

            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")
            finally:
                self.intercepted = True

    def intercept_request(self, route, request):

        if "/search/api/flightresults" in request.url:
            route.continue_()
            try:
                response = request.response()
                response_body = response.json()
                as_headers = request.all_headers()
                payload = request.post_data_json
                insert_target_headers(as_headers, self.TARGET, payload)
                status_code = response.status
                logger.info(f"{self.AIRLINE.value}: Response from {request.url}: Status Code - {status_code}")

                if response_body:
                    self.intercepted_response = response_body
                else:
                    raise CrawlerException("Looks like scraper got blocked !")                

            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")
            finally:
                self.intercepted = True
        else:
            return self.intercept_route(route)
        
    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.route("**", lambda route, request: self.intercept_request(route, request))
        
        link = f'https://www.alaskaair.com/search/results?A={self.adults}&C=0&L=0&O={self.origin}&D={self.destination}&OD={self.departure_date}&RT=false&ShoppingMethod=onlineaward'
        page.goto(link)
        # page.on("response", self.handle_response)

        try:
            selector = '.pane.isSelected.pane-priced'
            page.wait_for_selector(selector, timeout=20000)
            time.sleep(1)
            page.click(selector)
            # time.sleep(5)
        except Exception as e:
            raise NoSearchResult(airline=self.AIRLINE, reason="No available flights!")
    
        waited_time = max_time = 30
        while not self.intercepted_response and max_time > 0:
            loading_spinner_count = page.locator("table#MatrixTable_0").count()
            
            if self.intercepted and not self.intercepted_response and not loading_spinner_count:
                logger.info(f"{self.AIRLINE.value}: Search Failed!")
                break
            time.sleep(1)
            max_time -= 1

        if max_time == 0:
            logger.error(f"{self.AIRLINE.value}: waited for {waited_time}s but no results, might get blocked")
            raise NoSearchResult(airline=self.AIRLINE)

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["segments"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")

                connection_time = segment_element.get("stopoverDuration", 0)

                segment_origin = segment_element["departureStation"]
                segment_destination = segment_element["arrivalStation"]
                segment_departure_datetime = segment_element["departureTime"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment_element["arrivalTime"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                segment_aircraft = segment_element["aircraft"]
                segment_carrier = segment_element['displayCarrier']['carrierCode']
                segment_flight_number = str(segment_element['displayCarrier']['flightNumber'])
                segment_duration = segment_element["duration"]

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_datetime.date().isoformat(),
                        departure_time=segment_departure_datetime.time().isoformat()[:5],
                        departure_timezone=str(segment_departure_datetime.tzinfo),
                        arrival_date=segment_arrival_datetime.date().isoformat(),
                        arrival_time=segment_arrival_datetime.time().isoformat()[:5],
                        arrival_timezone=str(segment_arrival_datetime.tzinfo),
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=duration_isoformat(datetime.timedelta(minutes=segment_duration)),
                        layover_time=duration_isoformat(datetime.timedelta(minutes=connection_time))
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
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Classes points...")
        cabin_class_codes = CabinClassCodeMapping[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        for cabin_class_code, air_bound in flight_data["fares"].items():
            # try:
                if cabin_class_code not in cabin_class_codes:
                    continue

                fare_name = AirlineCabinClassCodeMapping[cabin_class_code]
                points = air_bound["milesPoints"]
                amount = round(air_bound["grandTotal"])
                currency = 'USD'
                points_by_fare_names[fare_name] = {
                    "points": points,
                    "cash_fee": CashFee(
                        amount=amount,
                        currency=currency,
                    ),
                }
            # except Exception as e:
            #     logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return points_by_fare_names

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        
        if not self.intercepted_response:
            raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

        if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
            raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

        flight_search_results = self.intercepted_response["slices"]
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
            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")
            for extract_cabin_class in all_cabins:
                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, extract_cabin_class)
                if not points_by_fare_names:
                    continue

                try:
                    segments = self.extract_flight_detail(flight_search_result)
                except Exception as e:
                    raise e
                duration = flight_search_result["duration"]
                for fare_name, points_and_cash in points_by_fare_names.items():
                    if not segments:
                        continue
                    flight = Flight(
                        airline=str(self.AIRLINE.value),
                        origin=segments[0].origin,
                        destination=segments[-1].destination,
                        cabin_class=str(extract_cabin_class.value),
                        airline_cabin_class=fare_name,
                        points=points_and_cash["points"],
                        cash_fee=points_and_cash["cash_fee"],
                        segments=segments,
                        duration=duration_isoformat(datetime.timedelta(minutes=duration)),
                    )
                    yield flight


if __name__ == "__main__":
    # import threading
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AlaskaPlaywrightWireCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=11, day=10)

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

    # run("PVG", "ICN", c.CabinClass.Economy)
    # run("JFK", "LHR", c.CabinClass.Economy)
    # run("LAX", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Economy)
    run("JFK", "LHR", c.CabinClass.PremiumEconomy)

