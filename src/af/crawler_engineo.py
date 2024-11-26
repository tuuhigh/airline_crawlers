import os
import datetime
from collections import namedtuple
from typing import Iterator, List
import logging
import json
import uuid
import requests
from isodate import duration_isoformat

from src.af.constants import (
    CabinClassCodeMapping,
)
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, NoSearchResult
from src.schema import CashFee, Flight, FlightSegment
from src.constants import BASE_DIR
from src.constants import AF_TEST_MODE
from src.constants import ENGINEO_ENDPOINT

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(f"airlines_crawlers.{__name__}")

FlightTime = namedtuple("FlightTime", ["date", "time", "timezone"])


def parse_datetime(time_format_string: str) -> FlightTime:
    parsed_datetime = datetime.datetime.strptime(time_format_string, "%Y-%m-%dT%H:%M:%S")
    return FlightTime(
        date=parsed_datetime.date().isoformat(),
        time=parsed_datetime.time().strftime("%H:%M"),
        timezone=f"{parsed_datetime.tzinfo}",
    )


class AFEngineoCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.AirFrance
    
    def generateUUID(self):
        return str(uuid.uuid4())

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: CabinClass = CabinClass.Economy,
        adults: int = 2,
        **kwargs
    ) -> Iterator[Flight]:
        api_requestId = kwargs.get("request_id")
        requestId = api_requestId or self.generateUUID()
        reportId = self.generateUUID()
        return_date = departure_date + datetime.timedelta(days=1)
        # print("=================requestId===============", requestId)
        # print("=================reportId===============", reportId)
        params = {
            "requestId": requestId,
            "reportId": requestId,
            # "requestId": "71c3342d-dc27-4b28-b7be-f7f86a4ebcc7",
            # "reportId": "7afed3d3-03cc-467a-80a0-033dc497963d",
            "customerId": 1,
            "siteId": 1,
            "siteName": "AirFrance",
            "retryCount": 5,
            "parameters": {
                "currency": "USD",
                "sourceIata": origin,   
                "destinationIata": destination,   
                "departureDate": departure_date.isoformat(),
                "returnDate": return_date.isoformat(),
                "pos": "US",
                "numOfAdults": adults,
                "numOfStops": 0,
                "isRoundtrip": False
            }
        }

        data = {}
        try:
            
            if AF_TEST_MODE is "True":
                with open(f'{BASE_DIR}/af_temp_data', 'r') as ff:
                    result = json.load(ff)

                data = result
            else:
                headers = {
                    "Content-Type": "application/json"
                }
                endpoint = f"{ENGINEO_ENDPOINT}/v1/sendRequest"
                logger.info(f"{self.AIRLINE.value} calling {endpoint} with params: {params}")
                response = requests.post(
                    endpoint,
                    json=params,
                    verify=False,
                    headers=headers
                )
                logger.info("================================== response ==============================")
                logger.info(response.status_code)
                if response.status_code != 200:
                    raise LiveCheckerException(
                        airline=Airline.AirFrance,
                        origin=origin,
                        destination=destination,
                        date=departure_date.isoformat(),
                        data=response.text,
                    )
                    
                data = response.json()

            file_name = 'data2.json'

            # Open the file in write mode and dump the data
            with open(file_name, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            
            all_cabins = []
            if cabin_class == CabinClass.All:
                all_cabins = [
                    CabinClass.Economy,
                    CabinClass.Business,
                    CabinClass.PremiumEconomy,
                    CabinClass.First,
                ]
            else:
                all_cabins = [cabin_class]

            offerItineraries = []

            try:
                offerItineraries = data["jsonResponse"]["data"]["availableOffers"]["offerItineraries"]
            except Exception as e:
                logger.error(f"{self.AIRLINE.value} - requestId: {requestId}: {origin}-{destination}-{departure_date.isoformat()} data: {data} - exception: {e}")
            
            if not offerItineraries:
                logger.error(f"{self.AIRLINE.value} - requestId: {requestId}: {origin}-{destination}-{departure_date.isoformat()}: NO FLIGHTS FOUND!")
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
            
            for cabin_item in all_cabins:
                for offerItinerary in offerItineraries:
                    segments: List[FlightSegment] = []
                    for segment in offerItinerary.get("activeConnection", {}).get("segments", []):
                        departure_datetime = segment.get("departureDateTime")
                        segment_departure_datetime = parse_datetime(departure_datetime) if departure_datetime else None

                        arrival_datetime = segment.get("arrivalDateTime")
                        segment_arrival_datetime = parse_datetime(arrival_datetime) if arrival_datetime else None
                        segment_aircraft = segment.get("equipmentName")
                        
                        layover_time = segment["transferDuration"]
                        if layover_time:
                            layover_time = duration_isoformat(datetime.timedelta(minutes=layover_time))
                        else:
                            layover_time = None

                        segments.append(
                            FlightSegment(
                                origin=segment.get("origin", {}).get("code", ""),
                                destination=segment.get("destination", {}).get("code", ""),
                                departure_date=segment_departure_datetime.date,
                                departure_time=segment_departure_datetime.time,
                                departure_timezone=segment_departure_datetime.timezone,
                                arrival_date=segment_arrival_datetime.date,
                                arrival_time=segment_arrival_datetime.time,
                                arrival_timezone=segment_arrival_datetime.timezone,
                                aircraft=segment_aircraft,
                                flight_number=segment.get("marketingFlight", {}).get("number", ""),
                                carrier=segment.get("marketingFlight", {}).get("carrier", "").get("code", ""),
                                duration=duration_isoformat(
                                    datetime.timedelta(minutes=segment["duration"])
                                ),
                                layover_time=layover_time,
                            )
                        )
                        
                    for cabin_price in offerItinerary.get("upsellCabinProducts", []):
                        product_type = cabin_price["connections"][0]["cabinClass"].lower()
                        
                        if product_type == 'premium':
                            product_type = 'premium_economy'
                        
                        if product_type == cabin_item.value.lower():
                            # print("product_type ===============>", product_type)
                            # print("cabin_item.value.lower() ===============>", cabin_item.value.lower())
                            
                            airline_cabin_class = CabinClassCodeMapping[cabin_item]
                        else:
                            continue
                        
                        points = cabin_price.get("connections", [{}])[0].get("price", {}).get("amount", 0)
                        
                        tax =  cabin_price.get("connections", [])[0].get("tax", {}) or {}
                        amount = tax.get("amount", 0)
                        currency = tax.get("currencyCode", '')
                        
                        final_flight = Flight(
                            airline=str(self.AIRLINE.value),
                            origin=segments[0].origin,
                            destination=segments[-1].destination,
                            cabin_class=str(cabin_item.value),
                            airline_cabin_class=airline_cabin_class,
                            points=points,
                            cash_fee=CashFee(
                                amount=amount,
                                currency=currency,
                            ),
                            segments=segments,
                            duration=duration_isoformat(datetime.timedelta(minutes=offerItinerary.get("activeConnection", {}).get("duration", 0))),
                        )
                        
                        yield final_flight

        except (LiveCheckerException, Exception) as e:
            logger.error(f"{self.AIRLINE.value} - requestId: {requestId}: {origin}-{destination}-{departure_date.isoformat()} data: {data}")
            raise e


if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = AFEngineoCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=12, day=27)
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
        print("flights ==============>", flights)

        if flights:
            with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    run("IAD", "CDG", CabinClass.Economy, 2)
    # run("LAX", "HND", CabinClass.Economy, 3)
    # run("JFK", "LHR", CabinClass.Economy, 1)
    # run("JFK", "LHR", CabinClass.Business, 1)
    # run("JFK", "LAX", CabinClass.Economy, 3)
