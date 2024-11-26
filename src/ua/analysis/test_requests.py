import requests
from curl_cffi import requests as crequests

cookies = {
    'QuantumMetricSessionID': 'f84ef92ab46a2fe534e50def79145858',
    'Session': 'AuthToken=DAAAANxToW2w3C9ZfB%2fEHBAAAAAovUgOgDiLpmB46TwUZJLaax7G8af6cQMW3CZF5i0qq7gHMbtRctKnECAXDEvpewVF%2ft%2f0',
    'akacd_ABdeployment': '3906037474~rv=60~id=69620a344006901a17f951bde8044aee',
    'QuantumMetricUserID': '4b8174003ab1168f5ffd441a7a4017ab',
    'Locale': 'UMID=ecb6ef0c-53d7-458a-b8ac-86c120b1f57b&Lang=en&POS=US',
    'newHP': 'true',
    'coveo_visitorId': '412e3b3e-e350-4f53-b104-0514892218f6',
    'LPVID': 'Q0MzllNzA0NWMyYzI1ZmNi',
    'LPSID-84608747': 'uMMQwBEJS1uQHR_ATV0leA',
    '__gads': 'ID=9492d0e97b38b099:T=1728584700:RT=1728584700:S=ALNI_MY3K2Fvl5OevuYiH_O8-bJHDMHayg',
    '__gpi': 'UID=00000f3e289dba7a:T=1728584700:RT=1728584700:S=ALNI_MbyS2sjul6QUwp6X_nxyExPS4HRBA',
    '__eoi': 'ID=a265801d5cdc4ccc:T=1728584700:RT=1728584700:S=AA-Afja8VSrAN0Uy6SQbpng0tPw5',
    'akacd_NS_AB': '3906037585~rv=95~id=322392278709818d765644c1b926d3ad',
    'bm_mi': 'C04D9DEB933C25A3ECC09BCAD2DDC469~YAAQBDNDGwt8TGaSAQAACKOudxnRQLg+lselTmXtC9mYrn1La606MB5e4H2K3kYkrIP5ge2SjVUMJc10fiA14QhKnSrOao31TlsRFHiQ+vZvclOA6U/OYT0v3ANRTF9z2qOZ0DgDRIPzF2CyDHKcpqbwKy5zlnlE0m+1C/7eQatJMPijaB2H6BNwZh+pTHW3ScZRqgUnUtemkKbh9t0Yw2EHvSdWBDDpf4Atshzt5QSrWOXq04FKYjn1+Q+2CqBOaYq2QiEzFxgdPJc9XUsyRpB4J0p+fbAsSsUHWRgLvsLpCJXQ8gRe4mbZ7Zs1ItJZi9mhLNVwLVEx/4DlV8e4WLipMktw9A==~1',
    'bm_sz': 'DF4EADBCBB121BEB1A78D18C52AB129A~YAAQBDNDGw18TGaSAQAACKOudxk9M9xmHHWUoNHe+svaS1wjAmePv4isZIiR9L+PDkeXWy1029EcMLZAYavEOxzp8wniEr10n2Ssv5LiT+DN+wMajYWAhXvURPtqdSRVtUYg+bQxMidBW51ID1rELPhm1jVoseaDqrLVspJRPA4pgO0tnFv5wZ/81PeGVp8T/QH1tAO7knSZaxqA/cAvRBlnsmoZjxEi61UyLqibhELXmiVuyrUohEUJ4cbrIl5V8ZKkxgaKHiXdTxwGXX7FMbj2lRTkZj+7XZuYU9Z+u7JNcknPAFTcXuA7n1coLYP5IAfXuAh654Y3WRiBjDkKbVUxuTB74RBajz/mXsfR41mfEvZ7VD6CbZYR5qhESTuq1XZZPfSWwxvpKnLkLozIkfjMqyAYM3FS8NLM0i0YeVySseb6fy7A~4600386~4470838',
    '_ga_FYCK6D7HD0': 'GS1.1.1728583859.1.1.1728584786.0.0.0',
    'RT': '"z=1&dm=united.com&si=d5998530-d22c-4a84-9276-c7c191ce2d00&ss=m23m6zzj&sl=7&tt=abt&bcn=%2F%2F684d0d44.akstat.io%2F"',
    'optimizely_id': '1728937740.22388045',
    # 'optimizely_id': '1728937843.51528198',
    'utag_main': '_sn:14$_se:150%3Bexp-session$_ss:0%3Bexp-session$_st:1728586589589%3Bexp-session$ses_id:1728583855310%3Bexp-session$_pn:2%3Bexp-session',
    'ak_bmsc': '34A6CFCA1746045C3DCE9108A45A7BD3~000000000000000000000000000000~YAAQBDNDGyB8TGaSAQAAza6udxnqpCTvGSxXDZ29+d+P6Wqd6pexsatzSfopxiDbACEbVEv4wjK87/NqfluAaFENKN6L5fw0TiYlg1ZdSvYmYUlcx5eDxxLsU9WPvtEwwRw/o3+l1rZeoE1uJHxOVI8VrYmrQIZnSk11+rJ2dEum1NFZoRunrZ1JC2aQ+2Vd0s5QW/xNYSyfv4fQqP607FwHDSgnx+srmxZ9LtlLunYQfqKaSX/jL61prqvyWW8veHklLkFVnlpaE0iuCKC/gXfwMTXCNoIJTBv8JbKk2mun2dI094aoYAccsw0sxFtQBmj02YKM7os0vqYJbQ7Kn0t1WYFtZQxfpQFnQpsx0eqxEOBWE8vQl52AVZbKkx+h2NCG1HCJKnrEiki+HAZBzegASjCWr5IbaQIoVq0YBRmxm761GA132o90dtPvQdl4ZGgpWnyjkHWC/VZ1niQpPt/dhQrU2kb2HJT5WR5AyjQLtQLn/6qDOO0NPgK8/el1nRTjoVHgpqY=',
    '_dd_s': 'rum=1&id=e32c0f58-5ef1-4702-957b-03ade174f724&created=1728584788646&expire=1728585688646',
    'akavpau_ualwww': '1728938040~id=4402afe197a362e83e35cb906f5370c0',
    '_abck': '885F33973CDFE8EAC411CF884EBBCCCC~-1~YAAQBDNDGyl8TGaSAQAAcLCudwxqWMLj+vroy9l5PlkcycciFPh2QHQTsURfcoWds4lQ/7vxZZ4jV7BaTrljKC4VRqdiDbjtJzqS9qWWdyZ66WrQPZcX5VP09z2jAXDaflo0fd2AIoOHbH14Mwbv0Yf7jgd2xh7UiRoermD9fy9kdbJyOUS+uIPQ62NOC8q2N2p1vCq2hmCsuQzL7taVrT5mEjUzm2LmBWN42423tQ+ZSfnva8UZN+Y92S1tBUrEHVjGD/SkOteW9l4LkOOHeNAkBeRdDQXHUNONjSp8z5Z4Bc5NPgOQ1YxEejcrylBslP1jRbpOeR2WJjGBkGV/pgjbSWh9WFixksIdnIEGCUGEMMHjThfrDHQ2UkQIx7NLlrbe1sGsJq6MOLqpmPvwYDDTVV7SNekkvNO/zfdSIk0Y6WTqn5Y/IvyI38H/YMrZ4Ptz3Cbhl6Jy1lD6X3+LheniuBENkWZLm1CmEsgF5da6uq6GWb4zsfrltCgpDGJZatQiCD5nlk7SSJJgx1tucRGARZ4+H22T5lk8JFr4f8Q04uuIrplq9NrBgBVAbwV6F19h9vtFtrm84DDe0ujYdfIy6lp8RtmnxXWsj3/Ig/6Esz8zHE5fq9YelgJaMcRjATuHOjGeEFBpVzigYRWLqOYAYRkmetVCOy3oqlvYkozQRxChaGHMbL74dWXuM8FNdjz2R18uxJxEDtugSCNfdNN3OQZoGzA681zjMKWwmUITByr4AaGFGhhbw9RdDA==~-1~||0||~1728937740',
    'bm_sv': '75683E9D4642D48BE70321554B5BC71B~YAAQBDNDGyt8TGaSAQAAq7Cudxn7dv03BukZpHZUS2ZKbML+DqCPuPHbS6NRA6GBDkaKKLk6IubB5SnVsGcqzwpWvUujwBke5jVrmzWyRm7hVCJwEOdJv3fL4ysN29dESq2MjsTspVojJNXpK0jVzRaFtM+hG9ShWGyERTYWjiqF8IA94DBk/nTKXmkKMunZmJCT3s7iM0zTIgH0TbesINO7Lc9IvJbp14kr/9E4n2ZrqaGk4K93ZcbL9a0o0XNWVA==~1',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'en-US',
    'content-type': 'application/json',
    # 'cookie': 'QuantumMetricSessionID=f84ef92ab46a2fe534e50def79145858; Session=AuthToken=DAAAANxToW2w3C9ZfB%2fEHBAAAAAovUgOgDiLpmB46TwUZJLaax7G8af6cQMW3CZF5i0qq7gHMbtRctKnECAXDEvpewVF%2ft%2f0; akacd_ABdeployment=3906037474~rv=60~id=69620a344006901a17f951bde8044aee; QuantumMetricUserID=4b8174003ab1168f5ffd441a7a4017ab; Locale=UMID=ecb6ef0c-53d7-458a-b8ac-86c120b1f57b&Lang=en&POS=US; newHP=true; coveo_visitorId=412e3b3e-e350-4f53-b104-0514892218f6; LPVID=Q0MzllNzA0NWMyYzI1ZmNi; LPSID-84608747=uMMQwBEJS1uQHR_ATV0leA; __gads=ID=9492d0e97b38b099:T=1728584700:RT=1728584700:S=ALNI_MY3K2Fvl5OevuYiH_O8-bJHDMHayg; __gpi=UID=00000f3e289dba7a:T=1728584700:RT=1728584700:S=ALNI_MbyS2sjul6QUwp6X_nxyExPS4HRBA; __eoi=ID=a265801d5cdc4ccc:T=1728584700:RT=1728584700:S=AA-Afja8VSrAN0Uy6SQbpng0tPw5; akacd_NS_AB=3906037585~rv=95~id=322392278709818d765644c1b926d3ad; bm_mi=C04D9DEB933C25A3ECC09BCAD2DDC469~YAAQBDNDGwt8TGaSAQAACKOudxnRQLg+lselTmXtC9mYrn1La606MB5e4H2K3kYkrIP5ge2SjVUMJc10fiA14QhKnSrOao31TlsRFHiQ+vZvclOA6U/OYT0v3ANRTF9z2qOZ0DgDRIPzF2CyDHKcpqbwKy5zlnlE0m+1C/7eQatJMPijaB2H6BNwZh+pTHW3ScZRqgUnUtemkKbh9t0Yw2EHvSdWBDDpf4Atshzt5QSrWOXq04FKYjn1+Q+2CqBOaYq2QiEzFxgdPJc9XUsyRpB4J0p+fbAsSsUHWRgLvsLpCJXQ8gRe4mbZ7Zs1ItJZi9mhLNVwLVEx/4DlV8e4WLipMktw9A==~1; bm_sz=DF4EADBCBB121BEB1A78D18C52AB129A~YAAQBDNDGw18TGaSAQAACKOudxk9M9xmHHWUoNHe+svaS1wjAmePv4isZIiR9L+PDkeXWy1029EcMLZAYavEOxzp8wniEr10n2Ssv5LiT+DN+wMajYWAhXvURPtqdSRVtUYg+bQxMidBW51ID1rELPhm1jVoseaDqrLVspJRPA4pgO0tnFv5wZ/81PeGVp8T/QH1tAO7knSZaxqA/cAvRBlnsmoZjxEi61UyLqibhELXmiVuyrUohEUJ4cbrIl5V8ZKkxgaKHiXdTxwGXX7FMbj2lRTkZj+7XZuYU9Z+u7JNcknPAFTcXuA7n1coLYP5IAfXuAh654Y3WRiBjDkKbVUxuTB74RBajz/mXsfR41mfEvZ7VD6CbZYR5qhESTuq1XZZPfSWwxvpKnLkLozIkfjMqyAYM3FS8NLM0i0YeVySseb6fy7A~4600386~4470838; _ga_FYCK6D7HD0=GS1.1.1728583859.1.1.1728584786.0.0.0; RT="z=1&dm=united.com&si=d5998530-d22c-4a84-9276-c7c191ce2d00&ss=m23m6zzj&sl=7&tt=abt&bcn=%2F%2F684d0d44.akstat.io%2F"; optimizely_id=1728584789.22388045; utag_main=_sn:14$_se:150%3Bexp-session$_ss:0%3Bexp-session$_st:1728586589589%3Bexp-session$ses_id:1728583855310%3Bexp-session$_pn:2%3Bexp-session; ak_bmsc=34A6CFCA1746045C3DCE9108A45A7BD3~000000000000000000000000000000~YAAQBDNDGyB8TGaSAQAAza6udxnqpCTvGSxXDZ29+d+P6Wqd6pexsatzSfopxiDbACEbVEv4wjK87/NqfluAaFENKN6L5fw0TiYlg1ZdSvYmYUlcx5eDxxLsU9WPvtEwwRw/o3+l1rZeoE1uJHxOVI8VrYmrQIZnSk11+rJ2dEum1NFZoRunrZ1JC2aQ+2Vd0s5QW/xNYSyfv4fQqP607FwHDSgnx+srmxZ9LtlLunYQfqKaSX/jL61prqvyWW8veHklLkFVnlpaE0iuCKC/gXfwMTXCNoIJTBv8JbKk2mun2dI094aoYAccsw0sxFtQBmj02YKM7os0vqYJbQ7Kn0t1WYFtZQxfpQFnQpsx0eqxEOBWE8vQl52AVZbKkx+h2NCG1HCJKnrEiki+HAZBzegASjCWr5IbaQIoVq0YBRmxm761GA132o90dtPvQdl4ZGgpWnyjkHWC/VZ1niQpPt/dhQrU2kb2HJT5WR5AyjQLtQLn/6qDOO0NPgK8/el1nRTjoVHgpqY=; _dd_s=rum=1&id=e32c0f58-5ef1-4702-957b-03ade174f724&created=1728584788646&expire=1728585688646; akavpau_ualwww=1728585390~id=4402afe197a362e83e35cb906f5370c0; _abck=885F33973CDFE8EAC411CF884EBBCCCC~-1~YAAQBDNDGyl8TGaSAQAAcLCudwxqWMLj+vroy9l5PlkcycciFPh2QHQTsURfcoWds4lQ/7vxZZ4jV7BaTrljKC4VRqdiDbjtJzqS9qWWdyZ66WrQPZcX5VP09z2jAXDaflo0fd2AIoOHbH14Mwbv0Yf7jgd2xh7UiRoermD9fy9kdbJyOUS+uIPQ62NOC8q2N2p1vCq2hmCsuQzL7taVrT5mEjUzm2LmBWN42423tQ+ZSfnva8UZN+Y92S1tBUrEHVjGD/SkOteW9l4LkOOHeNAkBeRdDQXHUNONjSp8z5Z4Bc5NPgOQ1YxEejcrylBslP1jRbpOeR2WJjGBkGV/pgjbSWh9WFixksIdnIEGCUGEMMHjThfrDHQ2UkQIx7NLlrbe1sGsJq6MOLqpmPvwYDDTVV7SNekkvNO/zfdSIk0Y6WTqn5Y/IvyI38H/YMrZ4Ptz3Cbhl6Jy1lD6X3+LheniuBENkWZLm1CmEsgF5da6uq6GWb4zsfrltCgpDGJZatQiCD5nlk7SSJJgx1tucRGARZ4+H22T5lk8JFr4f8Q04uuIrplq9NrBgBVAbwV6F19h9vtFtrm84DDe0ujYdfIy6lp8RtmnxXWsj3/Ig/6Esz8zHE5fq9YelgJaMcRjATuHOjGeEFBpVzigYRWLqOYAYRkmetVCOy3oqlvYkozQRxChaGHMbL74dWXuM8FNdjz2R18uxJxEDtugSCNfdNN3OQZoGzA681zjMKWwmUITByr4AaGFGhhbw9RdDA==~-1~||0||~1728588388; bm_sv=75683E9D4642D48BE70321554B5BC71B~YAAQBDNDGyt8TGaSAQAAq7Cudxn7dv03BukZpHZUS2ZKbML+DqCPuPHbS6NRA6GBDkaKKLk6IubB5SnVsGcqzwpWvUujwBke5jVrmzWyRm7hVCJwEOdJv3fL4ysN29dESq2MjsTspVojJNXpK0jVzRaFtM+hG9ShWGyERTYWjiqF8IA94DBk/nTKXmkKMunZmJCT3s7iM0zTIgH0TbesINO7Lc9IvJbp14kr/9E4n2ZrqaGk4K93ZcbL9a0o0XNWVA==~1',
    'origin': 'https://www.united.com',
    'priority': 'u=1, i',
    'referer': 'https://www.united.com/en/us/fsr/choose-flights?tt=1&st=bestmatches&d=2024-10-24&clm=7&taxng=1&f=JFK&px=1&newHP=True&sc=7&act=2&at=1&tqp=A&t=LHR&idx=1&mm=0',
    'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'x-authorization-api': 'bearer DAAAAPXqLXpLsXKEPkN3uhAAAACF4DkSYtSRTv+WD2yIPo3rCbkd3bA8vbQV1A0tVLL2Th9HdCJmZqVMHKk5DP8VYfSAIpxOs41WU6UFDFf0cd8lJLovXPz0FNbNcO4uQ+vL7c1T5eywxb529CNa1Ch1L8GelyktQulYN7Y+LN7lUrjPeos4TCOgSrulvhNAOU79fQ==',
    'x-datadog-origin': 'rum',
    'x-datadog-parent-id': '8012434446977613999',
    'x-datadog-sampling-priority': '0',
    'x-datadog-trace-id': '4782537470562989309',
}

