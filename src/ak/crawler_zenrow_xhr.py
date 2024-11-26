import datetime
import logging
import random
import json
from typing import Dict, Iterator, List, Optional, Tuple
import re

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

from src.ak.constants import (
    AirlineCabinClassCodeMapping,
    CabinClassCodeMapping
)
from isodate import duration_isoformat


logger = logging.getLogger(__name__)

def quote_keys(match):
    return f'"{match.group(1)}":'

def fix_json_string(data):
    # Split the string into parts by commas and brackets
    parts = data.replace('{', '{ ').replace('}', ' }').replace('[', '[ ').replace(']', ' ]').split()
    
    # Initialize an empty list for the fixed parts
    fixed_parts = []
    
    for part in parts:
        # Add quotes around keys
        if ':' in part:
            key_value = part.split(':', 1)
            key = key_value[0].strip()
            value = key_value[1].strip()
            fixed_parts.append(f'"{key}": {value}')
        else:
            fixed_parts.append(part)
    
    # Join the fixed parts back into a string
    return ' '.join(fixed_parts)

class AlaskaZenrowXHRCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.Alaska

    @staticmethod
    def months_until_target(departure_date: datetime.date):
        current_date = datetime.date.today()
        months_until = (departure_date.year - current_date.year) * 12 + (departure_date.month - current_date.month)
        return months_until

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
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
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
            url = f'https://www.alaskaair.com/search/results?A={adults}&C=0&L=0&O={origin}&D={destination}&OD={departure_date}&RT=false&ShoppingMethod=onlineaward'
            params = {
                'url': url,
                "apikey": c.ZENROWS_API_KEY,
                'js_render': 'true',
                'antibot': 'true',
                'wait_for': 'table#MatrixTable_0',
                'premium_proxy': 'true',
                'json_response': 'true',
                # "proxy_country": random.choice(["us", "ca"]),
            }

            logger.info(f"{self.AIRLINE.value}: Making Zenrows calls...")
            response = requests.get('https://api.zenrows.com/v1/', params=params)
            if response.status_code != 200:
                raise ZenRowFailed(airline=self.AIRLINE, reason=response.text)

            soup = BeautifulSoup(response.text, 'html.parser')
            json_data = {}
            script_tag = soup.find('script', string=re.compile(r'__sveltekit_\w+\.resolve'))
            if script_tag:
                script_content = script_tag.string
                json_match = re.search(r'\{.*\}', script_content, re.DOTALL)
                if json_match:
                    json_data = json_match.group(0).strip()
                    json_data = json_data.replace('\\"', '"')
                    json_data = re.sub(r'([,{])([A-Z\da-z_$]+):', r'\1"\2":', json_data)
                    json_data = re.sub(r':void 0', r':"void 0"', json_data)
                    json_data = re.sub(r':null', r':"None"', json_data)
                    json_data = json.loads(json_data)
                                
            all_cabins = []
            if cabin_class == c.CabinClass.All:
                all_cabins = [
                    c.CabinClass.Economy, 
                    c.CabinClass.PremiumEconomy, 
                    c.CabinClass.Business,
                    c.CabinClass.First
                ]
            else:
                all_cabins = [cabin_class]
                
            flights_data = json_data
            if flights_data:
                flight_search_results = flights_data["data"]["slices"]
                logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
                for index, flight_search_result in enumerate(flight_search_results):
                    logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")
                    
                    for cabin_klass in all_cabins:
                        points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_klass)
                        if not points_by_fare_names:
                            continue

                        try:
                            segments = self.extract_flight_detail(flight_search_result)
                        except Exception as e:
                            logger.info(f"{self.AIRLINE.value}: extract_flight_detail error: {e}...")
                            continue
                            # raise e
                        duration = flight_search_result["duration"]

                        for fare_name, points_and_cash in points_by_fare_names.items():
                            if not segments:
                                continue
                            flight = Flight(
                                airline=str(self.AIRLINE.value),
                                origin=segments[0].origin,
                                destination=segments[-1].destination,
                                cabin_class=str(cabin_klass.value),
                                airline_cabin_class=fare_name,
                                points=points_and_cash["points"],
                                cash_fee=points_and_cash["cash_fee"],
                                segments=segments,
                                duration=duration_isoformat(datetime.timedelta(minutes=duration)),
                            )
                            yield flight
            # if not xhrs:
            #     raise LiveCheckerException(f"{self.AIRLINE.value}: Zenrows returned no datas from api endpoints")
        except (LiveCheckerException, Exception) as e:
            raise e


if __name__ == "__main__":
    
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = AlaskaZenrowXHRCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=40)
        departure_date = datetime.date(year=2024, month=10, day=16)
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

    run("JFK", "LAX", CabinClass.Economy, 1)
    # run("DFW", "JFK", CabinClass.Business, 1)
    # run("SFO", "HNL", CabinClass.Economy, 1)
