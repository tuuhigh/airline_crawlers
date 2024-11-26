from src.base import AirlineCrawler
from src.constants import Airline
from src.dl.crawler_playwright import DeltaAirlinePlaywrightCrawler

# from src.dl.crawler_selenium import DeltaAirlineSeleniumBasedCrawler
from src.dl.crawler_zenrow import DeltaAirlineZenrowCrawler
from src.dl.crawler_hybrid import DeltaAirlineHybridCrawler
from src.dl.crawler_requests import DeltaAirlineRequestsCrawler
from src.dl.crawler_playwright_wire import DeltaAirlinePlaywrightWireCrawler


class DeltaAirlineCrawler(AirlineCrawler):
    AIRLINE = Airline.DeltaAirline
    CRAWLERS = [
        DeltaAirlineRequestsCrawler,
        DeltaAirlineHybridCrawler, 
        DeltaAirlinePlaywrightWireCrawler,
    ]
