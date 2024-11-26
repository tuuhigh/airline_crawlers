import os
from collections import namedtuple
from enum import Enum

from dotenv import load_dotenv

load_dotenv()
RANDOM_SLEEP_RANGE = (0.2, 0.5)
LOWEST_SLEEP = 0.5
LOW_SLEEP = 1
DEFAULT_SLEEP = 5
MEDIUM_SLEEP = 10
HIGH_SLEEP = 30
HIGHEST_SLEEP = 60
RETRY_COUNT = 2
ZENROWS_API_KEY = os.getenv("ZENROWS_API_KEY")
USE_VIRTUAL_DISPLAY = bool(os.getenv("USE_VIRTUAL_DISPLAY", "true").lower() == "true")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_CHANNEL_NAME = os.getenv("SLACK_CHANNEL_NAME")
ENV = os.getenv("ENV", "LOCAL")
LOCAL = bool(os.getenv("LOCAL", "true").lower() == "true")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")
PROXY_SERVICE_URL = os.getenv("PROXY_SERVICE_URL", "http://appdev.odynn.info:8090/proxy")
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_NAME = os.getenv("MONGODB_NAME")
AF_TEST_MODE = os.getenv("AF_TEST_MODE")
TK_TEST_MODE = os.getenv("TK_TEST_MODE")
ENGINEO_ENDPOINT = os.getenv("ENGINEO_ENDPOINT")

AirlineCredential = namedtuple("Credential", ["username", "password"])
EKAirlineCredential = namedtuple("Credential", ["username", "password", "app_pass"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# block pages by resource type. e.g. image, stylesheet
BLOCK_RESOURCE_TYPES = [
    'beacon',
    'csp_report',
    'font',
    'image',
    'imageset',
    'media',
    'object',
    'texttrack',
    'jpeg',
    'gif',
    'svg+xml'
    #  we can even block stylsheets and scripts though it's not recommended:
    # 'stylesheet',
    # 'script',
    # 'xhr',
]


# we can also block popular 3rd party resources like tracking and advertisements.
BLOCK_RESOURCE_NAMES = [
    'adzerk',
    'analytics',
    'cdn.api.twitter',
    'doubleclick',
    'exelator',
    'facebook',
    'fontawesome',
    'google',
    'google-analytics',
    'googletagmanager',
    "tiktok",
    #new
    'openh264',
    'adobedtm',
    'adobetarget',
    'mozilla.net',
    'mozilla.com',
    'bing',
    'pisano.com'
]


class ProxyType(Enum):
    BackConnect = "back_connect"
    Residential = "residential"


class CabinClass(Enum):
    Economy = "economy"
    PremiumEconomy = "premium_economy"
    Business = "business"
    First = "first"
    All = "all"


class Airline(Enum):
    AmericanAirline = "AA"
    AirCanada = "AC"
    VirginAtlantic = "VS"
    DeltaAirline = "DL"
    UnitedAirline = "UA"
    HawaiianAirline = "HA"
    AirFrance = "AF"
    JetBlue = "B6"
    Alaska = "AS"
    SingaporeAir = "SQ"
    CathayPacific = "CX"
    Avianca = "AV"
    Turkish = "TK"
    Emirates = "EK"
    BritishAir = "BA"


class ResponseFormat(str, Enum):
    Buffered = "Buffered"
    Streaming = "Streaming"


Credentials = {
    Airline.HawaiianAirline: [
        AirlineCredential(username="zachburau", password="Mgoblue16!"),
        AirlineCredential(username="jojnson1978yahoo", password="Pancakes123!"),
        AirlineCredential(username="tomas06271053", password="QWEqwe!@#123"),
        AirlineCredential(username="henry0627081459", password="QWEqwe!@#123"),
        AirlineCredential(username="becky0627082010", password="QWEqwe!@#123"),
        AirlineCredential(username="henry0627082314", password="QWEqwe!@#123"),
        AirlineCredential(username="sergio0627082458", password="QWEqwe!@#123"),
        AirlineCredential(username="becky0627082759", password="QWEqwe!@#123"),
        AirlineCredential(username="becky0627083158", password="QWEqwe!@#123"),
        AirlineCredential(username="sergio06270837", password="QWEqwe!@#123"),
    ],
    Airline.AirFrance: [
        AirlineCredential(username="zachburau@gmail.com", password="GoWolverinesBigM56!"),
        AirlineCredential(username="jojnson1978@yahoo.com", password="Umgobluezachburauodynn!23"),
        AirlineCredential(username="christinajohnson612@aol.com", password="Umgobluezachburauodynn!23"),
        AirlineCredential(username="silverado5160@gmail.com", password="Mgoblue16Odynn!"),
    ],
    Airline.SingaporeAir: [
        AirlineCredential(username="silverado5160@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="ilikepython7@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="luckyares1123@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="ilovesnow0520@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="drtulip0917@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="tpsapero1123@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="luckydragon0917@gmail.com", password="Pancakes123!"),
        AirlineCredential(username="foryoursuccess0415@gmail.com", password="Pancakes123!"),
    ],
    Airline.CathayPacific: [
        AirlineCredential(username="zachburau@gmail.com", password="Mgoblue16!")
    ],
    Airline.Avianca: [
        # AirlineCredential(username="08183922305", password="Pancakes123@"), # not work
        # AirlineCredential(username="08183922316", password="Pancakes123@"), # not work
        # AirlineCredential(username="08183922320", password="Pancakes123@"), # not work
        # AirlineCredential(username="08183922353", password="Pancakes123@"), # not work
        # AirlineCredential(username="08183922364", password="Pancakes123@"), # not work
        # AirlineCredential(username="08183922375", password="Pancakes123@"), # not work
        # AirlineCredential(username="08183922390", password="Pancakes123@"), # not work
        # AirlineCredential(username="13527569694", password="Pancakes123@"), # not work
        AirlineCredential(username="08183922331", password="Pancakes123@"), # work
        AirlineCredential(username="08183922342", password="Pancakes123@"), # work
        AirlineCredential(username="08183922386", password="Pancakes123@"), # work
    ],
    Airline.Turkish: [
        AirlineCredential(username="169180841", password="324612"),
        AirlineCredential(username="188469472", password="192837"),
        AirlineCredential(username="188478911", password="192837"),
        AirlineCredential(username="188482702", password="192837"),
        AirlineCredential(username="188500386", password="192837"),
        AirlineCredential(username="188508701", password="192837"),
        AirlineCredential(username="188516147", password="192837"),
        AirlineCredential(username="188528995", password="192837"),
        AirlineCredential(username="188535532", password="192837"),
        AirlineCredential(username="188541821", password="192837"),
        AirlineCredential(username="188546207", password="192837"),
    ],
    Airline.Emirates: [
        EKAirlineCredential(username="ilikepython7@gmail.com", password="Emirates@11112", app_pass="euqzsrniomqfbvxw"),
        EKAirlineCredential(username="luckyares1123@gmail.com", password="Emirates@11112", app_pass="aulszghghcqjjvir"),
        EKAirlineCredential(username="raulopespinto@gmail.com", password="Emirates@11112", app_pass="dvevhunbpfpumsce"),
        EKAirlineCredential(username="raullopesointo@gmail.com", password="Emirates@11112", app_pass="gvowoglmwltcimiy"),
        EKAirlineCredential(username="lucky.storm777owner@gmail.com", password="Emirates@11112", app_pass="titgdpzozniqorqc"),
    ],
    Airline.BritishAir: [
        AirlineCredential(username="crazydev1993@gmail.com", password="Avios@1123")
    ],
}
