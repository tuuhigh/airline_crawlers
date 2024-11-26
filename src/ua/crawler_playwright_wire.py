import datetime
import json
import logging
import time
from typing import Dict, Iterator, List, Optional

from isodate import duration_isoformat
from seleniumwire.utils import decode

from playwright.sync_api import Page
from src import constants as c

from src.ua.constants import CabinClassCodeMapping, CabinClassZenrowsCodeMapping
from src.exceptions import NoSearchResult
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from isodate import duration_isoformat
from src.db import insert_target_headers
# from python_ghost_cursor.playwright_sync import create_cursor

import urllib.request
import random

logger = logging.getLogger(__name__)

BLOCK_RESOURCE_NAMES = c.BLOCK_RESOURCE_TYPES

class UnitedAirlinePlaywrightWireCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.UnitedAirline
    REQUIRED_LOGIN = False
    HOME_PAGE_URL = "https://app.multiloginapp.com/WhatIsMyIP"
    BLOCK_RESOURCE = True
    TARGET = 'united'
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    @staticmethod
    def intercept_route(route):
        """intercept all requests and abort blocked ones"""
        if route.request.resource_type in c.BLOCK_RESOURCE_TYPES:
            # print(f'blocking background resource {route.request} blocked type "{route.request.resource_type}"')
            return route.abort()
        if any(key in route.request.url for key in BLOCK_RESOURCE_NAMES):
            # print(f"blocking background resource {route.request} blocked name {route.request.url}")
            return route.abort()
        return route.continue_()
    
    def get_user_agent(self):
        version1 = random.choice(range(124, 130))
        flatform = random.choice([
            "Mozilla/5.0 (X11; Linux x86_64)"
        ])
        user_agent = f"Mozilla/5.0 {flatform} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version1}.0.0.0 Safari/537.36"
        return user_agent
    
    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            # "pwd": "ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za",
            "pwd": "ihgproxy1234_country-ca",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }
        # return {
        #     "ip": 'http://pr.oxylabs.io',
        #     "user": 'odynn_2',
        #     "pwd": 'Odynn2024#Awayz',
        #     "port": '7777'
        # }
        
    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        self.origin = origin

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        self.destination = destination

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        self.departure_date = departure_date

    def _select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        self.adults = adults

    def intercept_request(self, route, request):
        if "/api/flight/FetchFlights" in request.url and request.method == "POST":
            route.continue_()
            try:
                ua_headers = request.all_headers()
                payload = request.post_data_json
                insert_target_headers(ua_headers, self.TARGET, payload)
                
                response = request.response()
                response_body = response.json()
                status_code = response.status
                self.intercepted_response = response_body
                logger.info(f"{self.AIRLINE.value}: Response from {request.url}: Status Code - {status_code}")

                if not self.intercepted_response:
                    raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

                if any(error["title"] == "NO FLIGHTS FOUND" for error in self.intercepted_response.get("errors", [])):
                    raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

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
        page.evaluate("localStorage.clear()")
        # cursor = create_cursor(page)
        
        link = (
            # "https://www.united.com/en/us/fsr/choose-flights?f=HND&t=JFK&d=2024-08-25&tt=1&at=1&sc=7&px=1&taxng=1&newHP=True&clm=7&st=bestmatches&tqp=A"
            f"https://www.united.com/en/us/fsr/choose-flights?f={self.origin}&t={self.destination}&"
            f"d={self.departure_date}&tt=1&at=1&sc=7&px={self.adults}&taxng=1&newHP=True&clm=7&st=bestmatches&tqp=A"  
        )
        page.route("**", lambda route, request: self.intercept_request(route, request))
        # page.goto("https://www.browserscan.net")
        # time.sleep(60)
        logger.info(f"{self.AIRLINE.value}: Search Link - {link}")
        page.goto(link)
        # selector = 'button.atm-c-btn.atm-c-modal__close-btn.atm-c-btn--bare'
        # page.wait_for_selector(selector)
        # cursor.click(selector)
        
    def _submit(self, *args, **kwargs):
        self._browse_reward_page(*args, **kwargs)

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

    def setup_driver(self, *args, **kwargs):
        playwright: SyncPlaywright = kwargs.get("playwright")
        default_user_agent = self.get_user_agent()
        user_agent = kwargs.get("user_agent", default_user_agent)
        proxy_vals = self.get_proxy()
        logger.info(f"setting up driver with user_agent {user_agent}.")
        proxy = None
        if proxy_vals:
            proxy_host = proxy_vals.get("ip")  # rotating proxy or host
            proxy_port = proxy_vals.get("port")  # port
            proxy_user = proxy_vals.get("user")  # username
            proxy_pass = proxy_vals.get("pwd")
            proxy = {
                "server": f"{proxy_host}:{proxy_port}",
                "username": proxy_user,
                "password": proxy_pass,
            }
            logger.info(f"running with proxy: {proxy}")

        # disable navigator.webdriver:true flag
        args = [
            "--disable-blink-features=AutomationControlled",
            f"--disable-extensions-except={self.WEB_RTC_PATH}",
            f"--load-extension={self.WEB_RTC_PATH}",
        ]
        browser = playwright.chromium.launch_persistent_context(
            args=args,
            proxy=proxy,
            user_data_dir=self._user_data_dir,
            headless=False,
            slow_mo=100,  # slow down step as human behavior,
            timezone_id="Canada/Atlantic",
            geolocation={
                "latitude": 43.651070,
                "longitude": -79.347015,
                "accuracy": 90,
            },
            # user_agent=user_agent
        )
        browser.set_default_navigation_timeout(200 * 1000)
        
        return browser
    
    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flight_search_results = self.intercepted_response['data']['Trips'][0]['Flights']
        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} flights...")
        crawler_cabin_classes = []

        if cabin_class == c.CabinClass.All:
            crawler_cabin_classes = [
                c.CabinClass.Economy,
                c.CabinClass.PremiumEconomy,
                c.CabinClass.Business,
                c.CabinClass.First
            ]
        else:
            crawler_cabin_classes = [cabin_class]

        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item => index: {index}...")
            
            for cabin_item in crawler_cabin_classes:
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
        crawler = UnitedAirlinePlaywrightWireCrawler()
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
    run("JFK", "LHR", c.CabinClass.All)
    # run("LAX", "YYZ", c.CabinClass.PremiumEconomy)
    # run("SIN", "JFK", c.CabinClass.Economy)
