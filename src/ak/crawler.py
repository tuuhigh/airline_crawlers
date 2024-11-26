from src.ak.crawler_zenrow_xhr import AlaskaZenrowXHRCrawler
from src.ak.crawler_multilogin import AlaskaMultiloginCrawler
from src.ak.crawler_playwright_wire import AlaskaPlaywrightWireCrawler
from src.ak.crawler_requests import AlaskaRequestsCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class AlaskaCrawler(AirlineCrawler):
    AIRLINE = Airline.Alaska
    CRAWLERS = [
        AlaskaRequestsCrawler,
        AlaskaZenrowXHRCrawler,
        AlaskaPlaywrightWireCrawler,
        # AlaskaMultiloginCrawler,
    ]
