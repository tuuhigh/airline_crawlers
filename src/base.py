import datetime
import requests
import socket
import logging
import os
import random
import re
import shutil
import stat
import tempfile
import time
import traceback
from typing import Iterator, List, Optional

import undetected_chromedriver as uc
from pyvirtualdisplay import Display
from retry import retry
from seleniumwire import webdriver as webdriversw  # Import from seleniumwire
from selenium import webdriver as wd
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src import constants as c
from src.exceptions import (
    AirportNotSupported,
    CabinClassNotSelectable,
    CrawlerException,
    DepartureDateNotSelectable,
    DestinationNotSelectable,
    FlexibleDateNotSelectable,
    LocaleNotSelectable,
    LoginFailed,
    MileNotSelectable,
    NoSearchResult,
    OnewayNotSelectable,
    OriginNotSelectable,
    PassengerNotSelectable,
)
from src.proxy import PrivateProxyService, ProxyExtension
from src.schema import Flight
from src.types import SmartCabinClassType, SmartDateType
from src.utils import send_slack_message, get_random_port

logger = logging.getLogger(__name__)


def validate(
    airline: c.Airline,
    origin: str,
    destination: str,
    departure_date: datetime.date,
    cabin_class: c.CabinClass = c.CabinClass.Economy,
):
    if len(origin) != 3 or len(destination) != 3:
        return False
    if departure_date < datetime.date.today():
        return False
    if airline == c.Airline.VirginAtlantic and cabin_class == c.CabinClass.First:
        return False
    if airline == c.Airline.HawaiianAirline and cabin_class not in [c.CabinClass.Economy, c.CabinClass.Business, c.CabinClass.First, c.CabinClass.PremiumEconomy, c.CabinClass.All]:
        return False
    return True


class BaseAirlineCrawler:
    AIRLINE: Optional[c.Airline] = None
    NEED_VIRTUAL_DISPLAY: bool = False
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = None

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.proxy_service = PrivateProxyService()
        self.username = username
        self.password = password
        if self.username is None and self.password is None and self.AIRLINE in c.Credentials:
            credential: c.AirlineCredential = random.choice(c.Credentials[self.AIRLINE])
            self.username = credential.username
            self.password = credential.password

    def _run(
        self,
        origin: str,
        destination: str,
        departure_date: datetime.date,
        cabin_class: SmartCabinClassType = c.CabinClass.Economy,
        adults: int = 1,
        **kwargs
    ) -> Iterator[Flight]:
        pass

    def run(
        self,
        origin: str,
        destination: str,
        departure_date: SmartDateType,
        cabin_class: SmartCabinClassType = c.CabinClass.Economy,
        adults: int = 1,
        **kwargs
    ) -> Iterator[Flight]:
        if isinstance(cabin_class, str):
            cabin_class = c.CabinClass(cabin_class)

        if isinstance(departure_date, str):
            departure_date = datetime.date.fromisoformat(departure_date)

        is_validated = validate(self.AIRLINE, origin, destination, departure_date, cabin_class)
        if not is_validated:
            return []

        try:
            for flight in self._run(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                cabin_class=cabin_class,
                adults=adults,
                **kwargs
            ):
                yield flight
        except NoSearchResult as e:
            logger.error(f"{self.AIRLINE.value}: ({origin}-{destination})({departure_date.isoformat()}) {e.message}")
            return []

