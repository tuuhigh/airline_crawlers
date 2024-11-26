from src.constants import CabinClass

CabinClassCodeMapping = {
    CabinClass.Economy: ["MAIN", "REFUNDABLE_MAIN"],
    CabinClass.PremiumEconomy: ["REFUNDABLE_PARTNER_PREMIUM", "PREMIUM"],
    CabinClass.Business: ["REFUNDABLE_PARTNER_BUSINESS", "BUSINESS"],
    CabinClass.First: ["FIRST", "REFUNDABLE_FIRST"],
}
AirlineCabinClassCodeMapping = {
    "REFUNDABLE_MAIN": "Refundable Main",
    "MAIN": "Main",
    "REFUNDABLE_FIRST": "Refundable First",
    "First": "First Class",
    "REFUNDABLE_PARTNER_PREMIUM": "Refundable Partner Premium",
    "PREMIUM": "Premium",
    "REFUNDABLE_PARTNER_BUSINESS": "Refundable Partner Business",
    "BUSINESS": "Business",
}
