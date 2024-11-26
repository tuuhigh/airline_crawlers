from src.constants import CabinClass

CabinClassCodeMapping = {
    CabinClass.Economy: "economy class",
    CabinClass.PremiumEconomy: "premium economy",
    CabinClass.Business: "business class",
    CabinClass.First: "first class",
}
CabinClassCodeMappingForHybrid = {
    CabinClass.Economy: ["ECONOMY_REDEMPTION", "BLUE", "BLUE_EXTRA", "BLUE_REFUNDABLE", "BLUE_EXTRA_REFUNDABLE"],
    CabinClass.PremiumEconomy: [],
    CabinClass.Business: ["MINT_REFUNDABLE", "MINT"],
    CabinClass.First: [],
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
