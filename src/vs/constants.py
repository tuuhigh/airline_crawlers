from src.constants import CabinClass

CabinClassCodeMapping = {
    CabinClass.Economy: "CL",
    CabinClass.PremiumEconomy: "PE",
    CabinClass.Business: "UP",
    CabinClass.First: "FS",
}

CabinClassCodeMappingForHybrid = {
    CabinClass.Economy: "1",
    CabinClass.PremiumEconomy: "2",
    CabinClass.Business: "3",
}
AirlineCabinClassCodeMapping = {
    "1": "Economy Classic",
    "2": "Premium",
    "3": "Upper Class",
}