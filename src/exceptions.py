import datetime
from typing import Optional, Union

from src.types import SmartAirlineType


class CrawlerException(Exception):
    def __init__(self, message: str, *args, **kwargs):
        self.message = message
        reason = kwargs.get("reason")
        if reason:
            self.message += f" Reasons: {reason}"

    def __str__(self):
        if hasattr(self, "message"):
            return self.message
        else:
            return super().__str__()


class LiveCheckerException(Exception):
    def __init__(
        self,
        airline: SmartAirlineType,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date: Optional[str] = None,
        data: Optional[str] = None,
    ):
        self.message = f"{airline} ({origin} - {destination}) on {date}: {data}"
        super().__init__(self.message)


class AirlineCrawlerException(CrawlerException):
    def __init__(self, airline: SmartAirlineType, message: str, reason: Optional[str] = None):
        super().__init__(message=f"{airline}: {message}, Reason: {reason}")


class AirportNotSupported(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Does not Support airport"

    def __init__(self, airline: SmartAirlineType, airport: str, reason: Optional[str] = None):
        super().__init__(airline=airline, message=f"{self.MESSAGE_TEMPLATE}: {airport}", reason=reason)


class OnewayNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select One way trip"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class OriginNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select origin"

    def __init__(self, airline: SmartAirlineType, airport: str, reason: Optional[str] = None):
        super().__init__(airline=airline, message=f"{self.MESSAGE_TEMPLATE}: {airport}", reason=reason)


class DestinationNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select destination"

    def __init__(self, airline: SmartAirlineType, airport: str, reason: Optional[str] = None):
        super().__init__(airline=airline, message=f"{self.MESSAGE_TEMPLATE}: {airport}", reason=reason)


class LocaleNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select locale"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class MileNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select miles on"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class FlexibleDateNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select miles on"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class DepartureDateNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select departure date"

    def __init__(
        self, airline: SmartAirlineType, departure_date: Union[str, datetime.date], reason: Optional[str] = None
    ):
        super().__init__(airline=airline, message=f"{self.MESSAGE_TEMPLATE}: {departure_date}", reason=reason)


class CabinClassNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select cabin class"

    def __init__(self, airline: SmartAirlineType, cabin_class: str, reason: Optional[str] = Optional):
        super().__init__(airline=airline, message=f"{self.MESSAGE_TEMPLATE}: {cabin_class}", reason=reason)


class PassengerNotSelectable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to select passengers"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class CannotContinueSearch(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Not able to continue search"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class NoSearchResult(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "No Search Result"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class ZenRowFailed(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Zenrow script failed"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class PointNotExtractable(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Error occurred while extracting points"

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)


class LoginFailed(AirlineCrawlerException):
    MESSAGE_TEMPLATE = "Authentication failed..."

    def __init__(self, airline: SmartAirlineType, reason: Optional[str] = None):
        super().__init__(airline=airline, message=self.MESSAGE_TEMPLATE, reason=reason)