json_data = {
    'SearchTypeSelection': 1,
    'SortType': 'bestmatches',
    'SortTypeDescending': False,
    'Trips': [
        {
            'Origin': 'JFK',
            'Destination': 'LHR',
            'DepartDate': '2024-11-24',
            'Index': 1,
            'TripIndex': 1,
            'SearchRadiusMilesOrigin': 0,
            'SearchRadiusMilesDestination': 0,
            'DepartTimeApprox': 0,
            'SearchFiltersIn': {
                'FareFamily': 'BUSINESS',
                'AirportsStop': None,
                'AirportsStopToAvoid': None,
            },
        },
    ],
    'CabinPreferenceMain': 'premium',
    'PaxInfoList': [
        {
            'PaxType': 1,
        },
    ],
    'AwardTravel': True,
    'NGRP': True,
    'CalendarLengthOfStay': 0,
    'PetCount': 0,
    'RecentSearchKey': 'JFKLHR10/24/2024',
    'CalendarFilters': {
        'Filters': {
            'PriceScheduleOptions': {
                'Stops': 1,
            },
        },
    },
    'Characteristics': [
        {
            'Code': 'SOFT_LOGGED_IN',
            'Value': False,
        },
        {
            'Code': 'UsePassedCartId',
            'Value': False,
        },
    ],
    'FareType': 'mixedtoggle',
    'CartId': 'ED9791DF-9219-471F-86DE-D6C18CD91D9C',
}

