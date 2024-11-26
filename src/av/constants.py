# flake8: noqa
from src.constants import CabinClass


CabinClassCodeMapping = {
    CabinClass.Economy: "ECONOMY",
    CabinClass.PremiumEconomy: "PREMIUM ECONOMY",
    CabinClass.Business: "BUSINESS",
    CabinClass.First: "First/Suites",
}

CabinClassCodeIDMapping = {
    CabinClass.Economy: 1,
    CabinClass.PremiumEconomy: 1,
    CabinClass.Business: 2,
    CabinClass.First: 2,
}

CabinClassCodeTypeMapping = {
    "B0": "basic",
    "B2": "classic",
    "B3": "flex",
}
