import json
# flake8: noqa
from src.constants import CabinClass, BASE_DIR

CabinClassCodeMapping = {
    CabinClass.Economy: "ECONOMY",
    CabinClass.PremiumEconomy: "PREMIUM ECONOMY",
    CabinClass.Business: "BUSINESS",
    CabinClass.First: "LA PREMIÈRE",
}

def get_airport_timezone():
    with open(f"{BASE_DIR}/cx/airport_timezone.json", "r") as f:
        contents = f.read()
        ret = json.loads(contents)
        return ret