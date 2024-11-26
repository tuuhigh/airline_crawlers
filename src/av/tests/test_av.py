
from botasaurus_requests import request
from curl_cffi import requests as crequests
import json

cookies = {
    'rxVisitor': '1725294304504OF50I3VCN5ISH70LHJA6SFJ2JS31BOJ1',
    'chn-stg': 'wst',
    'ak_bmsc': 'EEC707D268ACC1C06895981BD7612BF6~000000000000000000000000000000~YAAQ71JNG73RZJeRAQAAU+KNsxgStY6X8NDTDAtpi5+njKeOuG2aj7wp6Rq+F9Ad9EInJViiH+9uSvpVGi2QXLlFgE60vVEa1I8KrivVV1iPDcRreqa+N/6O81xj7S5m+Q0Q9GCvN+NHl84uzQ3+8CfiWW5EJp+EvPsIeGLFXcZ+LCnCwmQEpfusJrfvb3vf08XKZVmcQrCwhVrRKvEBwp0lkEIcO83o+DAvtJREY7ekcFn01ghzzGCufdGH0BHkaWTmDaGpaNAXCG6nov6dcvZzpuAQlt2ENpHrTWiQ0F8CJZyeD8mRzH1HkO4RJEsZ1248peOc1GyM+BBdOIDkJIXdeUHWTZ5bBBcVu641H+kyKHwZI21wl+2NgFqthRskdAEyYXNociNwIVc733f5EIHE1acNIRpIbAJQyn0Qu4VvCMYB6Kcxoz2Kog7iv4X8a6KzpNEhxEKGp3rgK39f',
    '_tt_enable_cookie': '1',
    '_ttp': 'tJUr4m5MXPADgPfHFmqctJSE0U3',
    '_gcl_au': '1.1.1432052510.1725294307',
    '__ssid': '88b8bd0be60acb2081c4aec47a97cea',
    'lng-stg': 'en',
    'cty-stg': 'us',
    '_fbp': 'fb.1.1725294307579.11536486230369965',
    '_gid': 'GA1.2.1554079601.1725294315',
    '_ga_BS8PBT1VYN': 'GS1.2.1725294315.1.1.1725294585.0.0.0',
    '_ga_LWDNL0ZMW0': 'GS1.1.1725294315.1.1.1725294587.0.0.0',
    '_ga': 'GA1.1.1059275046.1725294306',
    'loginMethod': 'lifemiles',
    'provDtLogin': '%7B%22site%22%3A%22LM%22%2C%22provider%22%3A%22%22%2C%22currentDate%22%3A%222024-09-02%2023%3A30%3A13%22%7D',
    'dtSa': '-',
    '_hjSessionUser_1712397': 'eyJpZCI6IjE3YmU1ZjQ2LTIxNGItNTk3My04MTVhLTY1MWJhNjJkYTgzMiIsImNyZWF0ZWQiOjE3MjUyOTQ2MjA4NzMsImV4aXN0aW5nIjpmYWxzZX0=',
    'FPID': 'FPID2.2.hwJY%2FEU65fsKOkMRZ0Y8IhP28YhSl9w7pcfXWM%2BlAoI%3D.1725294306',
    'FPLC': 'ZarjNUZ9QTQ9SgwOIquiSmDDypkn9rDtpm%2BcTKiMi9TCluuyNc7XWrKhBAwCmL3cZaOc9OiWAThPAMe%2BAaJmvHXi2SWAx8iXr1IF3QTlQB%2B67ZLTxt16w1mPxaDc1w%3D%3D',
    'dtCookie': 'v_4_srv_9_sn_A67064305CF6A5088CC0F4CE2A64C546_perc_100000_ol_0_mul_1_app-3A93fb5a7425baf99b_1_app-3A6caf7d1c4abbb4b3_0_app-3A1eba319656f7eebb_0_rcs-3Acss_1',
    '_ga_YYYYYYYYYY': 'GS1.1.1725294314.1.1.1725295485.0.0.915183076',
    '_abck': '43AD960CB27EA72603491A59FDF27B34~0~YAAQ5FJNGyPVIZmRAQAAV+rEswzGvCSg5vhnokRxpK88NVJnaICjK4i4PNiFCnMLKvxI92uX9iZ8lQhKg5UlVJv5fF4+58T6w0KCJ5N/tB6XbeWa8A+9buTs7+2pBYC4Koo4DXcRRv3eiE9rzrO01+l1cubtOwVlvbBHFb9yb3BrSmD/gXbnON5loMi4lIDwVvnuSYnnEPeejAjtBwmbRNb3K9qtGRHX6CK6P12kWYpQl0B2RleyZZwzsKzRiRPRr+TiqTkEUd6pzF/GbDQGzvMyUYi4M/Dth9IRHtMz6vz3evz8S4SU+Z7D4fHatbhrjb8DEKRq2JYj8rd9VKi2yDgxZ7EwUQiFpdDn+wlFTIiq3vWa5vS2OIucTbBsysyDoWrcvyn9PUZjdI0Dm0IEiqeWOhGBWTYDuBpGmMPbB4CsfzQELgaJGkWM5Xajy6ZeRjwHccnFPpJjoN3svAyLpr+9JdrJC9J8UOaofVIqAgwki1w0YnNbKO2OiMxn9yBSrTqDt7eY//Q=~-1~-1~-1',
    'bm_sz': 'E9877A385C9F040B9A0F87F35424561D~YAAQ5FJNGyXVIZmRAQAAV+rEsxhpPbYah65Bf20vO6Dq6+clMfVRBRde4xtOahB5EbHi+K/9OtxICYeygjItUFT9h9ym9FihWJzXVXffg0RrAzv1wOPPW+Mba8BeeGgX74N+uXgFWlic/+DoVFDlIcoxh+mZDZT/LTiMPQgZZoNTkBGejfrrof6kmssdiyMIM7zR3EAzmvp4Cf/5RFCCQmGR2XrsOlB8l16e6VGe1cGClt7GHdn/66KHzUWBBO1PDrpFPOJoq4XTdBajBtn9bgZnssytU0u4DToL2IbOVjthW6wYURZ83C9PGvRS3HVrZgFU4yGxvGF/fxbogPJqKUeVebrr4bnN3JqTM+srCyn3WspRHXrUhxkL0i1ZdE4aQqRIa2mD2YFJAbLNLXsLUMUuLTQfwYk2YP/I6c73isqxy8Co+tKatbz7/QqTDKPu/PQTP+K9oEqrIsupdSzFiJWM1Ax65QVGFZcL0bkC//4kMvsDF5QCAS0HaGWec/cTiEK/S3GelWRB3B1vF4GvMV5nq69vTOFxTg==~3618355~3421506',
    'bm_sv': '31D7BB6E58331CBB8B24108E06262E05~YAAQ5FJNGz/WIZmRAQAAUBvFsxjAg4RZ4hKzMRnRZ0KDf03XjRMExbdvHL0fExMh+S3UhTO5UA6DEUKaRcahRH9+BG97DfJiQSCFHzKGp3jtaRsMhTfuQGULfkOEbCNezHskjsLg8UrvylFncwhNVRaorcjzW7K52x/qQqKIU/nbUEANUnP7FgQmR5ffGO7IsY5qOleqL5JAx6juR3WjTE+vJPNDKAZNAoTFaV9GT7IH4lCQjczaFyUG5cL/oqjaIZtwL+A=~1',
    '_ga_P7JFFQ1HW2': 'GS1.1.1725297491.2.1.1725297924.54.0.0',
    'rxvt': '1725299755147|1725294304505',
    'dtPC': '9$295485932_641h76vTNFDQCBJPAMTHCOTEEHCCVRJDUAHJJMK-0e0',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
    'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJ5TGxIWEZ5ajU3Y2R3Mll1eGlHcm9XT25kejBIOEkzZDBzM3JmRERrU1FJIn0.eyJleHAiOjE3MjUyOTgyMTksImlhdCI6MTcyNTI5NzkxOSwiYXV0aF90aW1lIjoxNzI1Mjk0NjE3LCJqdGkiOiIzNjU2OTg2Yy00ZWQzLTRhZjctOWFlMC1iM2E3MDI2YjgzNzciLCJpc3MiOiJodHRwczovL3Nzby5saWZlbWlsZXMuY29tL2F1dGgvcmVhbG1zL2xpZmVtaWxlcyIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI3NTA1YjQ3Yi1lMWE5LTQ3MDYtOGQ5YS1kNGU2YjE2NTViNDgiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJsaWZlbWlsZXMiLCJzZXNzaW9uX3N0YXRlIjoiMjBhMDVhMWQtYmUyMi00ZDA1LWIzNTEtNTJhODcyY2RiZDEwIiwiYWNyIjoiMSIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwczovL3d3dy5saWZlbWlsZXMuY29tLyJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsib2ZmbGluZV9hY2Nlc3MiLCJkZWZhdWx0LXJvbGVzLWxpZmVtaWxlcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgZW1haWwgcHJvZmlsZSBsaWZlbWlsZXMtbXAiLCJzaWQiOiIyMGEwNWExZC1iZTIyLTRkMDUtYjM1MS01MmE4NzJjZGJkMTAiLCJsbS1pZCI6IjA4MTgzOTIyMzMxIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwcm92aWRlciI6ImxpZmVtaWxlcyIsIm5hbWUiOiJTIGlsdmVyYWRvIiwicHJlZmVycmVkX3VzZXJuYW1lIjoic2lsdmVyYWRvLjUxNjBAZ21haWwuY29tIiwiZ2l2ZW5fbmFtZSI6IlMiLCJmYW1pbHlfbmFtZSI6ImlsdmVyYWRvIiwidGlkIjoiNmM1ODkzOGIwMzc5YTFiZTQyNmFjMzliZDhlOTM5NDAxYTU0Mzg3MzEyNjVkMTc5ZWI2ZGE2MWQyMjBjMzU0NyIsImVtYWlsIjoic2lsdmVyYWRvLjUxNjBAZ21haWwuY29tIiwiY2lkIjoibGlmZW1pbGVzIn0.U7ar5Dbtuxvvm3pZS_7OaLGqXqvCRiM3awwnOwjmorHwqZsosoyKAEFBpDCxXZcZ2ybGtcn-VmUJMm-eTFBbXKpRy7YLiuDLDrKsDbaBKLT77G4E9LG2p7fdyamWkUkv0XWR70HR3HR0X4wvOA8E7b3MM7a6FOmKMuM2G3MmBrgr5mvh5X610xrb-WKeKBh-NLpnAslgGbnM1EJHOhOCWNsfjDpNUlmR6gwxn5V37LvvyYHrWT366kvmtdGQ4sbKMjpjshg_1ff0k_ZFKK6-VErFd2po08HvEFYgWVPiy--lLtaY5m_8Rt7I45WnPBmwnkBVpS3JjlgQ2o-t_s8THA',
    'content-type': 'application/json',
    # 'cookie': 'rxVisitor=1725294304504OF50I3VCN5ISH70LHJA6SFJ2JS31BOJ1; chn-stg=wst; ak_bmsc=EEC707D268ACC1C06895981BD7612BF6~000000000000000000000000000000~YAAQ71JNG73RZJeRAQAAU+KNsxgStY6X8NDTDAtpi5+njKeOuG2aj7wp6Rq+F9Ad9EInJViiH+9uSvpVGi2QXLlFgE60vVEa1I8KrivVV1iPDcRreqa+N/6O81xj7S5m+Q0Q9GCvN+NHl84uzQ3+8CfiWW5EJp+EvPsIeGLFXcZ+LCnCwmQEpfusJrfvb3vf08XKZVmcQrCwhVrRKvEBwp0lkEIcO83o+DAvtJREY7ekcFn01ghzzGCufdGH0BHkaWTmDaGpaNAXCG6nov6dcvZzpuAQlt2ENpHrTWiQ0F8CJZyeD8mRzH1HkO4RJEsZ1248peOc1GyM+BBdOIDkJIXdeUHWTZ5bBBcVu641H+kyKHwZI21wl+2NgFqthRskdAEyYXNociNwIVc733f5EIHE1acNIRpIbAJQyn0Qu4VvCMYB6Kcxoz2Kog7iv4X8a6KzpNEhxEKGp3rgK39f; _tt_enable_cookie=1; _ttp=tJUr4m5MXPADgPfHFmqctJSE0U3; _gcl_au=1.1.1432052510.1725294307; __ssid=88b8bd0be60acb2081c4aec47a97cea; lng-stg=en; cty-stg=us; _fbp=fb.1.1725294307579.11536486230369965; _gid=GA1.2.1554079601.1725294315; _ga_BS8PBT1VYN=GS1.2.1725294315.1.1.1725294585.0.0.0; _ga_LWDNL0ZMW0=GS1.1.1725294315.1.1.1725294587.0.0.0; _ga=GA1.1.1059275046.1725294306; loginMethod=lifemiles; provDtLogin=%7B%22site%22%3A%22LM%22%2C%22provider%22%3A%22%22%2C%22currentDate%22%3A%222024-09-02%2023%3A30%3A13%22%7D; dtSa=-; _hjSessionUser_1712397=eyJpZCI6IjE3YmU1ZjQ2LTIxNGItNTk3My04MTVhLTY1MWJhNjJkYTgzMiIsImNyZWF0ZWQiOjE3MjUyOTQ2MjA4NzMsImV4aXN0aW5nIjpmYWxzZX0=; FPID=FPID2.2.hwJY%2FEU65fsKOkMRZ0Y8IhP28YhSl9w7pcfXWM%2BlAoI%3D.1725294306; FPLC=ZarjNUZ9QTQ9SgwOIquiSmDDypkn9rDtpm%2BcTKiMi9TCluuyNc7XWrKhBAwCmL3cZaOc9OiWAThPAMe%2BAaJmvHXi2SWAx8iXr1IF3QTlQB%2B67ZLTxt16w1mPxaDc1w%3D%3D; dtCookie=v_4_srv_9_sn_A67064305CF6A5088CC0F4CE2A64C546_perc_100000_ol_0_mul_1_app-3A93fb5a7425baf99b_1_app-3A6caf7d1c4abbb4b3_0_app-3A1eba319656f7eebb_0_rcs-3Acss_1; _ga_YYYYYYYYYY=GS1.1.1725294314.1.1.1725295485.0.0.915183076; _abck=43AD960CB27EA72603491A59FDF27B34~0~YAAQ5FJNGyPVIZmRAQAAV+rEswzGvCSg5vhnokRxpK88NVJnaICjK4i4PNiFCnMLKvxI92uX9iZ8lQhKg5UlVJv5fF4+58T6w0KCJ5N/tB6XbeWa8A+9buTs7+2pBYC4Koo4DXcRRv3eiE9rzrO01+l1cubtOwVlvbBHFb9yb3BrSmD/gXbnON5loMi4lIDwVvnuSYnnEPeejAjtBwmbRNb3K9qtGRHX6CK6P12kWYpQl0B2RleyZZwzsKzRiRPRr+TiqTkEUd6pzF/GbDQGzvMyUYi4M/Dth9IRHtMz6vz3evz8S4SU+Z7D4fHatbhrjb8DEKRq2JYj8rd9VKi2yDgxZ7EwUQiFpdDn+wlFTIiq3vWa5vS2OIucTbBsysyDoWrcvyn9PUZjdI0Dm0IEiqeWOhGBWTYDuBpGmMPbB4CsfzQELgaJGkWM5Xajy6ZeRjwHccnFPpJjoN3svAyLpr+9JdrJC9J8UOaofVIqAgwki1w0YnNbKO2OiMxn9yBSrTqDt7eY//Q=~-1~-1~-1; bm_sz=E9877A385C9F040B9A0F87F35424561D~YAAQ5FJNGyXVIZmRAQAAV+rEsxhpPbYah65Bf20vO6Dq6+clMfVRBRde4xtOahB5EbHi+K/9OtxICYeygjItUFT9h9ym9FihWJzXVXffg0RrAzv1wOPPW+Mba8BeeGgX74N+uXgFWlic/+DoVFDlIcoxh+mZDZT/LTiMPQgZZoNTkBGejfrrof6kmssdiyMIM7zR3EAzmvp4Cf/5RFCCQmGR2XrsOlB8l16e6VGe1cGClt7GHdn/66KHzUWBBO1PDrpFPOJoq4XTdBajBtn9bgZnssytU0u4DToL2IbOVjthW6wYURZ83C9PGvRS3HVrZgFU4yGxvGF/fxbogPJqKUeVebrr4bnN3JqTM+srCyn3WspRHXrUhxkL0i1ZdE4aQqRIa2mD2YFJAbLNLXsLUMUuLTQfwYk2YP/I6c73isqxy8Co+tKatbz7/QqTDKPu/PQTP+K9oEqrIsupdSzFiJWM1Ax65QVGFZcL0bkC//4kMvsDF5QCAS0HaGWec/cTiEK/S3GelWRB3B1vF4GvMV5nq69vTOFxTg==~3618355~3421506; bm_sv=31D7BB6E58331CBB8B24108E06262E05~YAAQ5FJNGz/WIZmRAQAAUBvFsxjAg4RZ4hKzMRnRZ0KDf03XjRMExbdvHL0fExMh+S3UhTO5UA6DEUKaRcahRH9+BG97DfJiQSCFHzKGp3jtaRsMhTfuQGULfkOEbCNezHskjsLg8UrvylFncwhNVRaorcjzW7K52x/qQqKIU/nbUEANUnP7FgQmR5ffGO7IsY5qOleqL5JAx6juR3WjTE+vJPNDKAZNAoTFaV9GT7IH4lCQjczaFyUG5cL/oqjaIZtwL+A=~1; _ga_P7JFFQ1HW2=GS1.1.1725297491.2.1.1725297924.54.0.0; rxvt=1725299755147|1725294304505; dtPC=9$295485932_641h76vTNFDQCBJPAMTHCOTEEHCCVRJDUAHJJMK-0e0',
    'origin': 'https://www.lifemiles.com',
    'priority': 'u=1, i',
    'realm': 'lifemiles',
    'referer': 'https://www.lifemiles.com/',
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
}

