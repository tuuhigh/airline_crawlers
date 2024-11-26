import datetime
import logging
import os
import random
import re
import shutil
import time
from typing import Iterator

# from playwright_stealth import stealth_sync
from undetected_playwright.sync_api import Locator, Page
from undetected_playwright.sync_api import Playwright as SyncPlaywright
from undetected_playwright.sync_api import sync_playwright

from src import constants as c
from src.base import WebBrowserBasedAirlineCrawler
from src.schema import Flight
from src.types import SmartCabinClassType

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger(__name__)


class PlaywrightBaseAirlineCrawler(WebBrowserBasedAirlineCrawler):
    WEB_RTC_PATH = os.path.join(BASE_DIR, "webrtc_addon")
    BLOCK_RESOURCE = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utc_now = datetime.datetime.utcnow().isoformat().replace(":", "_")
        self._user_data_dir = os.path.join(BASE_DIR, f"{self.AIRLINE.value}_user_data_dir_{utc_now}")

    def __del__(self):
        super().__del__()
        if self._user_data_dir:
            logger.info(f"Removing _user_data_dir {self._user_data_dir}...")
            shutil.rmtree(self._user_data_dir, ignore_errors=True)

    @staticmethod
    def human_typing(page: Page, element: Locator, text: str, clear_flag=True, speed=(0.002, 0.005)):
        element.focus()
        if clear_flag:
            element.select_text()
            page.keyboard.press("Delete")
        for character in text:
            time.sleep(random.uniform(*speed))
            page.keyboard.press(character)

    @staticmethod
    def get_text(locator=None, **options):
        """
        options: timeout

        """
        options.setdefault("timeout", 100)
        try:
            if locator:
                content = locator.text_content(**options)
                if content:
                    return re.sub(r"\s+", " ", content).strip()
        except Exception:
            pass
        return ""

    def get_proxy(self):
        """
        To be inherited in child class to get proper proxy type,
        return default proxy value
        """
        # proxy_user = "ihgproxy1"
        # proxy_pass = "ihgproxy1234_country-us"
        # proxy_host = "geo.iproyal.com"
        # proxy_port = "12321"

        return random.choice([{
                "ip": "geo.iproyal.com",
                "port": "12321",
                "user": "ihgproxy1",
                # "pwd": "ihgproxy1234_country-us",
                "pwd": "ihgproxy1234_region-northamerica",
            },
            # {
            #     'ip': 'gate.smartproxy.com',
            #     'port': '7000',
            #     'user': 'tempUserx81kdh2',
            #     'pwd': 'ae4U4wqfcRiw_Xc2M1'
            # }
            ]
        )

    def get_user_agent(self):
        """
        To be inherited for specific airline
        """
        version1 = random.choice(range(124, 130))
        flatform = random.choice([
            "(Macintosh; Intel Mac OS X 10_15_7)",
            "(Macintosh; Intel Mac OS X 10_15_3)",
            "(Windows NT 10.0; Win64; x64)"
        ])
        user_agent = f"Mozilla/5.0 {flatform} AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version1}.0.0.0 Safari/537.36"
        return user_agent
            
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
            # channel="chrome",
            args=args,
            proxy=proxy,
            user_data_dir=self._user_data_dir,
            headless=False,
            slow_mo=100,  # slow down step as human behavior,
            timezone_id="America/New_York",
            geolocation={
                "latitude": 40.71427,
                "longitude": -74.00597,
                "accuracy": 90,
            },
            user_agent=user_agent
        )
        browser.set_default_navigation_timeout(200 * 1000)
        browser.clear_cookies()
        return browser

    def parse_flights(self, page, departure_date: datetime.date, cabin_class: c.CabinClass) -> Iterator[Flight]:
        pass

    @staticmethod
    def intercept_route(route):
        """intercept all requests and abort blocked ones"""
        if route.request.resource_type in c.BLOCK_RESOURCE_TYPES:
            # print(f'blocking background resource {route.request} blocked type "{route.request.resource_type}"')
            return route.abort()
        if any(key in route.request.url for key in c.BLOCK_RESOURCE_NAMES):
            # print(f"blocking background resource {route.request} blocked name {route.request.url}")
            return route.abort()
        return route.continue_()

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: SmartCabinClassType = c.CabinClass.Economy,
        adults: int = 1,
        **kwargs
    ) -> Iterator[Flight]:
        self.start_virtual_display()
        with sync_playwright() as p:
            browser = self.setup_driver(playwright=p)
            page = browser.new_page()
            # enable intercepting for this page, **/* stands for all requests
            if self.BLOCK_RESOURCE:
                logger.info(f"Blocking resource...")
                page.route("**/*", self.intercept_route)
            # stealth_sync(page)
            # STARTER_URL = "https://app.multiloginapp.com/WhatIsMyIP"
            # page.goto(STARTER_URL)
            # time.sleep(5)
        
            logger.info(f"Visiting {self.home_page_url}...")
            page.goto(self.home_page_url, timeout=120000)
            page.wait_for_load_state()
            self.search(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                cabin_class=cabin_class,
                adults=adults,
                username=self.username,
                password=self.password,
                page=page,
            )
            try:
                for flight in self.parse_flights(page, departure_date, cabin_class):
                    yield flight
            except Exception as e:
                raise e
            finally:
                browser.close()