class MultiLoginAirlineCrawler(BaseAirlineCrawler):
    AIRLINE: Optional[c.Airline] = None
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered
    ML_AUTOMATION_TOKEN: str = ""
    QUICK_PROFILES_MLX_LAUNCHER = "https://launcher.mlx.yt:45001/api/v2/profile/quick"
    BLOCK_URLS = [
        'adzerk',
        'analytics',
        'cdn.api.twitter',
        'doubleclick',
        'exelator',
        'facebook',
        'fontawesome',
        'google',
        'google-analytics',
        'googletagmanager',
        "tiktok",
        'contentstack',
        'mozilla',
        'openh264',
        'adobedtm',
        'adobetarget',
        'bing',
        # 'pisano.com',
        # 'tags.tiqcdn.com'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_id = False
        self.init_quick_header()
    
    def init_quick_header(self):
        ML_AUTOMATION_TOKEN = random.choice([
            'eyJhbGciOiJIUzUxMiJ9.eyJicGRzLmJ1Y2tldCI6Im1seC1icGRzLXByb2QtZXUtMSIsImVtYWlsIjoiYW51anBhdGVsQG9keW5uLmNvbSIsImlzQXV0b21hdGlvbiI6dHJ1ZSwibWFjaGluZUlEIjoiIiwicHJvZHVjdElEIjoibXVsdGlsb2dpbiIsInNoYXJkSUQiOiJjYmUxMzgwMC1iYmFmLTRjOGYtODBiMy0xOTdmODk2Mzk0ZjIiLCJ1c2VySUQiOiI0YjNhZTc1OS03MzY2LTRjOGEtYTc0YS04NGM0ZGM0ZGMxZmIiLCJ2ZXJpZmllZCI6dHJ1ZSwid29ya3NwYWNlSUQiOiI0Njk1NTVhMC0wM2Q4LTRmNTYtOWE1OC1kOGM5ODlkMjA3NTYiLCJ3b3Jrc3BhY2VSb2xlIjoib3duZXIiLCJqdGkiOiI4ZjIzMjA1Ni04MDMyLTRmMmUtOTdiNS03OTA0MDEzNThkYTciLCJzdWIiOiJNTFgiLCJpc3MiOiI0YjNhZTc1OS03MzY2LTRjOGEtYTc0YS04NGM0ZGM0ZGMxZmIiLCJpYXQiOjE3MTE3MzIxNTQsImV4cCI6MjAzMzE0MDE1NH0.ITFgvwh-NJORiAMfUdSkYzVY2uWWYagGAMCsLf9oCYV7N12Y2YqSAa9_30UKMn2hZquGkmwwlaInSnFUyHnnEQ',
            'eyJhbGciOiJIUzUxMiJ9.eyJicGRzLmJ1Y2tldCI6Im1seC1icGRzLXByb2QtZXUtMSIsImVtYWlsIjoib2R5bm4uYWxlcnRAZ21haWwuY29tIiwiaXNBdXRvbWF0aW9uIjp0cnVlLCJtYWNoaW5lSUQiOiIiLCJwcm9kdWN0SUQiOiJsdCIsInNoYXJkSUQiOiJjYmUxMzgwMC1iYmFmLTRjOGYtODBiMy0xOTdmODk2Mzk0ZjIiLCJ1c2VySUQiOiIzZjgyYzJmNy00MTdkLTQwNTMtOTRiZC1iOGRkMGVjYjA3M2IiLCJ2ZXJpZmllZCI6dHJ1ZSwid29ya3NwYWNlSUQiOiI3NTYwMmIzNS0yZDkyLTRhMzQtYTI5YS01YzFlMTBiYzdkZmMiLCJ3b3Jrc3BhY2VSb2xlIjoib3duZXIiLCJqdGkiOiI2MjQxNzc0Zi02NjBkLTQyZTUtYmU3Yy0yMWM3MTczNzcwY2MiLCJzdWIiOiJNTFgiLCJpc3MiOiIzZjgyYzJmNy00MTdkLTQwNTMtOTRiZC1iOGRkMGVjYjA3M2IiLCJpYXQiOjE3MTUwMTU2MzUsImV4cCI6MjAzNjQyMzYzNX0.ADgmhoAjzIUPhSGntErQ4twAKHRN9hhadDxfzr6eTPFPGBbijTDppvzY8MRbxpOEwmgiTb-9vuYPWhVDnZIArQ'
        ])
        self.quick_header = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {ML_AUTOMATION_TOKEN}'
        }
        
    def get_proxy(self):
        """
        To be inherited in child class to get proper proxy type,
        return default proxy value
        """
    def get_proxy(self):
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
            {
                'ip': 'gate.smartproxy.com',
                'port': '7000',
                'user': 'tempUserx81kdh2',
                'pwd': 'ae4U4wqfcRiw_Xc2M1'
            }])

        # return {
        #     "ip": 'us.smartproxy.com',
        #     "port": '10001',
        #     "user": "spyc5m5gbs",
        #     "pwd": "puFNdLvkx6Wcn6h6p8",
        # }
        
    def quit_driver(self):
        quit_quick_profile = f"https://launcher.mlx.yt:45001/api/v1/profile/stop/p/{self.profile_id}"
        quit_response = requests.request('GET', quit_quick_profile, headers=self.quick_header)
        logger.info(f'Quit multilogin quick profile {self.profile_id}: Status code: {quit_response.status_code}')
            
    def setup_driver(self, use_selenium_wire=False):
        def interceptor(request):
            # Block PNG, JPEG and GIF images
            if request.path.endswith(('.png', '.jpg', '.gif')):
                request.abort()
            for block_url in self.BLOCK_URLS:
                if block_url in request.url:
                    request.abort()
                
        proxy = self.get_proxy()
        PROXY_HOST = proxy.get('ip')  # rotating proxy or host
        PROXY_PORT = int(proxy.get('port'))  # port
        PROXY_USER = proxy.get('user')  # username
        PROXY_PASS = proxy.get('pwd')  # password
        OS_TYPES = random.choice(['windows', 'macos'])

        browser_type = random.choice([
                                    'stealthfox',
                                    # 'mimic'
                                    ])

        mask_natural = random.choice(["mask", "real"])
        real_noise = random.choice(["real", "noise"])

        quick_payload = {
            "browser_type": browser_type,
            "name": "quick_profile",
            "os_type": OS_TYPES,
            "automation": "selenium",
            "proxy": {
                    "host": PROXY_HOST,
                    "type": "http",
                    "port": PROXY_PORT,
                    "username": PROXY_USER,
                    "password": PROXY_PASS
                },
            "parameters": {
                "fingerprint": {},
                "flags": {
                    "audio_masking": "mask",
                    "fonts_masking": "mask",
                    "geolocation_masking": "mask",
                    "geolocation_popup": "prompt",
                    "graphics_masking": "mask",
                    "graphics_noise": "mask",
                    "localization_masking": "mask",
                    "media_devices_masking": "mask",
                    "navigator_masking": "mask",
                    "ports_masking": "mask",
                    "screen_masking": "mask",
                    "timezone_masking": "mask",
                    "webrtc_masking": "mask",
                    "proxy_masking": "custom"
                    },
                "storage": {
                    "is_local": False,
                    "save_service_worker": True
                    },
                }
            }
        logger.info(f">>> Calling quick profile with header: {self.quick_header}")
        response = requests.post(url=self.QUICK_PROFILES_MLX_LAUNCHER, headers=self.quick_header,json=quick_payload)
        
        if response.status_code != 200:
            logger.error(f">>> Calling quick profile error: {response.text}")
            
        profile_port = response.json()["data"]["port"]
        self.profile_id = response.json()["data"]["id"]
        if browser_type == 'mimic':
            options = ChromiumOptions()
            # options.add_argument('--incognito')
        else:
            options = FirefoxOptions()
            if use_selenium_wire:
                options.set_preference('network.proxy.allow_hijacking_localhost', True)
            
        if use_selenium_wire:
            sw_address = socket.gethostbyname(socket.gethostname())
            sw_port = get_random_port()
            sw_options = {
                "auto_config": False,
                "addr": sw_address,
                "port": sw_port,
                'disable_encoding': True,
                "request_storage_base_dir": "/tmp",  # Use /tmp to store captured data
                'proxy': {
                    'http': 'http://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321',
                    'https': 'https://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321',
                    'no_proxy': 'http://ihgproxy1:ihgproxy1234_country-br,ca,cl,de,es,fr,gb,mx,za@geo.iproyal.com:12321'
                }
            }

            proxy = f"{sw_address}:{sw_port}"
            print(f">>>>>>> proxy: {proxy}")
            firefox_capabilities = webdriversw.DesiredCapabilities.FIREFOX
            firefox_capabilities['marionette'] = True
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": proxy,
                "sslProxy": proxy
            }
            driver = webdriversw.Remote(
                command_executor=f'http://127.0.0.1:{profile_port}',
                options=options,
                desired_capabilities=firefox_capabilities,
                # desired_capabilities=self.OPTIONS.to_capabilities(),
                seleniumwire_options=sw_options
            )

            driver.request_interceptor = interceptor
            return driver
        # Instantiate the remote webdriver with the quick profile port
        driver = wd.Remote(command_executor=f'http://127.0.0.1:{profile_port}', options=options)
        return driver
    
