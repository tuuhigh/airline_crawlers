from src.constants import CabinClass

CabinClass2BookingCode = {
    CabinClass.Economy: ["B", "G", "H", "K", "L", "M", "N", "O", "Q", "V", "S", "Y", "T"],
    CabinClass.PremiumEconomy: ["P", "W"],
    CabinClass.Business: ["C", "D", "I", "J", "R"],
    CabinClass.First: ["A", "F"],
}

BookingCode2AmericanCabinClass = {
    "Y": "Main Cabin",
    "W": "Premium Economy",
    "J": "Business",
    "F": "First",
}
CabinClassMap = {
    CabinClass.Economy: "Main",
    CabinClass.PremiumEconomy: "Premium Economy",
    CabinClass.Business: "Business",
    CabinClass.First: "First",
}
