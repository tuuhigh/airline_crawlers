import datetime
import json
import logging
import time
import random
from typing import Dict, Iterator, List, Optional
from http.cookies import SimpleCookie

from isodate import duration_isoformat
from collections import namedtuple

from curl_cffi import requests as crequests
from src import constants as c
from src.ua.constants import CabinClassCodeMapping, CabinClassZenrowsCodeMapping
from src.exceptions import NoSearchResult, AirlineCrawlerException
from src.base import RequestsBasedAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.db import get_target_headers, update_target_headers
logger = logging.getLogger(__name__)

class UnitedRequestsCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = c.Airline.UnitedAirline
    TARGET = "united"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_proxy(self):
        # proxy_user = "ihgproxy1"
        # proxy_pass = "ihgproxy1234_country-us"
        # proxy_host = "geo.iproyal.com"
        # proxy_port = "12321"

        return {
            "ip": "geo.iproyal.com",
            "port": "12321",
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-ca",
        }

        # return {
        #     "ip": self.smart_proxy_host,
        #     "port": self.smart_proxy_port,
        #     "user": "spyc5m5gbs",
        #     "pwd": "puFNdLvkx6Wcn6h6p8",
        # }
        
    def setup_proxy_str(self):    
        proxy = self.get_proxy()
        proxy_host = proxy.get('ip')  # rotating proxy or host
        proxy_port = int(proxy.get('port'))  # port
        proxy_user = proxy.get('user')  # username
        proxy_pass = proxy.get('pwd')  # password
        
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        return proxy_attr
    
    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []
        
        first_connection_time = 0
        try:
            first_layover_min = flight_data["Connections"][0]["ConnectTimeMinutes"]
            if first_layover_min:
                first_connection_time = first_layover_min * 60
        except:
            pass

        first_segment_origin = flight_data["Origin"]
        first_segment_destination = flight_data["Destination"]
        first_segment_departure_datetime = flight_data["DepartDateTime"]
        first_segment_departure_datetime = datetime.datetime.fromisoformat(first_segment_departure_datetime)
        first_segment_arrival_datetime = flight_data["DestinationDateTime"]
        first_segment_arrival_datetime = datetime.datetime.fromisoformat(first_segment_arrival_datetime)
        first_segment_aircraft = flight_data["EquipmentDisclosures"]["EquipmentDescription"]
        first_segment_carrier = flight_data["MarketingCarrier"]
        first_segment_flight_number = flight_data["OriginalFlightNumber"]
        first_duration_min = flight_data["TravelMinutes"]
        first_segment_duration = 60 * first_duration_min

        flight_segments.append(
            FlightSegment(
                origin=first_segment_origin,
                destination=first_segment_destination,
                departure_date=first_segment_departure_datetime.date().isoformat(),
                departure_time=first_segment_departure_datetime.time().isoformat()[:5],
                departure_timezone="",
                arrival_date=first_segment_arrival_datetime.date().isoformat(),
                arrival_time=first_segment_arrival_datetime.time().isoformat()[:5],
                arrival_timezone="",
                aircraft=first_segment_aircraft,
                flight_number=first_segment_flight_number,
                carrier=first_segment_carrier,
                duration=duration_isoformat(datetime.timedelta(seconds=first_segment_duration)),
                layover_time=duration_isoformat(datetime.timedelta(seconds=first_connection_time))
                if first_connection_time
                else None,
            )
        )
        
        for segment_index, segment_element in enumerate(flight_data["Connections"]):
            try:
                connection_time = 0
                try:
                    layover_min = flight_data["Connections"][segment_index + 1]["ConnectTimeMinutes"]
                    if layover_min:
                        connection_time = layover_min * 60
                except:
                    pass
                    
                segment_origin = segment_element["Origin"]
                segment_destination = segment_element["Destination"]
                segment_departure_datetime = segment_element["DepartDateTime"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment_element["DestinationDateTime"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                segment_aircraft = segment_element["EquipmentDisclosures"]["EquipmentDescription"]
                segment_carrier = segment_element["MarketingCarrier"]
                segment_flight_number = segment_element["OriginalFlightNumber"]

                duration_min = segment_element["TravelMinutes"]
                segment_duration = 60 * duration_min

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
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Classes points...")
        points_by_fare_names: Dict[str, dict] = {}

        cabin_class_code = CabinClassCodeMapping[cabin_class]
        
        fare_name = CabinClassZenrowsCodeMapping[cabin_class]
        
        points_by_fare_names[fare_name] = {
            "points": -1,
            "cash_fee": CashFee(
                amount=0,
                currency="",
            ),
        }
        
        for sub_class in flight_data['Products']:
            if sub_class['ProductType'] == cabin_class_code:
                try:
                    points = sub_class['Prices'][0]['Amount']
                    amount = sub_class['Prices'][1]['Amount']
                    currency = sub_class['Prices'][1]['Currency']
                    points_by_fare_names[fare_name] = {
                        "points": points,
                        "cash_fee": CashFee(
                            amount=amount,
                            currency=currency,
                        ),
                    }
                except:
                    pass
                break
            
        return points_by_fare_names
    
    def now_milliseconds(self):
        return int(time.time())
    
    def compute_new_headers(self, headers):
        cookie_str = headers['cookie']
        # cookie = SimpleCookie()
        # cookie.load(cookie_str)

        # Even though SimpleCookie is dictionary-like, it internally uses a Morsel object
        # which is incompatible with requests. Manually construct a dictionary instead.
        cookies = (dict(i.split('=', 1) for i in cookie_str.split('; ')))
        # cookies = {k: v.value for k, v in cookie.items()}
        ck_akavpau_ualwww = cookies.get('akavpau_ualwww', '')
        if ck_akavpau_ualwww:
            # logger.info(f">>>>> origin_cookie: {ck_akavpau_ualwww}")
            ck_akavpau_ualwwws = ck_akavpau_ualwww.split('~')
            current_timestamp = self.now_milliseconds()
            new_ck_akavpau_ualwww = f"{current_timestamp}~{ck_akavpau_ualwwws[1]}"
            cookies['akavpau_ualwww'] = new_ck_akavpau_ualwww
            # logger.info(f">>>>> computed_cookie: {new_ck_akavpau_ualwww}")
        return cookies
        
    def get_flights(self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1
    ):
        headers_recs = get_target_headers(self.TARGET)
        ### only need to try 15
        headers_recs = headers_recs[:15]
        random.shuffle(headers_recs)
        retry_count = len(headers_recs)
        
        for i, headers_rec in enumerate(headers_recs):
            headers = headers_rec.get("headers", {})
            cookies = self.compute_new_headers(headers)
            del headers["cookie"]
            
            json_data = headers_rec.get("payload", {})
            json_data["Trips"][0].update({
                'Origin': origin,
                'Destination': destination,
                'DepartDate': departure_date.strftime('%Y-%m-%d'),
            })
            
            proxy_attr = self.setup_proxy_str()
            response = crequests.post(
                'https://www.united.com/api/flight/FetchFlights',
                impersonate="chrome120",
                proxies=proxy_attr, 
                cookies=cookies,
                headers=headers, 
                json=json_data,
            )
            logger.info(f"{self.AIRLINE.value} - {cabin_class.value}: Retrieving Points API Data => {i+1}/{retry_count} => Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.info(f"{self.AIRLINE.value} - Failed with cabin class: {cabin_class.value}: result: {response.text}")
                logger.info(f"{self.AIRLINE.value} - headers: {headers}: proxy: {proxy_attr}")
                headers_id = headers_rec.get("_id")
                update_target_headers(headers_id, {"active": False}, self.TARGET)

        raise AirlineCrawlerException(self.AIRLINE, "No active headers to run")
    
    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1, 
        **kwargs
    ) -> Iterator[Flight]:
        flights_data = self.get_flights(origin, destination, departure_date, cabin_class, adults)
        
        
        if not flights_data:
            raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
        
        if any(error["title"] == "NO FLIGHTS FOUND" for error in flights_data.get("errors", [])):
            raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

        if not flights_data['data']['Trips']:
            logger.info(f"{self.AIRLINE.value} - {cabin_class.value} not found trips: {flights_data}")
            raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")
                
        flight_search_results = flights_data['data']['Trips'][0]['Flights']
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
            
            for cabin_item in all_cabins:
                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, cabin_item)
                if not points_by_fare_names:
                    continue
        
                try:
                    segments = self.extract_flight_detail(flight_search_result)
                except Exception as e:
                    raise e
            
                duration = flight_search_result["TravelMinutesTotal"]
                duration_s = duration * 60
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
                        duration=duration_isoformat(datetime.timedelta(seconds=duration_s)),
                    )
                    yield flight


if __name__ == "__main__":
    # import threading
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = UnitedRequestsCrawler()
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

    run("JFK", "LHR", c.CabinClass.All)
    # run("PVG", "BRU", c.CabinClass.Economy)
    # run("JFK", "LHR", c.CabinClass.Economy)
    # run("LAX", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Economy)
    # asyncio.run(run("YVR", "YYZ", c.CabinClass.Economy))
    # run("KUL", "YYZ", c.CabinClass.First)
