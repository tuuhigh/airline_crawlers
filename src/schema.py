import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class FlightSegment:
    id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    departure_time: Optional[str] = None
    departure_timezone: Optional[str] = None
    arrival_date: Optional[str] = None
    arrival_time: Optional[str] = None
    arrival_timezone: Optional[str] = None
    duration: Optional[str] = None
    aircraft: Optional[str] = None
    flight_number: Optional[str] = None
    carrier: Optional[str] = None
    layover_time: Optional[str] = None
    flight_stop: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        self.id = str(uuid.uuid4())


@dataclass
class CashFee:
    amount: Optional[float] = None
    currency: Optional[str] = None


@dataclass(unsafe_hash=True)
class Flight:
    airline: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    cabin_class: Optional[str] = None
    airline_cabin_class: Optional[str] = None
    fare_brand_name: Optional[str] = None
    amount: Optional[float] = None
    points: Optional[float] = None
    cash_fee: Optional[CashFee] = None
    segments: Optional[List[FlightSegment]] = None
    duration: Optional[str] = None  # This is only required for DL

    @property
    def finger_print(self) -> str:
        parts = [self.airline_cabin_class]
        for segment in self.segments:
            parts.append(segment.flight_number)
        return "_".join(parts).lower()
