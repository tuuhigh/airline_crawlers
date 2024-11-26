import datetime
import json
import logging
import time
from typing import Dict, Iterator, List, Optional

from isodate import duration_isoformat

from playwright._impl._errors import Error
from playwright.sync_api import Page
from src import constants as c
from src.ac.constants import (
    AirlineCabinClassCodeMapping,
    CabinClassCodeMappingForHybrid,
)
from src.exceptions import NoSearchResult, AirlineCrawlerException
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment

logger = logging.getLogger(__name__)


class AirCanadaPlaywrightWireCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.AirCanada
    REQUIRED_LOGIN = False
    BLOCK_RESOURCE = True
    HOME_PAGE_URL = "https://www.aircanada.com"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-us",
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

    def intercept_request(self, route, request):

        if "/v2/search/air-bounds" in request.url and request.method == "POST":
            route.continue_()
            try:
                response = request.response()
                response_body = response.json()
                status_code = response.status
                logger.info(f"{self.AIRLINE.value}: Response from {request.url}: Status Code - {status_code}")

                if response_body:
                    self.intercepted_response = response_body
                    return

            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")
            finally:
                self.intercepted = True
        else:
            return self.intercept_route(route)

    def _browse_reward_page(self, *args, **kwargs):
        """
        Go direct reward page without need to submit
        """
        self.intercepted = False
        self.intercepted_response = None
        page: Page = kwargs.get("page")
        link = (
            f"https://www.aircanada.com/aeroplan/redeem/availability/outbound?"
            f"org0={self.origin}&dest0={self.destination}&departureDate0={self.departure_date.isoformat()}"
            f"&lang=en-CA&tripType=O&ADT={self.adults}&YTH=0&CHD=0&INF=0&INS=0&marketCode=DOM"
        )
        page.route("**", lambda route, request: self.intercept_request(route, request))

        logger.info(f"{self.AIRLINE.value}: Search Link - {link}")
        page.goto(link, wait_until="domcontentloaded")
        page.wait_for_url("**/aeroplan/redeem/availability/outbound")

    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")

        self._browse_reward_page(*args, **kwargs)
        time.sleep(5)
        # maxium time to wait for data is 60s
        waited_time = max_time = 200
        while not self.intercepted_response and max_time > 0:
            try: 
                if "Access Denied" in page.content():
                    raise AirlineCrawlerException(self.AIRLINE, "Access Denied")
            except Error as e:
                logger.info(
                f"{self.AIRLINE.value}: access denied error: {e}"
            )
            
            loading_spinner_count = page.locator("//kilo-loading-spinner-pres").count()
            logger.info(
                f"{self.AIRLINE.value}: spinner count: {loading_spinner_count} - "
                f"waiting for loading flights data, {max_time}s remaining"
            )
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
        flight_dictionaries: Dict,
        aircrafts: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["boundDetails"]["segments"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                flight_id = segment_element["flightId"]
                connection_time = segment_element.get("connectionTime", 0)
                flight_dictionary = flight_dictionaries.get(flight_id, None)

                if flight_dictionary:
                    segment_origin = flight_dictionary["departure"]["locationCode"]
                    segment_destination = flight_dictionary["arrival"]["locationCode"]
                    segment_departure_datetime = flight_dictionary["departure"]["dateTime"].replace("Z","+00:00")
                    segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                    segment_arrival_datetime = flight_dictionary["arrival"]["dateTime"].replace("Z","+00:00")
                    segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                    aircraft_id = flight_dictionary["aircraftCode"]
                    segment_aircraft = aircrafts.get(aircraft_id, None)
                    segment_carrier = flight_dictionary["marketingAirlineCode"]
                    segment_flight_number = flight_dictionary["marketingFlightNumber"]
                    if not segment_carrier:
                        segment_carrier = flight_dictionary.get("operatingAirlineName", None)
                    segment_duration = flight_dictionary["duration"]

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

        for air_bound in flight_data["airBounds"]:
            if c.CabinClass.Economy == cabin_class:
                continue_flag = all(
                    [
                        cabin_class_code == air_bound_availability["cabin"]
                        for air_bound_availability in air_bound["availabilityDetails"]
                    ]
                )
            else:
                continue_flag = any(
                    [
                        cabin_class_code == air_bound_availability["cabin"]
                        for air_bound_availability in air_bound["availabilityDetails"]
                    ]
                )

            if continue_flag:
                try:
                    fare_name = AirlineCabinClassCodeMapping[air_bound["fareFamilyCode"]]

                    points = air_bound["airOffer"]["prices"]["milesConversion"]["convertedMiles"]["base"]
                    amount = air_bound["airOffer"]["prices"]["totalPrices"][0]["total"]
                    if amount:
                        amount = round(amount / 100)
                    currency = air_bound["airOffer"]["prices"]["totalPrices"][0]["currencyCode"]
                    points_by_fare_names[fare_name] = {
                        "points": points,
                        "cash_fee": CashFee(
                            amount=amount,
                            currency=currency,
                        ),
                    }
                except Exception as e:
                    logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")

        return points_by_fare_names

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        if not self.intercepted_response:
            raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

        if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
            raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

        flight_search_results = self.intercepted_response["data"]["airBoundGroups"]
        flight_dictionaries = self.intercepted_response["dictionaries"]["flight"]
        aircrafts = self.intercepted_response["dictionaries"]["aircraft"]
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
                    segments = self.extract_flight_detail(flight_search_result, flight_dictionaries, aircrafts)
                except Exception as e:
                    raise e
                duration = flight_search_result["boundDetails"]["duration"]
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
                        duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                    )
                    yield flight


if __name__ == "__main__":
    # import threading
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AirCanadaPlaywrightWireCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=24)

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
    run("YVR", "YYZ", c.CabinClass.All)
    # asyncio.run(run("YVR", "YYZ", c.CabinClass.Economy))
    # run("KUL", "YYZ", c.CabinClass.First)
    #
    # t1 = threading.Thread(target=run, args=("LAX", "JFK", c.CabinClass.PremiumEconomy))
    # t2 = threading.Thread(target=run, args=("YVR", "YYZ", c.CabinClass.PremiumEconomy))
    # t1.start()
    # t2.start()
    # t1.join()
    # t2.join()
