import datetime
import logging
import random
import json
import re
from typing import Dict, Iterator, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from src import constants as c
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, ZenRowFailed
from src.schema import CashFee, Flight, FlightSegment

from src.b6.constants import (
    CabinClassCodeMapping,
    CabinClassCodeMappingForHybrid,
)
from isodate import duration_isoformat

logger = logging.getLogger(__name__)


class JetBlueZenrowXHRCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.JetBlue

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_data in enumerate(flight_data["segments"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                connection_time = segment_data.get("layover", None)

                segment_origin = segment_data["from"]
                segment_destination = segment_data["to"]
                segment_departure = segment_data["depart"].replace("Z","+00:00")
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure)
                segment_arrival = segment_data["arrive"].replace("Z","+00:00")
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival)
                timezone_pattern = r'[\+\-]\d{2}:\d{2}$'
                departure_timezone_match = re.search(timezone_pattern, segment_departure)
                if departure_timezone_match:
                    departure_timezone = departure_timezone_match.group()
                else:
                    departure_timezone = ""
                arrival_timezone_match = re.search(timezone_pattern, segment_arrival)
                if arrival_timezone_match:
                    arrival_timezone = arrival_timezone_match.group()
                else:
                    arrival_timezone = ""
                segment_aircraft = segment_data["aircraft"]
                segment_carrier = segment_data["operatingAirlineCode"]
                segment_flight_number = segment_data["flightno"]
                segment_duration = segment_data["duration"]

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_datetime.date().isoformat(),
                        departure_time=segment_departure_datetime.time().isoformat()[:5],
                        departure_timezone=departure_timezone,
                        arrival_date=segment_arrival_datetime.date().isoformat(),
                        arrival_time=segment_arrival_datetime.time().isoformat()[:5],
                        arrival_timezone=arrival_timezone,
                        aircraft=segment_aircraft,
                        flight_number=segment_flight_number,
                        carrier=segment_carrier,
                        duration=segment_duration,
                        layover_time=connection_time
                    )
                )
            
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def extract_sub_classes_points(
        self, flight_data, currency, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        cabin_class_codes = CabinClassCodeMappingForHybrid[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        for air_bound in flight_data["bundles"]:
            if air_bound.get("code","") in cabin_class_codes:
                try:
                    fare_name = CabinClassCodeMapping[cabin_class]
                    fare_brand_name = air_bound["code"]
                    if fare_brand_name:
                        fare_brand_name = fare_brand_name.replace('_', ' ').replace('-', ' ')
                        fare_name = f'{fare_name} {fare_brand_name}'

                    points = -1 if air_bound.get("status","") == 'SOLD_OUT' else air_bound["points"]
                    amount = 0 if air_bound.get("status","") == 'SOLD_OUT' else air_bound["fareTax"]
                    points_by_fare_names[fare_name] = {
                        "points": int(points),
                        "fare_brand_name": fare_brand_name,
                        "cash_fee": CashFee(
                            amount=float(amount),
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
            url = f'https://www.jetblue.com/booking/flights?from={origin}&to={destination}&depart={departure_date.isoformat()}&isMultiCity=false&noOfRoute=1&lang=en&adults={adults}&children=0&infants=0&sharedMarket=false&roundTripFaresFlag=false&usePoints=true'
            params = {
                "url": url,
                "apikey": c.ZENROWS_API_KEY,
                "js_render": "true",
                "antibot": "true",
                "wait_for": "jb-flight-details",
                "premium_proxy": "true",
                "proxy_country": random.choice(["us"]),
                "json_response": "true",
            }
            logger.info(f"{self.AIRLINE.value}: Making Zenrows calls...")
            response = requests.get("https://api.zenrows.com/v1/", params=params)
            if response.status_code != 200:
                raise ZenRowFailed(airline=self.AIRLINE, reason=response.text)

            json_data = response.json()
            xhrs = json_data.get("xhr", [])
            for xhr in xhrs:
                if 'jbrest.jetblue.com/lfs-rwb/outboundLFS' in xhr.get('url', ''):
                    flights_data = xhr.get("body", {})
                    if flights_data:
                        flights_data = isinstance(flights_data, str) and json.loads(flights_data) or flights_data
                        flight_search_results = flights_data["itinerary"]
                        currency = flights_data["currency"]
                        crawler_cabin_classes = []
                        
                        if cabin_class == c.CabinClass.All:
                            crawler_cabin_classes = [
                                c.CabinClass.Economy,
                                # c.CabinClass.PremiumEconomy,
                                c.CabinClass.Business,
                                # c.CabinClass.First
                            ]
                        else:
                            # since B6 doesn't have cabin_class code for for PremiumEconomy and First, so we will
                            # use PremiumEconomy = Economy and First = Business
                            if cabin_class == c.CabinClass.PremiumEconomy:
                                cabin_class = c.CabinClass.Economy
                            if cabin_class == c.CabinClass.First:
                                cabin_class = c.CabinClass.Business
                                
                            crawler_cabin_classes = [cabin_class]
                                
                        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
                        for index, flight_search_result in enumerate(flight_search_results):
                            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")

                            for cabin_item in crawler_cabin_classes:
                                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, currency, cabin_item)
                                print(points_by_fare_names)
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
                                        cabin_class=str(cabin_item.value),
                                        fare_brand_name = points_and_cash["fare_brand_name"],
                                        airline_cabin_class=fare_name,
                                        points=points_and_cash["points"],
                                        cash_fee=points_and_cash["cash_fee"],
                                        segments=segments,
                                        duration=duration,
                                    )
                                    yield flight

            if not xhrs:
                raise LiveCheckerException(f"{self.AIRLINE.value}: Zenrows returned no datas from api endpoints")
        except (LiveCheckerException, Exception) as e:
            print(e)
            raise e


if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = JetBlueZenrowXHRCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=40)
        departure_date = datetime.date(year=2024, month=11, day=26)
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
    # run("IAD", "AMD", c.CabinClass.All, 1)
    # run("JFK", "LHR", CabinClass.Economy, 1)
    run("JFK", "LAX", CabinClass.All, 1)
    # run("DFW", "JFK", CabinClass.Economy)
