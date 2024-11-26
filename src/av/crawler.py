from src.av.crawler_playwright import AviancaPlaywrightCrawler
from src.av.crawler_hybrid import AviancaAirlineHybridCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class AviancaAirCrawler(AirlineCrawler):
    AIRLINE = Airline.Avianca
    CRAWLERS = [
        AviancaAirlineHybridCrawler, 
        AviancaPlaywrightCrawler
    ]
