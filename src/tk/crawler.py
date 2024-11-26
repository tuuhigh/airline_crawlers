from src.tk.crawler_playwright import TurkishPlaywrightCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class TurkishAirCrawler(AirlineCrawler):
    AIRLINE = Airline.Turkish
    CRAWLERS = [TurkishPlaywrightCrawler]
