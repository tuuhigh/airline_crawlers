from src.ek.crawler_playwright import EmiratesPlaywrightCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class EmiratesAirCrawler(AirlineCrawler):
    AIRLINE = Airline.Emirates
    CRAWLERS = [EmiratesPlaywrightCrawler]
