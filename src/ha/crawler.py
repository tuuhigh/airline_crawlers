from src.ha.crawler_playwright import HawaiianPlaywrightCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class HawaiianAirCrawler(AirlineCrawler):
    AIRLINE = Airline.HawaiianAirline
    CRAWLERS = [HawaiianPlaywrightCrawler]