json_data = {
    'internationalization': {
        'language': 'en',
        'country': 'us',
        'currency': 'usd',
    },
    'currencies': [
        {
            'currency': 'USD',
            'decimal': 2,
            'rateUsd': 1,
        },
    ],
    'passengers': 1,
    'od': {
        'orig': 'JFK',
        'dest': 'LHR',
        'depDate': '2024-11-20',
        'depTime': '',
    },
    'filter': True,
    'codPromo': None,
    'idCoti': '792066726487667214',
    'officeId': '',
    'ftNum': '',
    'discounts': [],
    'promotionCodes': [
        'DBEP36',
    ],
    'context': 'D',
    'channel': 'COM',
    'cabin': '1',
    'itinerary': 'OW',
    'odNum': 1,
    'usdTaxValue': '0',
    'getQuickSummary': False,
    'ods': '',
    'searchType': 'AVH',
    'searchTypePrioritized': 'AVH',
    'sch': {
        'schHcfltrc': 'xAQL/r6euF/VOdJ+tiH+7i0rZkPNA521bqdEBAvTqQM=',
    },
    'posCountry': 'VN',
    'odAp': [
        {
            'org': 'JFK',
            'dest': 'LHR',
            'cabin': 1,
        },
    ],
    'suscriptionPaymentStatus': '',
}