class RequestsBasedAirlineCrawler(BaseAirlineCrawler):
    AIRLINE: Optional[c.Airline] = None
    NEED_VIRTUAL_DISPLAY: bool = False
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Buffered


class WebBrowserBasedAirlineCrawler(BaseAirlineCrawler):
    HOME_PAGE_URL = ""
    AIRLINE: Optional[c.Airline] = None
    REQUIRED_LOGIN: bool = False
    NEED_VIRTUAL_DISPLAY: bool = True
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Streaming

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.virtual_display_configured = False
        self.display = None
        self.home_page_url = self.HOME_PAGE_URL

    def __del__(self):
        if self.display:
            logger.info("Stopping Virtual Display...")
            self.display.stop()

    @staticmethod
    def months_until_departure_date(departure_date: datetime.date):
        today = datetime.date.today()
        return (departure_date.year - today.year) * 12 + (departure_date.month - today.month)

    def start_virtual_display(self):
        if c.USE_VIRTUAL_DISPLAY and self.display is None:
            logger.info("Starting Virtual Display")
            self.display = Display(visible=False, size=(1920, 1200))
            self.display.start()

    def _select_locale(self, *args, **kwargs) -> None:
        pass

    def select_locale(self, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value}: Selecting locale...")
            self._select_locale(*args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected Locales")
        except Exception as e:
            raise LocaleNotSelectable(airline=self.AIRLINE, reason=f"{e}")

    def _select_miles(self, *args, **kwargs) -> None:
        pass
        # raise NotImplementedError("`_choose_miles` should be implemented")

    def select_miles(self, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value}: Selecting miles...")
            self._select_miles(*args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected miles")
        except Exception as e:
            raise MileNotSelectable(airline=self.AIRLINE, reason=f"{e}")

    def _select_flexible_dates(self, *args, **kwargs) -> None:
        pass

    def select_flexible_dates(self, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value}: Selecting flexible dates...")
            self._select_miles(*args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected flexible dates")
        except Exception as e:
            raise FlexibleDateNotSelectable(airline=self.AIRLINE, reason=f"{e}")

    def _select_oneway(self, *args, **kwargs) -> None:
        pass
        # raise NotImplementedError("`_choose_oneway` should be implemented")

    def select_oneway(self, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value}: Selecting one way...")
            self._select_oneway(*args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected one way")
        except Exception:
            raise OnewayNotSelectable(
                airline=self.AIRLINE,
            )

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        pass
        # raise NotImplementedError("`_choose_origin` should be implemented")

    def select_origin(self, origin: str, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value}: Selecting origin airport({origin})...")
            self._select_origin(origin, *args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected Origin: {origin}")
        except (AirportNotSupported, OriginNotSelectable) as e:
            raise e
        except NoSearchResult as e:
            raise e
        except Exception as e:
            raise OriginNotSelectable(airline=self.AIRLINE, airport=origin, reason=f"{e}")

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        pass
        # raise NotImplementedError("`_choose_destination` should be implemented")

    def select_destination(self, destination: str, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value} Selecting destination airport({destination})...")
            self._select_destination(destination, *args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected destination: {destination}")
        except AirportNotSupported as e:
            raise e
        except NoSearchResult as e:
            raise e
        except Exception as e:
            raise DestinationNotSelectable(airline=self.AIRLINE, airport=destination, reason=f"{e}")

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        pass
        # raise NotImplementedError("`_choose_destination` should be implemented")

    def select_date(self, departure_date: SmartDateType, *args, **kwargs) -> None:
        try:
            if isinstance(departure_date, str):
                departure_date = datetime.date.fromisoformat(departure_date)
            logger.info(f"{self.AIRLINE.value}: Selecting departure date({departure_date})...")
            self._select_date(departure_date, *args, **kwargs)
            logger.info(f"{self.AIRLINE.value}: Selected departure date({departure_date})")
        except Exception:
            raise DepartureDateNotSelectable(
                airline=self.AIRLINE,
                departure_date=departure_date,
            )

    def _select_cabin_class(self, cabin_class: c.CabinClass.Economy, *args, **kwargs) -> None:
        pass

    def select_cabin_class(self, cabin_class: c.CabinClass.Economy, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value} Selecting cabin class ({cabin_class})...")
            self._select_cabin_class(cabin_class, *args, **kwargs)
            logger.info(f"{self.AIRLINE.value} Selected cabin class ({cabin_class})...")
        except Exception as e:
            raise CabinClassNotSelectable(airline=self.AIRLINE, cabin_class=cabin_class, reason=f"{e}")

    def _select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        pass

    def select_passengers(self, adults: int = 1, *args, **kwargs) -> None:
        try:
            logger.info(f"{self.AIRLINE.value}: Selecting {adults} Passengers")
            self._select_passengers(adults, *args, **kwargs)
            logger.info(f"{self.AIRLINE.value} Selected {adults} Passengers")
        except Exception as e:
            raise PassengerNotSelectable(airline=self.AIRLINE, reason=f"{e}")

    def accept_cookie(self, *args, **kwargs):
        pass
        # raise NotImplementedError("`accept_cookie` should be implemented")

    def _submit(self, *args, **kwargs):
        pass
        # raise NotImplementedError("`_submit` should be implemented")

    def submit(self, *args, **kwargs):
        logger.info(f"{self.AIRLINE.value} Submitting...")
        self._submit(*args, **kwargs)

    def _login(self, *args, **kwargs):
        pass

    def login(self, *args, **kwargs):
        try:
            logger.info(f"{self.AIRLINE.value}: Logging into...")
            self._login(*args, **kwargs)
        except Exception as e:
            raise LoginFailed(airline=self.AIRLINE, reason=f"{e}")

    def check_page(self):
        pass

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: SmartDateType,
        cabin_class: c.CabinClass = c.CabinClass.Economy,
        adults: int = 1,
        *args,
        **kwargs,
    ) -> None:
        logger.info(f"{self.AIRLINE.value}: Searching...")
        if self.REQUIRED_LOGIN:
            self.login(*args, **kwargs)
        self.select_locale(*args, **kwargs)
        self.select_miles(*args, **kwargs)
        self.select_oneway(*args, **kwargs)
        self.select_passengers(adults, *args, **kwargs)
        self.select_origin(origin, *args, **kwargs)
        self.select_destination(destination, *args, **kwargs)
        self.select_date(departure_date, *args, **kwargs)
        self.select_flexible_dates(*args, **kwargs)
        self.select_cabin_class(cabin_class, *args, **kwargs)
        self.accept_cookie(*args, **kwargs)
        self.submit(*args, **kwargs)



class SeleniumBasedAirlineCrawler(WebBrowserBasedAirlineCrawler):
    def __init__(self):
        super().__init__()
        self._driver = None
        self._driver_dir = None
        self.proxy_service = None
        self.actions = None

    def setup_driver(self):
        self.start_virtual_display()
        logger.info("Setting Web Driver...")
        caps = DesiredCapabilities.CHROME
        caps["pageLoadStrategy"] = "eager"

        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--whitelisted-ips=''")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-xss-auditor")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        )
        prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.headless = False

        proxy = self.proxy_service.choose_proxy()
        proxy_extension = ProxyExtension(
            host=proxy.host,
            port=proxy.port,
            user=proxy.user,
            password=proxy.password,
        )

        chrome_options.add_argument(f"--load-extension={proxy_extension.directory}")

        driver_path = self.duplicate_undetected_driver()
        driver = uc.Chrome(options=chrome_options, desired_capabilities=caps, driver_executable_path=driver_path)

        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self._driver = driver
        logger.info("Driver is ready")
        return driver

    def quit_driver(self):
        if self.driver is not None:
            self.driver.quit()
            self._driver = None
            self.remove_duplicated_undetected_driver()

    def duplicate_undetected_driver(self) -> str:
        if c.CHROME_DRIVER_PATH:
            logger.info("Duplicating undetected driver")
            self._driver_dir = os.path.normpath(tempfile.mkdtemp())
            driver_path = os.path.join(self._driver_dir, "chromedriver")
            shutil.copyfile(c.CHROME_DRIVER_PATH, driver_path)
            logger.info(f"Duplicated at {driver_path}")
            driver_permission = os.stat(driver_path)
            os.chmod(driver_path, driver_permission.st_mode | stat.S_IEXEC)
            return driver_path

    def remove_duplicated_undetected_driver(self):
        if self._driver_dir:
            shutil.rmtree(self._driver_dir)
            logger.info("Deleted duplicated chrome driver")

    def save_screenshot(self, file_name):
        self.driver.save_screenshot(file_name)

    def move_mouse(self):
        if self.actions is None:
            self.actions = ActionChains(self.driver)
        # body_element = self.driver.find_element(By.TAG_NAME, "body")
        # self.actions.move_to_element(body_element).perform()
        self.actions.move_by_offset(random.randint(10, 500), random.randint(20, 500)).perform()

    @property
    def driver(self) -> Optional[WebDriver]:
        return self._driver

    def wait_until_presence(
        self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP
    ) -> Optional[WebElement]:
        return WebDriverWait(self.driver, timeout).until(ec.presence_of_element_located((by, identifier)))

    def wait_until_visible(
        self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP
    ) -> Optional[WebElement]:
        return WebDriverWait(self.driver, timeout).until(ec.visibility_of_element_located((by, identifier)))

    def wait_until_clickable(
        self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP
    ) -> Optional[WebElement]:
        return WebDriverWait(self.driver, timeout).until(ec.element_to_be_clickable((by, identifier)))

    def wait_until_all_visible(
        self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP
    ) -> List[WebElement]:
        return WebDriverWait(self.driver, timeout).until(ec.presence_of_all_elements_located((by, identifier)))

    def find_and_click_element(self, identifier: str, by: str = By.XPATH, from_element: Optional[WebElement] = None):
        if from_element:
            element = from_element.find_element(by=by, value=identifier)
        else:
            element = self.driver.find_element(by=by, value=identifier)
        self.scroll_and_click_element(element)

    def click_element(self, element: WebElement):
        self.driver.execute_script("arguments[0].click();", element)

    def scroll_to(self, element: WebElement):
        self.driver.execute_script("arguments[0].scrollIntoView(false);", element)

    def scroll_and_click_element(self, element: WebElement):
        self.driver.execute_script("arguments[0].scrollIntoView(false);", element)
        self.driver.execute_script("arguments[0].click();", element)

    def click_once_clickable(self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP):
        element = self.wait_until_clickable(identifier, by, timeout)
        self.scroll_and_click_element(element)

    def click_once_presence(self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP):
        element = self.wait_until_presence(identifier, by, timeout)
        self.click_element(element)

    def click_once_visible(self, identifier: str, by: str = By.XPATH, timeout: int = c.DEFAULT_SLEEP):
        element = self.wait_until_visible(identifier, by, timeout)
        self.click_element(element)

    def find_elements(self, identifier: str, by: str = By.XPATH, from_element: Optional[WebElement] = None):
        if from_element:
            return from_element.find_elements(by, identifier)
        else:
            return self.driver.find_elements(by, identifier)

    def find_element(self, identifier: str, by: str = By.XPATH, from_element: Optional[WebElement] = None):
        if from_element:
            return from_element.find_element(by, identifier)
        else:
            return self.driver.find_element(by, identifier)

    def get_text_from_element(self, identifier: str, by: str = By.XPATH, from_element: Optional[WebElement] = None):
        if from_element:
            element = from_element.find_element(by, identifier)
        else:
            element = self.driver.find_element(by, identifier)
        return self.get_text(element)

    @staticmethod
    def get_text(element: Optional[WebElement] = None):
        try:
            if element:
                content = element.get_attribute("textContent")
                if content:
                    return re.sub(r"\s+", " ", content).strip()
        except Exception:
            traceback.print_exc()
        return ""

    @staticmethod
    def human_typing(element: WebElement, text: str, speed=(0.2, 0.5)):
        for character in text:
            time.sleep(random.uniform(*speed))
            element.send_keys(character)

    def check_ip_address(self):
        self.driver.get("http://utilserver.privateproxy.me")
        element = self.wait_until_visible(
            by=By.CSS_SELECTOR,
            identifier="pre",
            timeout=c.HIGH_SLEEP,
        )
        logger.info(element.text)

    @retry(CrawlerException, tries=c.RETRY_COUNT)
    def run(
        self,
        origin: str,
        destination: str,
        departure_date: SmartDateType,
        cabin_class: SmartCabinClassType = c.CabinClass.Economy,
        adults: int = 1,
        **kwargs,
    ) -> Iterator[Flight]:
        if isinstance(cabin_class, str):
            cabin_class = c.CabinClass(cabin_class)

        if isinstance(departure_date, str):
            departure_date = datetime.date.fromisoformat(departure_date)

        is_validated = validate(self.AIRLINE, origin, destination, departure_date, cabin_class)
        if not is_validated:
            return []

        try:
            self.setup_driver()
            # self.check_ip_address()
            logger.info(f"{self.AIRLINE.value}: Go to {self.home_page_url}")
            self.driver.get(self.home_page_url)
            self.check_page()
            self.search(origin, destination, departure_date, cabin_class, adults)
            for flight in self._run(origin, destination, departure_date, cabin_class, adults, **kwargs):
                yield flight
        except (AirportNotSupported, NoSearchResult) as e:
            logger.error(f"{self.AIRLINE.value}: ({origin}-{destination})({departure_date.isoformat()}) {e.message}")
            return []
        except Exception as e:
            logger.error(f"{self.AIRLINE.value}: {e}")
            # self.save_screenshot("error.png")
            raise e
        finally:
            self.quit_driver()


class AirlineCrawler:
    AIRLINE: Optional[c.Airline] = None
    CRAWLERS = []

    def __init__(self):
        self._response_format = c.ResponseFormat.Buffered

    @property
    def response_format(self):
        return self._response_format

    def run(
        self,
        origin: str,
        destination: str,
        departure_date: SmartDateType,
        cabin_class: SmartCabinClassType = c.CabinClass.Economy,
        adults: int = 1,
        **kwargs
    ) -> Iterator[Flight]:
        if isinstance(cabin_class, str):
            cabin_class = c.CabinClass(cabin_class)

        if isinstance(departure_date, str):
            departure_date = datetime.date.fromisoformat(departure_date)

        is_validated = validate(self.AIRLINE, origin, destination, departure_date, cabin_class)
        if not is_validated:
            return []

        success = False
        tries = 0
        while not success:
            tries += 1
            if tries > 5:
                break
            logger.info(f"{self.AIRLINE.value}: ({origin}-{destination})({departure_date.isoformat()}) - tried {tries} times")
            for crawler_index, crawler_klass in enumerate(self.CRAWLERS):
                crawler = crawler_klass()
                try:
                    self._response_format = crawler.RESPONSE_FORMAT
                    for flight in crawler.run(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date,
                        cabin_class=cabin_class,
                        adults=adults,
                        **kwargs
                    ):
                        yield flight
                        
                    success = True
                except NoSearchResult as e:
                    logger.error(
                        f"{self.AIRLINE.value}: ({origin}-{destination})({departure_date.isoformat()}) {e.message}"
                    )
                    return []
                except Exception as e:
                    logger.error(f"{self.AIRLINE.value} - {origin}-{destination} - {departure_date} {crawler_index}th Crawler: {e}")
                    logger.error(traceback.format_exc())
                    send_slack_message(
                        slack_channel_name=c.SLACK_CHANNEL_NAME,
                        slack_webhook_url=c.SLACK_WEBHOOK_URL,
                        env=c.ENV,
                        airline=str(self.AIRLINE.value),
                        origin=origin,
                        destination=destination,
                        departure_date=f"{departure_date}",
                        cabin_class=str(cabin_class.value),
                        adults=adults,
                        headline=f"{crawler_index + 1}th {crawler.__class__.__name__}",
                        reason=traceback.format_exc(),
                    )
                else:
                    break