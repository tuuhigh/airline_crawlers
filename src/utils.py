import datetime
import re
import random
import json
import socket
from decimal import Decimal
from typing import Optional, Tuple
import requests
from src.constants import BASE_DIR

# def gen_random_user_agent():
    # ...

def get_airport_timezone():
    airport_tz = []
    with open(f"{BASE_DIR}/airport_timezone.json", "r") as f:
        contents = f.read()
        airport_tz = json.loads(contents)
        
    return {ap.get('iata_code', ''):ap.get('time_zone', '') for ap in airport_tz}
    
def get_random_port():
    while True:
        port = random.randint(3500, 3600)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            sock.close()
            continue
        else:
            sock.close()
            return port

def extract_digits(input_string):
    digits = re.findall(r"\d", input_string)
    result = "".join(digits)

    return result


def extract_k_digits(input_string) -> Optional[str]:
    pattern = r"\d+,\d{3}"  # Matches a pattern of digits, a comma, and three more digits
    match = re.search(pattern, input_string)

    if match:
        number = match.group(0).replace(",", "")  # Remove the comma from the matched number
        return number


def extract_iso_time(input_string):
    match = re.search(r"\d{2}:\d{2}", input_string)
    if match:
        return match.group(0)


def extract_digits_before_text(input_string):
    match = re.search(r"\d+", input_string)
    if match:
        return match.group(0)
    else:
        return None


def extract_flight_number(input_string) -> Optional[Tuple[str, str]]:
    airline_and_flight_pattern = re.compile(r"\b([A-Za-z0-9]{2})(\s*)(\d+)\b")
    match = airline_and_flight_pattern.search(input_string)

    if match:
        airline_code = match.group(1)
        flight_number = match.group(3)
        return airline_code, flight_number

    return "", ""


def convert_time_string_to_iso_format(input_string):
    time_pattern = re.compile(r"\b(\d{1,2}):(\d{2})\s*([APMapm]{2})\b")
    match = time_pattern.search(input_string)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3).upper()

        if period == "PM" and hour != 12:
            hour = hour + 12

        if period == "AM" and hour == 12:
            hour = 0

        iso_format = f"{hour:02d}:{minute:02d}"
        return iso_format


def convert_k_to_float(input_string: str) -> float:
    input_string = input_string.strip().lower()
    input_string = input_string.replace(",", "")
    if input_string.endswith("k"):
        return float(Decimal(input_string.replace("k", "")) * 1000)
    else:
        return float(input_string)


def convert_human_time_to_seconds(input_time: str) -> float:
    """
    "human time": 1h 12m
    to seconds
    """
    units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    return int(
        datetime.timedelta(
            **{
                units.get(m.group("unit").lower(), "seconds"): float(m.group("val"))
                for m in re.finditer(
                    r"(?P<val>\d+(\.\d+)?)(?P<unit>[smhdw]?)", input_time.replace(" ", ""), flags=re.I
                )
            }
        ).total_seconds()
    )


def extract_currency_and_amount(input_string) -> Optional[Tuple[str, float]]:
    pattern = re.compile(r"^\s*([+-])?([A-Za-z€£$]+)\s*([0-9,.]+)")
    match = pattern.match(input_string)

    if match:
        currency = match.group(2)
        amount = float(match.group(3).replace(",", ""))
        return currency, amount
    else:
        return None
    
def convert_currency_symbol_to_name(symbol):
    currency_map = {
        "$": "USD",
        "€": "EUR",
        "¥": "JPY",
        "£": "GBP",
        "₩": "KRW",
        "₹": "INR",
        "A$": "AUD",
        "C$": "CAD",
        "CHF": "CHF",
        "NZ$": "NZD",
        "R$": "BRL"
    }
    
    if symbol in currency_map:
        return currency_map[symbol]
    else:
        return "Unknown Currency"


def parse_date(input_date_string: str, input_date_format: str, output_date_format: str = "%Y-%m-%d") -> Optional[str]:
    try:
        return datetime.datetime.strptime(input_date_string, input_date_format).strftime(output_date_format)
    except ValueError:
        pass


def parse_time(input_time_string: str, input_time_format: str, output_time_format: str = "%H:%M") -> Optional[str]:
    try:
        return datetime.datetime.strptime(input_time_string, input_time_format).strftime(output_time_format)
    except ValueError:
        pass


def extract_letters(content):
    return re.sub(r"[^a-zA-Z]+", " ", content).strip()


def sanitize_text(content):
    return re.sub(r"\s+", " ", content).strip()


def send_slack_message(
    slack_channel_name: str,
    slack_webhook_url: str,
    env: str,
    airline: str,
    origin: str,
    destination: str,
    departure_date: str,
    cabin_class: str,
    adults: int,
    headline: str,
    reason: str,
):
    if slack_channel_name and slack_webhook_url:
        env = env.capitalize()
        cabin_class = cabin_class.capitalize()
        airline = airline.upper()

        payload = {
            "channel": slack_channel_name,
            "username": "Airline Live Checker Error",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{env.capitalize()}: {airline}:* {headline}\n",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"({origin}->{destination}), {departure_date}, {cabin_class} for {adults} passengers",
                    },
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": reason}},
                {"type": "divider"},
            ],
        }
        requests.post(slack_webhook_url, json=payload)


if __name__ == "__main__":
    test_strings = [
        "AF63 1Footnote Flight Specific Detailsopens in new popup",
        "AF1580 1Footnote Flight Specific Detailsopens in new popup",
    ]
    for test_string in test_strings:
        print(extract_flight_number(test_string))
