from src.ba.crawler_playwright import BritishAirPlaywrightCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class BritishAirCrawler(AirlineCrawler):
    AIRLINE = Airline.BritishAir
    CRAWLERS = [BritishAirPlaywrightCrawler]
