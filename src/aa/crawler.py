from src.aa.crawler_requests import AmericanAirlineRequestsBasedCrawler
from src.aa.crawler_zenrow_requests import AmericanAirlineZenrowRequestsCrawler
from src.aa.crawler_zenrow_xhr import AmericanAirlineZenrowXHRCrawler
from src.base import AirlineCrawler
from src.constants import Airline


class AmericanAirlineCrawler(AirlineCrawler):
    AIRLINE = Airline.AmericanAirline
    CRAWLERS = [
        AmericanAirlineRequestsBasedCrawler, 
        AmericanAirlineZenrowXHRCrawler,
        AmericanAirlineZenrowRequestsCrawler
    ]


if __name__ == "__main__":
    import datetime
    import json
    import time
    from dataclasses import asdict

    from src.constants import CabinClass

    def run(origin, destination, cabin_class, adults):
        try:
            start_time = time.perf_counter()
            crawler = AmericanAirlineCrawler()
            # departure_date = datetime.date.today() + datetime.timedelta(days=14)
            departure_date = datetime.date(year=2024, month=11, day=24)
            flights = list(
                crawler.run(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    cabin_class=cabin_class,
                    adults=adults,
                )
            )
            end_time = time.perf_counter()

            if flights:
                with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                    json.dump([asdict(flight) for flight in flights], f, indent=2)
            else:
                print("No result....")
            print(f"It took {end_time - start_time} seconds.")
        except Exception as e:
            print(f">>>>>>>>>>>e: {e}")

    run("ORD", "LHR", CabinClass.PremiumEconomy, 1)
