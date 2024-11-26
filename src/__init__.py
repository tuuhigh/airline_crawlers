from .aa.crawler import AmericanAirlineCrawler
from .ac.crawler import AirCanadaCrawler
from .af.crawler import AirFranceCrawler
from .constants import Airline
from .dl.crawler import DeltaAirlineCrawler
from .ha.crawler import HawaiianAirCrawler
from .ua.crawler import UnitedAirlineCrawler
from .vs.crawler import VirginAtlanticCrawler
from .ak.crawler import AlaskaCrawler
from .b6.crawler import JetBlueCrawler
from .sq.crawler import SingaporeAirCrawler
from .cx.crawler import CathayPacificCrawler
from .ek.crawler import EmiratesAirCrawler
from .av.crawler import AviancaAirCrawler
from .tk.crawler import TurkishAirCrawler
from .ba.crawler import BritishAirCrawler

Crawlers = {
    Airline.AmericanAirline: AmericanAirlineCrawler,
    Airline.AirCanada: AirCanadaCrawler,
    Airline.AirFrance: AirFranceCrawler,
    Airline.DeltaAirline: DeltaAirlineCrawler,
    Airline.HawaiianAirline: HawaiianAirCrawler,
    Airline.UnitedAirline: UnitedAirlineCrawler,
    Airline.VirginAtlantic: VirginAtlanticCrawler,
    Airline.Alaska: AlaskaCrawler,
    Airline.JetBlue: JetBlueCrawler,
    Airline.SingaporeAir: SingaporeAirCrawler,
    Airline.CathayPacific: CathayPacificCrawler,
    Airline.Emirates: EmiratesAirCrawler,
    Airline.Avianca: AviancaAirCrawler,
    Airline.Turkish: TurkishAirCrawler,
    Airline.BritishAir: BritishAirCrawler,
}
