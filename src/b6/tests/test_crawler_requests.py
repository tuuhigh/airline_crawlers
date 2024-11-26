import requests
from botasaurus_requests import request
from botasaurus_driver.user_agent import UserAgent
from curl_cffi import requests as crequests
import random

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
    'api-version': 'v3',
    'application-channel': 'Desktop_Web',
    'booking-application-type': 'NGB',
    'content-type': 'application/json',
    'origin': 'https://www.jetblue.com',
    'priority': 'u=1, i',
    'referer': 'https://www.jetblue.com/booking/flights?from=SGN&to=LHR&depart=2024-09-27&isMultiCity=false&noOfRoute=1&adults=1&children=0&infants=0&sharedMarket=true&roundTripFaresFlag=true&usePoints=true',
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'x-b3-spanid': '1724861410001',
    'x-b3-traceid': '33a262599788ad1c',
}

json_data = {
    'tripType': 'oneWay',
    'from': 'SGN',
    'to': 'LHR',
    'depart': '2024-09-27',
    'cabin': 'economy',
    'refundable': False,
    'dates': {
        'before': '3',
        'after': '3',
    },
    'pax': {
        'ADT': 1,
        'CHD': 0,
        'INF': 0,
        'UNN': 0,
    },
    'redempoint': True,
    'pointsBreakup': {
        'option': '',
        'value': 0,
    },
    'isMultiCity': False,
    'isDomestic': False,
    'outbound-source': 'fare-setSearchParameters',
}

UserAgentInstance = UserAgent()
my_ua = UserAgentInstance.get_random_cycled()
print(my_ua)

response = request.post(
    'https://jbrest.jetblue.com/lfs-rwb/outboundLFS', 
    headers=headers, json=json_data,
    os=random.choice(["windows", "mac", "linux"]),
    browser=random.choice(["firefox", "chrome"]),
    user_agent=my_ua,
    proxy="http://ihgproxy1:ihgproxy1234_country-us@geo.iproyal.com:12321"
    )

print(f">>>>>>>>>>.{response.status_code}")
print(f">>>>>>>>>>.{response.json()}")
# Note: json_data will not be serialized by requests
# exactly as it was in the original request.
#data = '{"tripType":"oneWay","from":"SGN","to":"LHR","depart":"2024-09-27","cabin":"economy","refundable":false,"dates":{"before":"3","after":"3"},"pax":{"ADT":1,"CHD":0,"INF":0,"UNN":0},"redempoint":true,"pointsBreakup":{"option":"","value":0},"isMultiCity":false,"isDomestic":false,"outbound-source":"fare-setSearchParameters"}'
#response = requests.post('https://jbrest.jetblue.com/lfs-rwb/outboundLFS', headers=headers, data=data)