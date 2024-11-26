from src.ac.crawler_playwright import AirCanadaPlaywrightCrawler
from src.ac.crawler_playwright_wire import AirCanadaPlaywrightWireCrawler
from src.ac.crawler_selenium import AirCanadaSeleniumBasedCrawler
from src.ac.crawler_multilogin import AirCanadaMultiloginCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class AirCanadaCrawler(AirlineCrawler):
    AIRLINE = Airline.AirCanada
    CRAWLERS = [
        AirCanadaMultiloginCrawler,
        AirCanadaMultiloginCrawler,
        AirCanadaPlaywrightWireCrawler,
    ]


if __name__ == "__main__":
    import datetime
    import json
    import time
    from dataclasses import asdict

    from src.constants import CabinClass

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AirCanadaCrawler()
        # departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=2, day=15)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                cabin_class=cabin_class,
            )
        )
        end_time = time.perf_counter()

        if flights:
            with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    run("DFW", "JFK", CabinClass.Economy)
