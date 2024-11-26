from zenrows import ZenRowsClient
import datetime
from collections import namedtuple
from typing import Iterator, List

from curl_cffi import requests as crequests
from isodate import duration_isoformat

from src.aa.constants import (
    BookingCode2AmericanCabinClass,
    CabinClass2BookingCode,
    CabinClassMap,
)
from src import constants as c
from src.aa.headers import GET_FLIGHT_POINTS_HEADDER
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException, NoSearchResult
from src.schema import CashFee, Flight, FlightSegment

FlightTime = namedtuple("FlightTime", ["date", "time", "timezone"])


def parse_datetime(time_format_string: str) -> FlightTime:
    parsed_datetime = datetime.datetime.strptime(time_format_string, "%Y-%m-%dT%H:%M:%S.%f%z")
    return FlightTime(
        date=parsed_datetime.date().isoformat(),
        time=parsed_datetime.time().strftime("%H:%M"),
        timezone=f"{parsed_datetime.tzinfo}",
    )


class AmericanAirlineZenrowRequestsCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.AmericanAirline

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: CabinClass = CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        json_data = {
            "metadata": {
                "selectedProducts": [],
                "tripType": "OneWay",
                "udo": {},
            },
            "passengers": [
                {
                    "type": "adult",
                    "count": adults,
                },
            ],
            "requestHeader": {
                "clientId": "AAcom",
            },
            "slices": [
                {
                    "allCarriers": True,
                    "cabin": "",
                    "departureDate": departure_date.isoformat(),
                    "destination": destination,
                    "destinationNearbyAirports": False,
                    "maxStops": None,
                    "origin": origin,
                    "originNearbyAirports": False,
                },
            ],
            "tripOptions": {
                "searchType": "Award",
                "corporateBooking": False,
                "locale": "en_US",
            },
            "loyaltyInfo": None,
            "queryParams": {
                "sliceIndex": 0,
                "sessionId": "",
                "solutionSet": "",
                "solutionId": "",
            },
        }

        try:
            client = ZenRowsClient(c.ZENROWS_API_KEY)
            params = {"premium_proxy":"true"}
            response = client.post(
                "https://www.aa.com/booking/api/search/itinerary",
                headers=GET_FLIGHT_POINTS_HEADDER,
                json=json_data,
                params=params
            )
            if response.status_code != 200:
                raise LiveCheckerException(
                    airline=Airline.AmericanAirline,
                    origin=origin,
                    destination=destination,
                    date=departure_date.isoformat(),
                    data=response.text,
                )

            data = response.json()
            if data["error"]:
                raise NoSearchResult(airline=Airline.AmericanAirline)

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

            slices = data.get("slices", [])
            for slice in slices:
                for cabin_item in all_cabins:
                    segments: List[FlightSegment] = []
                    for slice_segment in slice.get("segments", []):
                        departure_datetime = slice_segment.get("departureDateTime")
                        segment_departure_datetime = parse_datetime(departure_datetime) if departure_datetime else None

                        arrival_datetime = slice_segment.get("arrivalDateTime")
                        segment_arrival_datetime = parse_datetime(arrival_datetime) if arrival_datetime else None
                        segment_aircraft = None
                        segment_legs = slice_segment.get("legs", [])
                        layover_time = segment_legs[0]["connectionTimeInMinutes"]
                        if layover_time:
                            layover_time = duration_isoformat(datetime.timedelta(minutes=layover_time))
                        else:
                            layover_time = None

                        if segment_legs:
                            segment_leg = segment_legs[0]
                            aircraft = [
                                segment_leg.get("aircraft", {}).get("code", ""),
                                segment_leg.get("aircraft", {}).get("shortName", ""),
                            ]
                            segment_aircraft = "-".join([_it.strip() for _it in aircraft if _it.strip()])

                        segments.append(
                            FlightSegment(
                                origin=slice_segment.get("origin", {}).get("code", ""),
                                destination=slice_segment.get("destination", {}).get("code", ""),
                                departure_date=segment_departure_datetime.date,
                                departure_time=segment_departure_datetime.time,
                                departure_timezone=segment_departure_datetime.timezone,
                                arrival_date=segment_arrival_datetime.date,
                                arrival_time=segment_arrival_datetime.time,
                                arrival_timezone=segment_arrival_datetime.timezone,
                                aircraft=segment_aircraft,
                                flight_number=slice_segment.get("flight", {}).get("flightNumber", ""),
                                carrier=slice_segment.get("flight", {}).get("carrierCode"),
                                duration=duration_isoformat(
                                    datetime.timedelta(minutes=segment_legs[0]["durationInMinutes"])
                                ),
                                layover_time=layover_time,
                            )
                        )

                    for cabin_price in slice.get("pricingDetail", []):
                        product_type = cabin_price["productType"].lower()
                        if product_type in ["premium_economy", "business", "first"]:
                            if product_type == cabin_item.value.lower():
                                airline_cabin_class = CabinClassMap[cabin_item]
                            else:
                                continue
                        else:
                            if product_type in ["coach", "main"]:
                                airline_cabin_class = "Main Cabin"
                            else:
                                extended_fare_code = cabin_price.get("extendedFareCode")

                                if not extended_fare_code:
                                    continue

                                fare_code = extended_fare_code[0]
                                if fare_code not in CabinClass2BookingCode[cabin_item]:
                                    continue
                                airline_cabin_class = BookingCode2AmericanCabinClass[fare_code]

                        ## since API can match flight by finger_print=flight_number
                        # so in scraper, we must be sure the correct cabin class to be returned
                        if CabinClassMap[cabin_item] not in airline_cabin_class:
                            continue

                        if (points := cabin_price.get("perPassengerAwardPoints", -1)) > 0:
                            yield Flight(
                                airline=str(self.AIRLINE.value),
                                origin=slice.get("origin", {}).get("code", ""),
                                destination=slice.get("destination", {}).get("code", ""),
                                cabin_class=str(cabin_item.value),
                                airline_cabin_class=airline_cabin_class,
                                points=points,
                                cash_fee=CashFee(
                                    amount=cabin_price.get("perPassengerTaxesAndFees", {}).get("amount", 0),
                                    currency=cabin_price.get("perPassengerTaxesAndFees", {}).get("currency"),
                                ),
                                segments=segments,
                                duration=duration_isoformat(datetime.timedelta(minutes=slice["durationInMinutes"])),
                            )

        except (LiveCheckerException, Exception) as e:
            raise e


if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()
        crawler = AmericanAirlineZenrowRequestsCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=10, day=27)
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

    # run("IAD", "CDG", CabinClass.All, 1)
    # run("ORD", "BCN", CabinClass.Economy, 1)
    # run("CPT", "HAV", CabinClass.Economy)
    # run("LAX", "HND", CabinClass.Economy, 3)
    run("JFK", "LHR", CabinClass.Economy, 1)
    # run("JFK", "LHR", CabinClass.Business, 1)
    # run("LAX", "HND", CabinClass.Business, 3)
    # run("IAH", "DXB", CabinClass.Business, 1)
    # run("JFK", "LAX", CabinClass.Economy, 3)
