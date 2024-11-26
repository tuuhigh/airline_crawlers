from src.sq.crawler_playwright import SingaporeAirPlaywrightCrawler
from src.sq.crawler_requests import SingaporeAirRequestCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class SingaporeAirCrawler(AirlineCrawler):
    AIRLINE = Airline.SingaporeAir
    CRAWLERS = [
        SingaporeAirRequestCrawler,
        SingaporeAirPlaywrightCrawler,
        SingaporeAirPlaywrightCrawler
    ]
