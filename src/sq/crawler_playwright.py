import base64
import datetime
import glob
import json
import logging
import os
import re
import shutil
import time
from typing import Iterator, Optional
from xml.dom import minidom
from typing import Dict, Iterator, List, Optional
from isodate import duration_isoformat
from zenrows import ZenRowsClient
import random
from scrapy import Selector

from playwright.sync_api import Locator, Page
from curl_cffi import requests as crequests
import requests
from src import constants as c
from src.sq.constants import CabinClassCodeMapping, EndpointCabinClassCodeMapping
from src.exceptions import NoSearchResult, LoginFailed
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.proxy import PrivateProxyService
from src.schema import CashFee, Flight, FlightSegment
from src.types import SmartCabinClassType, SmartDateType
from src.utils import (
    convert_time_string_to_iso_format,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    extract_k_digits,
    extract_letters,
    parse_date,
    parse_time,
    sanitize_text,
)
from src.db import insert_target_headers, update_target_headers

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


SingaporeAirlineCredentials = c.Credentials[c.Airline.SingaporeAir]

class SingaporeAirPlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.SingaporeAir
    REQUIRED_LOGIN = True
    TARGET = 'singaporeair'
    HOME_PAGE_URL = "https://www.singaporeair.com/en_UK/us/home#/book/redeemflight"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials: List[c.AirlineCredential] = SingaporeAirlineCredentials.copy()
        self._compute_latest_user_data_dir()
        self.proxy_str = self.setup_proxy_str()

    def __del__(self):
        self._clean_outdate_user_data_dir()

    def _copytree(self, src, dst):
        """
        shutil.copytree didn't work as expected, use this simple command to
        preserve attributes/permissions of original folder
        """
        os.system("cp -a " + src + " " + dst)

    def _compute_latest_user_data_dir(self):
        """
        check if exist last user_data_dir belong to current user,
        if yes, clone this user_data_dir into new dir to keep last sesion session
        if no, return new latest empty dir
        """
        utc_now = datetime.datetime.utcnow().isoformat()
        pattern = re.sub("[@.:]", "-", f"user_data_dir_{self.username}*")
        user_data_dir_pattern = os.path.join(BASE_DIR, pattern)

        user_data_name = f"user_data_dir_{self.username}_{utc_now}"
        user_data_name = re.sub("[@.:]", "-", user_data_name)
        new_user_data_dir = os.path.join(BASE_DIR, user_data_name)
        # logger.info(f"new_user_data_name: {new_user_data_dir}")

        all_user_data_dirs = glob.glob(user_data_dir_pattern)
        # logger.info(f"all_user_data_dirs: {all_user_data_dirs}")

        if all_user_data_dirs:
            latest_user_data_dir = max(all_user_data_dirs, key=os.path.getmtime)
            logger.info(f"found latest user_data_dir: {latest_user_data_dir}")
            self._copytree(latest_user_data_dir, new_user_data_dir)
            time.sleep(5)

        self._user_data_dir = new_user_data_dir

    def _clean_outdate_user_data_dir(self):
        """
        Clean up all user_data_dir, only keep the latest one
        only delete user_data_dir of folder
        older than 15 minutes avoid to delete running chrome windows.
        (Assumed that each window has maxiumum 15 minutes to complete)
        """
        user_data_dir = os.path.join(BASE_DIR, re.sub("[@.:]", "-", f"user_data_dir_{self.username}*"))

        all_user_data_dirs = glob.glob(user_data_dir)
        MAX_COMPLETE_TIME = 60 * 15
        now = time.time()
        if all_user_data_dirs:
            last_user_data_dir = max(all_user_data_dirs, key=os.path.getmtime)
            logger.info(f"> cleanup oudate user_data_dir except for latest one: " f"{last_user_data_dir}")
            for user_data_dir in all_user_data_dirs:
                try:
                    if user_data_dir == last_user_data_dir:
                        continue
                    if os.path.getmtime(user_data_dir) < now - MAX_COMPLETE_TIME:
                        logger.info(
                            f"> cleanup oudate folder older than {(MAX_COMPLETE_TIME/60)}m user_data_dir: "
                            f"{user_data_dir}"
                        )
                        shutil.rmtree(user_data_dir)
                except Exception:
                    pass

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-us",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }

    def setup_proxy_str(self):
        # proxy_user = "spyc5m5gbs"
        # proxy_pass = "puFNdLvkx6Wcn6h6p8"
        # proxy_host = "us.smartproxy.com"
        # proxy_port = "10001"
        
        # proxy = self.get_private_proxy()
        # proxy_host = proxy.get('ip')  # rotating proxy or host
        # proxy_port = int(proxy.get('port'))  # port
        # proxy_user = proxy.get('user')  # username
        # proxy_pass = proxy.get('pwd')  # password
        
        proxy_user = "ihgproxy1"
        proxy_pass = "ihgproxy1234_country-us"
        proxy_host = "geo.iproyal.com"
        proxy_port = "12321"
        
        proxy_attr = {
            "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
            "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
        }
        return proxy_attr
    
    def _close_cookie_popup(self, page):
        try:
            cookie = page.locator("button.dwc--SiaCookie__PopupBtn")
            cookie.wait_for(timeout=1000)
            page.click("button.dwc--SiaCookie__PopupBtn")
            logger.info("clicked accept cookie popup")
        except Exception as e:
            logger.error(f"click accept cookie popup error: {e}")
            pass

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        self.origin = origin

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        self.destination = destination

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        credential = random.choice(self.credentials)

        try:
            profile = page.locator('xpath=//user-panel/div[@class="dwc--UserPanel__LoggedInUser"]')
            profile.wait_for(timeout=20000)
            need_login = False
        except Exception as e:
            logger.error(f"need to login exeption: {e}")
            need_login = True

        if need_login:
            self._close_cookie_popup(page)

            page.click("button.kf-log-in-container__button")
            time.sleep(10)
            self.human_typing(page, page.locator('input[name="krisflyernumber"]'), credential.username)
            time.sleep(2)
            self.human_typing(page, page.locator('input[name="password"]'), credential.password)
            time.sleep(1)
            page.click('label[for="kf-login-remember"]')
            time.sleep(1)

            page.click("button.dwc--SiaLogin__ButtonLogin")
            time.sleep(2)

        try:
            profile = page.locator('xpath=//user-panel/div[@class="dwc--UserPanel__LoggedInUser"]')
            profile.wait_for(timeout=120000)
            logger.info(f"Login Succeed!")
        except Exception as e:
            raise LoginFailed(airline=self.AIRLINE)

    def extract_flight_detail(
        self,
        flight_data: Dict,
        flight_dictionary: Dict,
    ) -> List[FlightSegment]:
        logger.info(f"{self.AIRLINE.value}: Extracting Flight Details...")
        flight_segments: List[FlightSegment] = []

        for segment_index, segment in enumerate(flight_data["legs"]):
            try:
                logger.info(f"{self.AIRLINE.value}: Retrieving segment info => index: {segment_index}...")
                if len(flight_data["legs"]) > segment_index+1:
                    connection_time = flight_data["legs"][segment_index+1].get("layoverDuration", 0)
                else:
                    connection_time = 0

                segment_origin = segment["originAirportCode"]
                segment_destination = segment["destinationAirportCode"]
                segment_departure_datetime = segment["departureDateTime"]
                segment_departure_datetime = datetime.datetime.fromisoformat(segment_departure_datetime)
                segment_arrival_datetime = segment["arrivalDateTime"]
                segment_arrival_datetime = datetime.datetime.fromisoformat(segment_arrival_datetime)
                aircraft_id = segment["aircraftCode"]
                segment_aircraft = flight_dictionary["aircraft"][aircraft_id]
                segment_carrier = segment["carrierCode"]
                segment_flight_number = segment["flightNumber"]
                if not segment_carrier:
                    segment_carrier = segment.get("marketingAirlineCode", None)
                segment_duration = segment["flightDuration"]

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
                        duration=duration_isoformat(datetime.timedelta(milliseconds=segment_duration)),
                        layover_time=duration_isoformat(datetime.timedelta(milliseconds=connection_time))
                        if connection_time
                        else None,
                    )
                )
            except Exception as err:
                logger.info(f"{self.AIRLINE.value}: ERR - {err}")

        return flight_segments

    def extract_sub_classes_points(
        self, flight_data, miles, departure_date_time: str, session, index, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Optional[Dict[str, dict]]:
        logger.info(f"{self.AIRLINE.value}: Extracting Sub Sub Classes points...")
        points_by_fare_names: Dict[str, dict] = {}
        
        try:
            miles_codes = flight_data["legs"][0]["cabinClassAvailability"]
            for miles_code in miles_codes:
                if miles_code.get('numberOfSeats', None) or miles_code.get('status', None):
                    selling_class_code = miles_code["sellingClass"]
                    for miles_selling_class in miles["sellingClass"]:
                        if miles_selling_class["code"] == selling_class_code:
                            fare_name = CabinClassCodeMapping[cabin_class] + ' ' + miles_selling_class["description"]
                            
                            fare_details = self.get_fare_details(index, miles_code, miles_selling_class, departure_date_time, session)
                            print("=========================================================================")
                            print("fare_details ==================>", fare_details)
                            
                            try:
                                currency = fare_details["bookingSummary"]["currency"]
                            except KeyError:
                                currency = None

                            try:
                                amount = fare_details["bookingSummary"]["taxTotal"]
                            except KeyError:
                                amount = None
                            
                            points_by_fare_names[fare_name] = {
                                "points": miles_selling_class["miles"],
                                "fare_brand_name": miles_selling_class["description"],
                                "cash_fee": CashFee(currency=currency, amount=amount)
                            }
                index += 1

        except Exception as e:
            logger.info(f"{self.AIRLINE.value}: extract_sub_classes_points exception: {e}")
            import traceback
            traceback.print_exc()

        return points_by_fare_names
    
    def get_fare_details(self, index, miles_code, miles_selling_class, departure_date_time, sess):
        try:
            isWaitListed = bool(miles_code.get('status'))
            
            data = {
                "selectedOnwardSegments": [
                    {
                        "sellingClass": miles_code["sellingClass"],
                        "sellingClassDescription": miles_selling_class["description"],
                        "segmentId": index,
                        "depatureDateTime": departure_date_time,
                        "waitListed": isWaitListed,
                        "originAirportCode": self.origin,
                        "destinationAirportCode": self.destination
                    }
                ],
                "selectedReturnSegments": []
            }
            
            response = sess.post(
                'https://www.singaporeair.com/redemption/getFare.form',
                impersonate="chrome124",
                proxies=self.proxy_str,
                headers=sess.headers,
                json=data,
                timeout=30 
            )
            
            time.sleep(random.uniform(1.13,1.5))
            
            response.raise_for_status() 
            
            fare_details = json.loads(response.text)
            return fare_details

        except Exception as e:
            logger.error(f"Error getting fare details: {e}")
            return None

    def fetch_data(
        self, cookies: str, departureMonth: str, cabin_class, session
    ) -> Optional[Dict[str, dict]]:
        try:
            cabin_code = EndpointCabinClassCodeMapping[cabin_class]

            # headers = {
            #     'authority': 'www.singaporeair.com',
            #     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            #     'accept-language': 'en-US,en;q=0.9,pt;q=0.7',
            #     'cache-control': 'max-age=0',
            #     'content-type': 'application/x-www-form-urlencoded',
            #     'cookie': cookies,
            #     'origin': 'https://www.singaporeair.com',
            #     'referer': 'https://www.singaporeair.com/en_UK/us/home',
            #     'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            #     'sec-ch-ua-mobile': '?0',
            #     'sec-ch-ua-platform': '"Windows"',
            #     'sec-fetch-dest': 'document',
            #     'sec-fetch-mode': 'navigate',
            #     'sec-fetch-site': 'same-origin',
            #     'sec-fetch-user': '?1',
            #     'upgrade-insecure-requests': '1',
            #     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            # }
            
            data = {
                '_payByMiles': 'on',
                'payByMiles': 'true',
                'fromHomePage': 'true',
                'orbOrigin': self.origin,
                'orbDestination': self.destination,
                '_tripType': 'on',
                'tripType': 'O',
                'departureMonth': departureMonth,
                'returnMonth': '',
                'cabinClass': cabin_code,
                'numOfAdults': '1',
                'numOfChildren': '0',
                'numOfInfants': '0',
                'flowIdentifier': 'redemptionBooking',
                '_eventId_flightSearchEvent': '',
                'isLoggedInUser': 'true',
                'numOfChildrenNominees': '1',
                'numOfAdultNominees': '1',
                'flexibleDates': 'off',
            }

            client = ZenRowsClient(c.ZENROWS_API_KEY)
            params = {"premium_proxy":"true"}
            for i in range(3):
                # response = client.post(
                #     'https://www.singaporeair.com/redemption/searchFlight.form',
                #     headers=headers,
                #     params=params,
                #     data=data
                # )

                response = session.post(
                    'https://www.singaporeair.com/redemption/searchFlight.form',
                    impersonate="chrome124",
                    proxies=self.proxy_str,
                    # headers=session.headers,
                    data=data
                )

                print(f'>>> Zenrow Call #{i+1}: {response.status_code}')
                if response.status_code == 200 and 'pageData = ' in response.text:
                    page_data_content = response.text.split('pageData = ')[-1].split('var ajax_urls')[0]
                    page_data_content = page_data_content.strip().strip('; ')
                    page_data = json.loads(page_data_content)
                    return page_data
        except Exception as err:
            print(err)
        
    def parse_flights(
        self, page: Page, departure_date: datetime.date, cabin_class: c.CabinClass = c.CabinClass.Economy
    ) -> Iterator[Flight]:
        cookies = page.context.cookies()
        cookies_rec = insert_target_headers(cookies, self.TARGET)
        
        sess = crequests.Session(impersonate="chrome124", proxies=self.proxy_str)
        last_success_cookies_rec = []
        updated_cookies = []
        headers = {
            
            'authority': 'www.singaporeair.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9,pt;q=0.7',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.singaporeair.com',
            'referer': 'https://www.singaporeair.com/en_UK/us/home',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        sess.headers = headers
        departureMonth = datetime.datetime.strftime(departure_date, '%d/%m/%Y')
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
        
        for cabin_klass in all_cabins:
            cookies_dict = {cookie['name']:cookie['value'] for cookie in cookies}
            new_cookies_dict = {k:v for k,v in sess.cookies.items()}
            
            cookies_dict.update(new_cookies_dict)
            cookie_str = "; ".join([f"{k}={v}" for k,v in cookies_dict.items()])
            headers["cookie"] = cookie_str
            flights_data = self.fetch_data(cookie_str, departureMonth, cabin_klass, sess)

            if not flights_data:
                if len(all_cabins) > 1:
                    continue
                raise NoSearchResult(airline=self.AIRLINE, reason="Search Failed!")

            # print("flights_data =====>", flights_data)
            # with open(f"HERE--destination-{cabin_class.value}.json", "w") as f:
            #     json.dump(flights_data, f, indent=2)
            # time.sleep(100)
            try: 
                flights = flights_data["flightSearch"]["response"]["data"]["flights"][0]["segments"]
                miles = flights_data["flightSearch"]["response"]["data"]["miles"]
                dictionary = flights_data["flightSearch"]["response"]["dictionary"]
            except (KeyError, IndexError):
                if len(all_cabins) > 1:
                    continue
                raise NoSearchResult(airline=self.AIRLINE, reason="NO FLIGHTS FOUND!")

            
            logger.info(f"{self.AIRLINE.value}: Found {len(flights)} flights...")
            for index, flight_search_result in enumerate(flights):
                logger.info(f"{self.AIRLINE.value}: Retrieving the detail of search item for cabin {cabin_klass.value} => index: {index}...")


                try:
                    segments = self.extract_flight_detail(flight_search_result, dictionary)
                except Exception as e:
                    raise e
                
                departure_date_time = segments[0].departure_date + " " + segments[0].departure_time
                
                points_by_fare_names = self.extract_sub_classes_points(flight_search_result, miles, departure_date_time, sess, index, cabin_klass)
                if not points_by_fare_names:
                    continue
                
                duration = flight_search_result["tripDuration"]

                for fare_name, points_and_cash in points_by_fare_names.items():
                    if not segments:
                        continue
                    flight = Flight(
                        airline=str(self.AIRLINE.value),
                        origin=segments[0].origin,
                        destination=segments[-1].destination,
                        cabin_class=str(cabin_klass.value),
                        airline_cabin_class=fare_name,
                        fare_brand_name=points_and_cash["fare_brand_name"],
                        points=points_and_cash["points"],
                        cash_fee=points_and_cash["cash_fee"],
                        segments=segments,
                        duration=duration_isoformat(datetime.timedelta(milliseconds=duration)),
                    )
                    yield flight
                    
                    new_cookies_dict = {k:v for k,v in sess.cookies.items()}
                    cookies_dict.update(new_cookies_dict)
                    updated_cookies = [{"name": k, "value": v} for k,v in cookies_dict.items()]
                    last_success_cookies_rec = [cookies_rec.inserted_id, updated_cookies]
                    
            time.sleep(random.uniform(1.5,3.2))
            
        if last_success_cookies_rec:
            _id, updated_cookies = last_success_cookies_rec
            update_target_headers(_id, {"headers": updated_cookies}, self.TARGET)


if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = SingaporeAirPlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=10, day=17)

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

    run("JFK", "SGN", c.CabinClass.All)
    # run("SFO", "BKK", c.CabinClass.All)
    # run("SIN", "LHR", c.CabinClass.Economy)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
