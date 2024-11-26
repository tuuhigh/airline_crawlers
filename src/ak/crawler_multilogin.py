import datetime
import logging
import random
import hashlib
import time
import socket
import json
import re
from typing import Iterator, List, Optional, Tuple, Dict

import requests
from src import constants as c
from src.base import MultiLoginAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException
from src.schema import CashFee, Flight, FlightSegment
from src.ak.constants import (
    CabinClassCodeMapping,
    AirlineCabinClassCodeMapping,
)
from src.exceptions import NoSearchResult
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    parse_time,
    get_random_port
)
from isodate import duration_isoformat
from src import db

DISABLE_LOGGERS = [
    "seleniumwire.server",
    "hpack.hpack",
    "hpack.table",
    "seleniumwire.handler"
]
for thirdparty_logger in DISABLE_LOGGERS:
    logging.getLogger(thirdparty_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


from selenium import webdriver
from seleniumwire.utils import decode
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from seleniumwire import webdriver as webdriversw  # Import from seleniumwire

STARTER_URL = "https://app.multiloginapp.com/WhatIsMyIP"
MLX_BASE = "https://api.multilogin.com"
MLX_LAUNCHER = "https://launcher.mlx.yt:45001/api/v1"
LOCALHOST = "http://127.0.0.1"
HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

USERNAME = "anujpatel@odynn.com"
PASSWORD = "ILoveMultiLogins1234@#"


class AlaskaMultiloginCrawler(MultiLoginAirlineCrawler):
    AIRLINE = Airline.Alaska

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        driver = False
        try:
            
            url = f'https://www.alaskaair.com/search/results?A={adults}&C=0&L=0&O={origin}&D={destination}&OD={departure_date}&RT=false&ShoppingMethod=onlineaward'

            driver = self.setup_driver(use_selenium_wire=True)
            # driver.get(STARTER_URL)
            time.sleep(1)
            driver.get(url)


            logger.info(f"{self.AIRLINE.value}: Making Multilogin calls...")
            for request in driver.requests:
                if request.response:
                    print(
                        request.url,
                        request.response.status_code,
                    )
            request = driver.wait_for_request('search/api/flightresults', timeout=60)

            response = request.response
            response_body = decode(response.body, response.headers.get('Content-Encoding', 'identity'))
            self.intercepted_response = json.loads(response_body)

            logger.info(f"{self.AIRLINE.value}: Got Multilogin response: count: {len(self.intercepted_response)}")

            if not self.intercepted_response:
                raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

            if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
            
            flight_search_results = self.intercepted_response.get("slices", [])
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
            
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

        except (LiveCheckerException, Exception) as e:
            raise e

        finally:
            logger.info(f"{self.AIRLINE.value}: closing driver")
            if driver:
                driver.quit()

if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AlaskaMultiloginCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=23)

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

    # run("CDG", "NYC", c.CabinClass.Economy)
    run("JFK", "CDG", c.CabinClass.Economy)