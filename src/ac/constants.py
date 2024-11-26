from src.constants import CabinClass

CabinClassCodeMapping = {
    CabinClass.Economy: "economy class",
    CabinClass.PremiumEconomy: "premium economy",
    CabinClass.Business: "business class",
    CabinClass.First: "first class",
}
CabinClassCodeMappingForHybrid = {
    CabinClass.Economy: "eco",
    CabinClass.PremiumEconomy: "ecoPremium",
    CabinClass.Business: "business",
    CabinClass.First: "first",
}
AirlineCabinClassCodeMapping = {
    "STANDARD": "Standard Reward",
    "FLEX": "Flex Reward",
    "LATITUDE": "Latitude Reward",
    "PYFLEX": "Lowest Reward",
    "PYLOW": "Flexible Reward",
    "EXECFLEX": "Lowest Reward",
    "EXECLOW": "Flexible Reward",
}
AirlineCabinClass = ""
