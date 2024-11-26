from datetime import date
from typing import Union

from src.constants import Airline, CabinClass

SmartAirlineType = Union[Airline, str]
SmartCabinClassType = Union[CabinClass, str]
SmartDateType = Union[date, str]
