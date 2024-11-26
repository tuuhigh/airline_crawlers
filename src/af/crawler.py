from src.af.crawler_playwright import AirFrancePlaywrightCrawler
from src.af.crawler_engineo import AFEngineoCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class AirFranceCrawler(AirlineCrawler):
    AIRLINE = Airline.AirFrance
    CRAWLERS = [AFEngineoCrawler]