response = crequests.post(
    'https://api.lifemiles.com/svc/air-redemption-find-flight-private',
    cookies=cookies,
    headers=headers,
    json=json_data,
    impersonate="chrome124",
)

# response = crequests.post(
#     'https://api.lifemiles.com/svc/air-redemption-find-flight-private',
#     cookies=cookies,
#     headers=headers,
#     json=json_data,
#     impersonate="chrome124",
# )


# Note: json_data will not be serialized by requests
# exactly as it was in the original request.

# data = '{"internationalization":{"language":"en","country":"us","currency":"usd"},"currencies":[{"currency":"USD","decimal":2,"rateUsd":1}],"passengers":1,"od":{"orig":"JFK","dest":"LHR","departingCity":"New York","arrivalCity":"London","depDate":"2024-12-09","depTime":""},"filter":false,"codPromo":null,"idCoti":"467093494961872669","officeId":"","ftNum":"","discounts":[],"promotionCodes":["DBEP36"],"context":"D","ipAddress":"171.247.9.19","channel":"COM","cabin":"1","itinerary":"OW","odNum":1,"usdTaxValue":"0","getQuickSummary":false,"ods":"","searchType":"SMR","searchTypePrioritized":"SSA","sch":{"schHcfltrc":"xAQL/r6euF9nL68QTDE+T1Xlzb6x513sQoyWhnhiV2E="},"posCountry":"VN","odAp":[{"org":"JFK","dest":"LHR","cabin":1}],"suscriptionPaymentStatus":""}'
# response = crequests.post(
#    'https://api.lifemiles.com/svc/air-redemption-find-flight-private',
#    cookies=cookies,
#    headers=headers,
#    data=data,
# )

print(f">>>>>>>>>>>>>>>..{response.status_code}")
try:
    data = response.json()
    with open(f"test_av.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f">>>>>>>>>>>>>>>..{data}")
except:
    print(f"error: {response.text}")