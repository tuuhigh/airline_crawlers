import datetime
import logging
import random
from typing import Iterator, List, Optional, Tuple
import re

import requests
from bs4 import BeautifulSoup

from src import constants as c
from src.base import RequestsBasedAirlineCrawler
from src.constants import Airline, CabinClass
from src.exceptions import LiveCheckerException
from src.schema import CashFee, Flight, FlightSegment
from src.ua.constants import CabinClassZenrowsCodeMapping
from src.utils import (
    convert_k_to_float,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    parse_time,
)

logger = logging.getLogger(__name__)


class UnitedAirlineZenrowCrawler(RequestsBasedAirlineCrawler):
    AIRLINE = Airline.UnitedAirline

    @staticmethod
    def get_evaluate_param():
        return """[
            {"click": "#closeBtn"},
            {"wait":1000},
            {"evaluate":"var button = document.querySelector('.atm-c-btn.atm-c-btn--primary.atm-c-btn--block'); if (button) {button.click();};"},
            {"wait":3000},
            {"evaluate":"const buttons = document.querySelectorAll('.atm-c-btn.atm-c-btn--link.atm-c-btn--small'); buttons.forEach(button => {if (button.getAttribute('aria-label') === 'Details') {button.scrollIntoView(); button.click();}});"},
            {"wait":5000}
        ]"""

    @staticmethod
    def extract_points(flight_data, cabin_class: CabinClass) -> Optional[Tuple[float, CashFee]]:
        pricing_data = flight_data.find_all("div", class_="app-components-Shopping-PriceCard-styles__top--W4RTY")
        for data in pricing_data:
            cabin_title = (
                data.find(
                    "div",
                    class_="app-components-Shopping-PriceCard-styles__cabinTitle--ikjUl "
                    "app-components-Shopping-PriceCard-styles__mobViewOnly--SJl_L",
                )
                .text.replace("(lowest)", "")
                .strip()
            )
            cabin_class_code = CabinClassZenrowsCodeMapping[cabin_class]
            if cabin_class_code == cabin_title:
                miles_cost_str = data.find(
                    "div", class_="app-components-Shopping-Miles-styles__fontStyle--U52XW"
                ).text.strip()
                points = convert_k_to_float(miles_cost_str)
                if not points:
                    continue

                tax_cost_str_element = data.find(
                    "div", class_="app-components-Shopping-PriceCard-styles__moneyContainer--KK_oN"
                )
                tax_cost_str = tax_cost_str_element.find_all("span")
                if not tax_cost_str:
                    continue

                tax_cost_str = tax_cost_str[1].text.strip()
                currency, amount = extract_currency_and_amount(tax_cost_str)
                return points, CashFee(currency=currency, amount=amount)

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
            url = (
                f"https://www.united.com/en/us/fsr/choose-flights?f={origin}&t={destination}&"
                f"d={departure_date.isoformat()}&tt=1&at=1&sc=7&px={adults}&taxng=1&newHP=True&clm=7&st=bestmatches&tqp=A"
            )

            # TODO: Need to update the params so that it returns asap when UA does not support route
            params = {
                "url": url,
                "apikey": c.ZENROWS_API_KEY,
                "js_render": "true",
                "antibot": "true",
                "wait_for": ".app-components-Shopping-FareWheelCard-styles__dateLabel--p6suN",
                "js_instructions": self.get_evaluate_param(),
                "premium_proxy": "true",
                "proxy_country": random.choice(["us", "ca"]),
                "block_resources": "image,media,font",
            }
            logger.info(f"{self.AIRLINE.value}: Making Zenrows calls...")
            response = requests.get("https://api.zenrows.com/v1/", params=params)
            logger.info(f"{self.AIRLINE.value}: Got Zenrows response...")
            content = response.content
            # with open("ua_new.html", "w") as f:
            #     f.write(content)
            # with open("/home/dev/Downloads/ua_new.html", "r") as f:
            #     content = f.read()
            soup = BeautifulSoup(content, "lxml")
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

            flight_cards = soup.find_all("div", class_="app-components-Shopping-GridItem-styles__flightRow--QbVXL")
            logger.info(f"{self.AIRLINE.value}: Found {len(flight_cards)} flights...")
            for index, flight_data in enumerate(flight_cards):
                logger.info(f"{self.AIRLINE.value}: Parsing {index + 1}th flight...")
                for cabin_item in crawler_cabin_classes:
                    points_and_cash = self.extract_points(flight_data, cabin_item)
                    if points_and_cash is None:
                        continue

                    logger.info(f"{self.AIRLINE.value}: {index + 1}th flight has prices and cash...")
                    points, cash_fee = points_and_cash
                    segments: List[FlightSegment] = []

                    layover_times = []
                    layover_time_divs = flight_data.find_all("div", class_="app-components-Shopping-FlightDetailCard-styles__dividerText--sN72G")
                    layover_time_spans = [layover_time_div.find_all("span")[-1] for layover_time_div in layover_time_divs]
                    if layover_time_spans:
                        layover_times = [
                            ele.text for ele in layover_time_spans if ele.text
                        ]

                    total_duration = None
                    duration_div = flight_data.find("div", class_="app-components-Shopping-FlightInfoBlock-styles__duration--P3ZXi")
                    if duration_div:
                        total_duration_txt = duration_div.find("span").text.strip()
                        total_duration = f'PT{total_duration_txt.replace(", ", "")}'
                    
                    flight_details_data = flight_data.find(
                        "div", class_="app-components-Shopping-FlightDetailCard-styles__flightDetails--dXkgx"
                    )

                    if not flight_details_data:
                        continue

                    flight_legs = flight_details_data.find_all(
                        "div", class_="app-components-Shopping-FlightDetailCard-styles__detailflightInfo--bzsXK"
                    )
                    segment_departure_date = departure_date

                    for leg_index, leg in enumerate(flight_legs):
                        origin_airport_code = (
                            leg.find(
                                "div",
                                class_="app-components-Shopping-FlightInfoBlock-styles__airport--JNzMu "
                                "app-components-Shopping-FlightInfoBlock-styles__departAirport--bcJF7",
                            )
                            .find("span")
                            .text.strip()
                        )
                        dest_airport_code = (
                            leg.find(
                                "div",
                                class_="app-components-Shopping-FlightInfoBlock-styles__airport--JNzMu "
                                "app-components-Shopping-FlightInfoBlock-styles__arrivalAirport--F8nWH",
                            )
                            .find("span")
                            .text.strip()
                        )
                        leg_duration = (
                            leg.find("div", class_="app-components-Shopping-FlightInfoBlock-styles__dividerText--Gwk7g")
                            .find("span")
                            .text.strip()
                        )
                        leg_duration = f'PT{leg_duration.replace(", ", "")}'

                        times = leg.find_all("span", class_="app-components-Shopping-FlightInfoBlock-styles__time--CaNGp")
                        departure_time = parse_time(times[0].text.strip(), "%I:%M %p")
                        arrival_time = parse_time(times[1].text.strip(), "%I:%M %p")

                        flight_no_carrier = leg.find(
                            "div", class_="app-components-Shopping-FlightDetailCard-styles__aircraftInfo--QbI6w"
                        ).text.strip()

                        segment_flight_number = flight_no_carrier.split("(")[0].strip()
                        segment_carrier, segment_flight_number = extract_flight_number(segment_flight_number)
                        aircraft = flight_no_carrier.split("(", 2)[1]
                        segment_aircraft = aircraft.replace(")", "")

                        arrival_date_data = leg.find(
                            "ul",
                            {
                                "class": "app-components-Shopping-FlightDetailCard-styles__detailItemGrid--cs2Su",
                                "aria-label": "advisories",
                            },
                        )
                        if arrival_date_data:
                            arrival_dates = [
                                ele.text for ele in arrival_date_data.find_all("span") if "arrival" in ele.text
                            ]
                            if arrival_dates:
                                day_delta = int(extract_digits(arrival_dates[0]))
                                segment_arrival_date = segment_departure_date + datetime.timedelta(days=day_delta)
                            else:
                                segment_arrival_date = segment_departure_date
                        else:
                            segment_arrival_date = segment_departure_date

                        layover_time = None
                        if len(layover_times) > leg_index:
                            layover_time = layover_times[leg_index]
                            hour_match = re.search(r'(\d+) hours?', layover_time)
                            minute_match = re.search(r'(\d+) minutes?', layover_time)
                            if hour_match:
                                layover_hour = int(hour_match.group(1))
                            else:
                                layover_hour = 0

                            if minute_match:
                                layover_minute = int(minute_match.group(1))
                            else:
                                layover_minute = 0

                            layover_time = f'PT{layover_hour}H{layover_minute}M'

                        segments.append(
                            FlightSegment(
                                origin=origin_airport_code,
                                destination=dest_airport_code,
                                departure_date=segment_departure_date.isoformat(),
                                departure_time=departure_time,
                                arrival_date=segment_arrival_date.isoformat(),
                                arrival_time=arrival_time,
                                aircraft=segment_aircraft,
                                flight_number=segment_flight_number,
                                carrier=segment_carrier,
                                duration=leg_duration,
                                layover_time=layover_time
                            )
                        )
                        
                        if layover_time:
                            segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_date.isoformat() + 'T' + arrival_time)
                            segment_final_date = segment_arrival_datetime + datetime.timedelta(hours=layover_hour, minutes=layover_minute)
                            segment_departure_date = segment_final_date.date()
                        else:
                            segment_departure_date = segment_arrival_date

                    yield Flight(
                        airline=str(self.AIRLINE.value),
                        origin=origin,
                        destination=destination,
                        cabin_class=str(cabin_item.value),
                        airline_cabin_class=CabinClassZenrowsCodeMapping[cabin_item],
                        points=points,
                        cash_fee=cash_fee,
                        segments=segments,
                        duration=total_duration,
                    )

        except (LiveCheckerException, Exception) as e:
            raise e


if __name__ == "__main__":
    import json
    import time
    from dataclasses import asdict

    def run(origin, destination, cabin_class, adults):
        start_time = time.perf_counter()

        crawler = UnitedAirlineZenrowCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=7, day=29)
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

    run("EWR", "LHR", CabinClass.All, 1)
    # run("DFW", "JFK", CabinClass.Economy)
