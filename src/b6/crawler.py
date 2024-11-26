from src.b6.crawler_multilogin import JetBlueMultiloginCrawler
from src.b6.crawler_zenrow_xhr import JetBlueZenrowXHRCrawler
from src.b6.crawler_requests import JetBlueRequestsCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class JetBlueCrawler(AirlineCrawler):
    AIRLINE = Airline.JetBlue
    CRAWLERS = [
        JetBlueRequestsCrawler,
        JetBlueZenrowXHRCrawler,
        JetBlueMultiloginCrawler,
    ]
