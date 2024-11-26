from src.cx.crawler_multilogin import CathayPacificMultiloginCrawler
from src.cx.crawler_playwright import CathayPacificPlaywrightCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class CathayPacificCrawler(AirlineCrawler):
    AIRLINE = Airline.CathayPacific
    CRAWLERS = [
        CathayPacificPlaywrightCrawler,
        CathayPacificMultiloginCrawler
    ]
