from src.constants import CabinClass

CabinClassCodeMapping = {
    CabinClass.Economy: "MIN-ECONOMY-SURP-OR-DISP",
    CabinClass.PremiumEconomy: "ECO-PREMIUM-DISP",
    CabinClass.Business: "MIN-BUSINESS-SURP-OR-DISP",
    CabinClass.First: "MIN-BUSINESS-SURP-OR-DISP-NOT-MIXED",
}

# Mapping for Zenrows
CabinClassZenrowsCodeMapping = {
    CabinClass.Economy: "Economy",
    CabinClass.PremiumEconomy: "Premium Economy",
    CabinClass.Business: "Business",
    CabinClass.First: "First",
}
