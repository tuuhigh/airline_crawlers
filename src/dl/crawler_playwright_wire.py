import datetime
import json
import logging
import random
import time
from collections import namedtuple
from typing import Dict, Iterator, List, Optional
from isodate import duration_isoformat

from undetected_playwright.sync_api import TimeoutError

from playwright.sync_api import Page
from src import constants as c
from src.dl.constants import (
    AirlineCabinClassCodeMapping, 
    CabinClassCodeMappingForHybrid, 
    AirCraftIATACode, 
    FareName2CabinClassMapping
)
from src.exceptions import NoSearchResult, CrawlerException
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.schema import CashFee, Flight, FlightSegment
from src.db import insert_target_headers

logger = logging.getLogger(__name__)
GeoLocationConfiguration = namedtuple("GeoLocationConfiguration", ("proxy_host", "proxy_port", "home_page_url"))
GeoLocationConfigurations = [
    GeoLocationConfiguration(
        proxy_host="us.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com"
    ),
    GeoLocationConfiguration(
        proxy_host="ca.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/ca/en"
    ),
    GeoLocationConfiguration(
        proxy_host="gb.smartproxy.com", proxy_port="30001", home_page_url="https://www.delta.com/gb/en"
    ),
    GeoLocationConfiguration(
        proxy_host="nl.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com/eu/en"
    ),
    GeoLocationConfiguration(
        proxy_host="de.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/eu/en"
    ),
    GeoLocationConfiguration(
        proxy_host="fr.smartproxy.com", proxy_port="40001", home_page_url="https://www.delta.com/fr/en"
    ),
    GeoLocationConfiguration(
        proxy_host="mx.smartproxy.com", proxy_port="20001", home_page_url="https://www.delta.com/mx/en"
    ),
    GeoLocationConfiguration(
        proxy_host="br.smartproxy.com", proxy_port="10001", home_page_url="https://www.delta.com/br/en"
    ),
]


class DeltaAirlinePlaywrightWireCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.DeltaAirline
    REQUIRED_LOGIN = False
    BLOCK_RESOURCE = True
    TARGET = 'delta'
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smart_proxy_host, self.smart_proxy_port, self.home_page_url = random.choice(GeoLocationConfigurations)
    
    def convert_to_seconds(self, days=0, hours=0, minutes=0):
        return (3600 * 24 * days) + (3600 * hours) + (60 * minutes)

    def get_proxy(self):
        
        # return {
        #     "ip": "geo.iproyal.com",
        #     "port": "12321",
        #     "user": "ihgproxy1",
        #     "pwd": "ihgproxy1234_country-us",
        # }
        return {
            "ip": self.smart_proxy_host,
            "port": self.smart_proxy_port,
            "user": "spyc5m5gbs",
            "pwd": "puFNdLvkx6Wcn6h6p8",
        }

    def _select_locale(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        try:
            page.click(".btn-keep.btn.btn-outline-secondary-cta.rounded-0", timeout=3000)
            logger.info(f"{self.AIRLINE.value}: English selected")
        except Exception:
            logger.info(f"{self.AIRLINE.value}: No need to select language button")

    def _select_miles(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        miles_is_checked = page.is_checked('input[id="shopWithMiles"]')
        if not miles_is_checked:
            js_script_check_miles = """
                var checkbox = document.getElementById('shopWithMiles');
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change', { 'bubbles': true }));
            """
            page.evaluate(js_script_check_miles)

        flexdate_is_checked = page.is_checked('input[id="chkFlexDate"]')
        if flexdate_is_checked:
            js_script_check_flexdate = """
                var checkbox = document.getElementById('chkFlexDate');
                checkbox.checked = false;
                checkbox.dispatchEvent(new Event('change', { 'bubbles': true }));
            """
            page.evaluate(js_script_check_flexdate)

    def _select_oneway(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_tripType_dropdown = "var selectElement = document.querySelector('span[aria-owns=\"selectTripType-desc\"]'); selectElement.click();"
        js_script_select_OneWay = (
            "var selectElement = document.querySelector('li[id=\"ui-list-selectTripType1\"]'); selectElement.click();"
        )
        page.evaluate(js_script_tripType_dropdown)
        time.sleep(1)
        page.evaluate(js_script_select_OneWay)
        time.sleep(1)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_select_origin_box = "document.querySelector('#fromAirportName').click()"
        js_script_enter_origin_airport = (
            """var searchInput = document.getElementById('search_input');
            if (searchInput) {searchInput.value = '%s';}
            var closeButton = document.querySelector('.search-flyout-close.float-right.d-none.d-lg-block.circle-outline.icon-moreoptionsclose');
            if (closeButton) {closeButton.click();}
        """
            % origin
        )

        page.evaluate(js_script_select_origin_box)
        time.sleep(0.5)
        page.evaluate(js_script_enter_origin_airport)
        time.sleep(1)

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_select_dest_box = (
            "var anchorElement = document.querySelector('#toAirportName'); if (anchorElement) {anchorElement.click();}"
        )
        js_script_enter_dest_airport = (
            """
            var searchInput = document.getElementById('search_input'); if (searchInput) {searchInput.value = '%s';} \
            var closeButton = document.querySelector('.search-flyout-close.float-right.d-none.d-lg-block.circle-outline.icon-moreoptionsclose'); \
            if (closeButton) {closeButton.click();}
        """
            % destination
        )
        page.evaluate(js_script_select_dest_box)
        time.sleep(0.5)
        page.evaluate(js_script_enter_dest_airport)
        time.sleep(1)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        js_script_open_calendar = "document.querySelector('.calenderDepartSpan').click()"
        page.evaluate(js_script_open_calendar)
        time.sleep(1)

        months_until_departure_date = self.months_until_departure_date(departure_date)
        if months_until_departure_date > 0:
            js_script_scroll_date = "document.querySelectorAll('.monthSelector')[1].click()"
            for _ in range(months_until_departure_date):
                page.evaluate(js_script_scroll_date)
                time.sleep(0.2)

        js_script_select_date = """
            var element = document.querySelector("[data-date*='%s']");
            if (element) {
                element.click();
            }
        """ % departure_date.strftime(
            "%m/%d/%Y"
        )
        page.evaluate(js_script_select_date)
        print("date selected")
        time.sleep(1.5)

    def _select_flexible_dates(self, *args, **kwargs) -> None:
        pass

    def _select_passengers(self, *args, **kwargs):
        pass
    
    def intercept_request(self, route, request):

        if "/prd/rm-offer-gql" in request.url and request.method == "POST":
            route.continue_()
            try:
                response = request.response()
                response_body = response.json()
                dl_headers = request.all_headers()
                insert_target_headers(dl_headers, self.TARGET)
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
        self.intercepted = False
        self.intercepted_response = None
        page: Page = kwargs.get("page")
        page.click('xpath=//button[@id="btn-book-submit"]')
        time.sleep(3)
        
        page.route("**", lambda route, request: self.intercept_request(route, request))
        

    def continue_search(self, page: Page):
        logger.info(f"{self.AIRLINE.value}: Continue Search...")
        try:
            page.wait_for_load_state(timeout=30000)
            # check flight availability on flexible page
            logger.info(f"{self.AIRLINE.value}: Checking if it lands on Flexible dates Page...")
            selected_date_element = page.locator(
                "//div[contains(@class, 'flexible-dates-grid-row')]/div[contains(@class, 'isSelected') and contains(@class, 'isPriceCell')]"
            )
            selected_date_element.wait_for(timeout=30000)
            is_flexible_dates_page = True
        except TimeoutError:
            is_flexible_dates_page = False

        if is_flexible_dates_page:
            logger.info(f"{self.AIRLINE.value}: On flexible dates page, checking availability...")

            lowest_price_text = self.get_text(selected_date_element)
            if lowest_price_text.lower() == "not available":
                logger.info(f"{self.AIRLINE.value}: No available flights...")
                raise NoSearchResult(airline=self.AIRLINE, reason="Not available flights on Flexible Page")

            try:
                # accept policy
                logger.info(f"{self.AIRLINE.value}: Check if policy popup displayed...")
                accept_cookie_buton = page.locator("//button[@class='btn btn-secondary-cta']")
                accept_cookie_buton.wait_for(timeout=10000)
                accept_cookie_buton.click()
            except TimeoutError:
                pass
            
            try:
                # accept cookies
                logger.info(f"{self.AIRLINE.value}: Have available flights on flexible dates page, continue...")
                accept_cookie_buton = page.locator(".btn-danger.gdpr-banner-btn.gdpr-banner-accept-btn")
                accept_cookie_buton.wait_for(timeout=3000)
                accept_cookie_buton.click()
            except TimeoutError:
                pass

            try:
                # Continue to search
                logger.info(f"{self.AIRLINE.value}: Click continue buttons...")
                continue_button = page.locator("//idp-button[contains(@class, 'flex-dates-continue-btn')]//button")
                continue_button.wait_for(timeout=3000)
                continue_button.click()
                time.sleep(3)
            except TimeoutError:
                pass
        else:
            try:
                advance_search = page.locator("//div[@class='idp-advance-search']/idp-error-message")
                advance_search.wait_for(timeout=3000)
                raise NoSearchResult(airline=self.AIRLINE, reason="Does not support this route")
            except TimeoutError as e:
                raise e

    def get_pricing_flights(self, page: Page) -> None:
        # page.wait_for_load_state()
        page.click('xpath=//a[@id="PriceTab_0"]')
        time.sleep(3)
        
    
    def load_more(self, page: Page) -> None:
        page.wait_for_load_state()
        try:
            logger.info(f"{self.AIRLINE.value}: Waiting for search result...")
            search_result = page.locator("//idp-flight-grid")
            search_result.wait_for(timeout=60000)
        except TimeoutError as e:
            raise NoSearchResult(airline=self.AIRLINE, reason=f"{e}")

        try:
            logger.info(f"{self.AIRLINE.value}: Checking if there is more button...")
            load_more_button = page.locator(
                "//div[contains(@class, 'search-results__load-more-btn')]//button[contains(@class, 'idp-btn')]"
            )
            load_more_button.wait_for(timeout=1000)
            load_more_button.click()
        except Exception:
            pass

    def extract_flight_detail(
        self,
        flight_data: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment_element in enumerate(flight_data["trips"][0]["flightSegment"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                if segment_element.get("layover", {}):
                    connection_time_hours = segment_element.get("layover", {}).get("layoverDuration", {}).get("hourCnt", 0)
                    connection_time_minutes = segment_element.get("layover", {}).get("layoverDuration", {}).get("minuteCnt", 0)
                    connection_time = self.convert_to_seconds(0, connection_time_hours, connection_time_minutes)
                else:
                    connection_time = 0

                segment_origin = segment_element["originAirportCode"]
                segment_destination = segment_element["destinationAirportCode"]
                segment_departure_time = segment_element["scheduledDepartureLocalTs"]
                segment_arrival_time = segment_element["scheduledArrivalLocalTs"]
                aircraft_id = segment_element["aircraftTypeCode"]
                segment_aircraft = AirCraftIATACode.get(aircraft_id, "")
                segment_carrier = segment_element.get('marketingCarrier', {}).get('carrierCode', None)
                if not segment_carrier:
                    segment_carrier = segment_element.get('operatingCarrier', {}).get('carrierCode', None)
                segment_flight_number = segment_element.get('marketingCarrier', {}).get('carrierNum', None)
                if not segment_flight_number:
                    segment_flight_number = segment_element.get('operatingCarrier', {}).get('carrierNum', None)

                flight_leg = segment_element["flightLeg"][0]
                segment_duration_hours = flight_leg["duration"]["hourCnt"]
                segment_duration_minutes = flight_leg["duration"]["minuteCnt"]
                segment_duration = self.convert_to_seconds(0, segment_duration_hours, segment_duration_minutes)

                flight_segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_time and segment_departure_time.split("T")[0],
                        departure_time=segment_departure_time
                        and segment_departure_time.split("T")[1].split(".")[0],
                        departure_timezone=segment_departure_time and segment_departure_time.split(".000")[-1],
                        arrival_date=segment_arrival_time and segment_arrival_time.split("T")[0],
                        arrival_time=segment_arrival_time and segment_arrival_time.split("T")[1].split(".")[0],
                        arrival_timezone=segment_arrival_time and segment_arrival_time.split(".000")[-1],
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
        self, flight_data, currency, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        cabin_class_codes = CabinClassCodeMappingForHybrid[cabin_class]
        points_by_fare_names: Dict[str, dict] = {}

        for offer in flight_data["offers"]:
            fare_code = offer["additionalOfferProperties"]["dominantSegmentBrandId"]
            
            if cabin_class != c.CabinClass.All and fare_code not in cabin_class_codes:
                continue

            try:
                fare_name = AirlineCabinClassCodeMapping[fare_code]
                if not offer["offerId"]:
                    points = -1
                    amount = 0
                else:
                    points = offer["offerItems"][0]["retailItems"][0]["retailItemMetaData"]["fareInformation"][0]["farePrice"][0]["totalFarePrice"]["milesEquivalentPrice"]["mileCnt"]
                    amount = offer["offerItems"][0]["retailItems"][0]["retailItemMetaData"]["fareInformation"][0]["farePrice"][0]["totalFarePrice"]["currencyEquivalentPrice"]["roundedCurrencyAmt"]

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
    
    def extract_sub_classes_cash(
        self, flight_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes Cash...")
        cabin_class_codes = CabinClassCodeMappingForHybrid[cabin_class]
        cash_by_fare_names: Dict[str, dict] = {}

        for offer in flight_data["offers"]:
            fare_code = offer["additionalOfferProperties"]["dominantSegmentBrandId"]
            if cabin_class != c.CabinClass.All and fare_code not in cabin_class_codes:
                continue

            try:
                fare_name = AirlineCabinClassCodeMapping[fare_code]
                if not offer["offerId"]:
                    amount = -1
                else:
                    amount = offer["offerItems"][0]["retailItems"][0]["retailItemMetaData"]["fareInformation"][0]["farePrice"][0]["totalFarePrice"]["currencyEquivalentPrice"]["roundedCurrencyAmt"]

                cash_by_fare_names[fare_name] = amount
            except Exception as e:
                logger.info(f"{self.AIRLINE.value}: extract_sub_classes_cash exception: {e}")

        return cash_by_fare_names
    
    def parse_points_flights(
        self, flights_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flights = list()
        flight_search_results = flights_data.get("data", {}).get("gqlSearchOffers", {}) or {}
        flight_search_results = flight_search_results.get("gqlOffersSets", [])
        currency = flights_data["data"]["gqlSearchOffers"]["offerDataList"]["pricingOptions"][0]["pricingOptionDetail"]["currencyCode"]
        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} Points Flights...")
        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Points Retrieving the detail of search item => index: {index}...")

            points_by_fare_names = self.extract_sub_classes_points(flight_search_result, currency, cabin_class)
            if not points_by_fare_names:
                continue

            try:
                segments = self.extract_flight_detail(flight_search_result)
            except Exception as e:
                raise e
            total_trip_time = flight_search_result["trips"][0]["totalTripTime"]
            total_trip_time_hours = total_trip_time["hourCnt"]
            total_trip_time_minutes = total_trip_time["minuteCnt"]
            duration = self.convert_to_seconds(0, total_trip_time_hours, total_trip_time_minutes)
            for fare_name, points_and_cash in points_by_fare_names.items():
                flight_cabin_class = FareName2CabinClassMapping.get(fare_name)
                if not segments:
                    continue
                flight = Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=flight_cabin_class and str(flight_cabin_class.value) or "",
                    airline_cabin_class=fare_name,
                    fare_brand_name=fare_name,
                    points=points_and_cash["points"],
                    cash_fee=points_and_cash["cash_fee"],
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                )
                flights.append(flight)
        return flights
    
    def parse_cash_flights(
        self, flights_data, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        flights = list()
        flight_search_results = flights_data.get("data", {}).get("gqlSearchOffers", {}) or {}
        flight_search_results = flight_search_results.get("gqlOffersSets", [])
        currency = flights_data["data"]["gqlSearchOffers"]["offerDataList"]["pricingOptions"][0]["pricingOptionDetail"]["currencyCode"]
        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)} Cash Flights...")
        for index, flight_search_result in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Cash Retrieving the detail of search item => index: {index}...")

            cash_by_fare_names = self.extract_sub_classes_cash(flight_search_result, cabin_class)
            if not cash_by_fare_names:
                continue

            try:
                segments = self.extract_flight_detail(flight_search_result)
            except Exception as e:
                raise e
            total_trip_time = flight_search_result["trips"][0]["totalTripTime"]
            total_trip_time_hours = total_trip_time["hourCnt"]
            total_trip_time_minutes = total_trip_time["minuteCnt"]
            duration = self.convert_to_seconds(0, total_trip_time_hours, total_trip_time_minutes)
            for fare_name, cash_amount in cash_by_fare_names.items():
                flight_cabin_class = FareName2CabinClassMapping.get(fare_name)
                if not segments:
                    continue
                flight = Flight(
                    airline=str(self.AIRLINE.value),
                    origin=segments[0].origin,
                    destination=segments[-1].destination,
                    cabin_class=flight_cabin_class and str(flight_cabin_class.value) or "",
                    airline_cabin_class=fare_name,
                    fare_brand_name=fare_name,
                    amount=cash_amount,
                    segments=segments,
                    duration=duration_isoformat(datetime.timedelta(seconds=duration)),
                )
                flights.append(flight)
        return flights
    
    def match_flights(self, cash_flights: List[Flight], points_flights: List[Flight]):
        flights = []
        logger.info(f"{self.AIRLINE.value}: Doing matching for {len(cash_flights)} Cash and {len(points_flights)} Points")
        sorted_points_flights = dict()
        for points_flight in points_flights:
            flight_numbers = [segment.flight_number for segment in points_flight.segments]
            flight_number = '-'.join(flight_numbers)
            flight_key = f'{flight_number}-{points_flight.airline_cabin_class}'
            sorted_points_flights[flight_key] = points_flight

        print(f">>>> sorted_points_flights: {sorted_points_flights}")
        
        sorted_cash_flights = dict()
        for cash_flight in cash_flights:
            flight_numbers = [segment.flight_number for segment in cash_flight.segments]
            flight_number = '-'.join(flight_numbers)
            flight_key = f'{flight_number}-{cash_flight.airline_cabin_class}'
            sorted_cash_flights[flight_key] = cash_flight
        print(f">>>> sorted_cash_flights: {sorted_cash_flights}")
        
        for flight_key, sorted_points_flight in sorted_points_flights.items():
            if flight_key in sorted_cash_flights:
                sorted_points_flight.amount = sorted_cash_flights[flight_key].amount
                del sorted_cash_flights[flight_key]

            flights.append(sorted_points_flight)

        flights = flights + list(sorted_cash_flights.values())

        return flights

    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        # self.continue_search(page)
        self.load_more(page)
        points_flights_response = self.intercepted_response
        self.intercepted_response = None

        self.get_pricing_flights(page)
        self.load_more(page)
        pricing_flights_response = self.intercepted_response
        
        # if not self.intercepted_response:
        #     raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

        # if self.intercepted_response.get('shoppingError', {}).get('error', {}).get('message', ''):
        #     raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

        points_flights = self.parse_points_flights(points_flights_response, cabin_class)
        cash_flights = self.parse_cash_flights(pricing_flights_response, cabin_class)
        
        flights = self.match_flights(cash_flights, points_flights)
        for flight in flights:
            yield flight


if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = DeltaAirlinePlaywrightWireCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=11, day=25)

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
    # run("LHR", "PEK", c.CabinClass.PremiumEconomy)
    run("ATL", "LHR", c.CabinClass.All)
    # run("JFK", "HND", c.CabinClass.Economy)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
