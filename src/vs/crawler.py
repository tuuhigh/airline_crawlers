from src.base import AirlineCrawler
from src.constants import Airline

# from src.vs.crawler_selenium import VirginAtlanticSeleniumBasedCrawler
from src.vs.crawler_zenrow_xhr import VirginAtlanticZenrowXHRCrawler
from src.vs.crawler_playwright_wire import VirginAtlanticPlaywrightWireCrawler
from src.vs.crawler_requests import VirginAtlanticRequestsCrawler

class VirginAtlanticCrawler(AirlineCrawler):
    AIRLINE = Airline.VirginAtlantic
    CRAWLERS = [
        VirginAtlanticRequestsCrawler,
        # VirginAtlanticZenrowXHRCrawler,
        VirginAtlanticPlaywrightWireCrawler,
        VirginAtlanticRequestsCrawler,
    ]
