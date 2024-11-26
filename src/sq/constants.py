# flake8: noqa
from src.constants import CabinClass


CabinClassCodeMapping = {
    CabinClass.Economy: "ECONOMY",
    CabinClass.PremiumEconomy: "PREMIUM ECONOMY",
    CabinClass.Business: "BUSINESS",
    CabinClass.First: "First/Suites",
}

EndpointCabinClassCodeMapping = {
    CabinClass.Economy: "Y",
    CabinClass.PremiumEconomy: "S",
    CabinClass.Business: "J",
    CabinClass.First: "F",
}