proxy_user = "ihgproxy1"
proxy_pass = "ihgproxy1234_country-us"
proxy_host = "geo.iproyal.com"
proxy_port = "12321"
proxy_attr = {
    "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
    "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
}

response = crequests.post(
    'https://www.united.com/api/flight/FetchFlights', 
    impersonate="chrome120",
    proxies=proxy_attr, 
    cookies=cookies, headers=headers, json=json_data)

print(f">>>>>>>>>>>>>>>..{response.status_code}")
print(f">>>>>>>>>>>>>>>..{response.text}")
# Note: json_data will not be serialized by requests
# exactly as it was in the original request.
#data = '{"SearchTypeSelection":1,"SortType":"bestmatches","SortTypeDescending":false,"Trips":[{"Origin":"JFK","Destination":"LHR","DepartDate":"2024-10-24","Index":1,"TripIndex":1,"SearchRadiusMilesOrigin":0,"SearchRadiusMilesDestination":0,"DepartTimeApprox":0,"SearchFiltersIn":{"FareFamily":"BUSINESS","AirportsStop":null,"AirportsStopToAvoid":null}}],"CabinPreferenceMain":"premium","PaxInfoList":[{"PaxType":1}],"AwardTravel":true,"NGRP":true,"CalendarLengthOfStay":0,"PetCount":0,"RecentSearchKey":"JFKLHR10/24/2024","CalendarFilters":{"Filters":{"PriceScheduleOptions":{"Stops":1}}},"Characteristics":[{"Code":"SOFT_LOGGED_IN","Value":false},{"Code":"UsePassedCartId","Value":false}],"FareType":"mixedtoggle","CartId":"ED9791DF-9219-471F-86DE-D6C18CD91D9C"}'
#response = requests.post('https://www.united.com/api/flight/FetchFlights', cookies=cookies, headers=headers, data=data)