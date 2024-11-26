from src.base import AirlineCrawler
from src.constants import Airline

# from src.ua.crawler_selenium import UnitedAirlineSeleniumBasedCrawler
from src.ua.crawler_zenrow import UnitedAirlineZenrowCrawler
from src.ua.crawler_multilogin_wire import UnitedAirlineMultiloginWireCrawler
from src.ua.crawler_multilogin import UnitedAirlineMultiloginCrawler
from src.ua.crawler_playwright_wire import UnitedAirlinePlaywrightWireCrawler
from src.ua.crawler_requests import UnitedRequestsCrawler


class UnitedAirlineCrawler(AirlineCrawler):
    AIRLINE = Airline.UnitedAirline
    CRAWLERS = [
        UnitedRequestsCrawler,
        UnitedAirlinePlaywrightWireCrawler,
        UnitedAirlinePlaywrightWireCrawler,
        UnitedAirlineMultiloginCrawler,
        # UnitedAirlineMultiloginWireCrawler
    ]
