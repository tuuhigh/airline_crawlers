# flake8: noqa
from src.constants import CabinClass


CabinClassCodeMapping = {
    CabinClass.Economy: "ECONOMY",
    CabinClass.PremiumEconomy: "PREMIUM ECONOMY",
    CabinClass.Business: "BUSINESS",
    CabinClass.First: "First",
}

EndpointCabinClassCodeMapping = {
    CabinClass.Economy: "M",
    CabinClass.PremiumEconomy: "W",
    CabinClass.Business: "C",
    CabinClass.First: "F",
}