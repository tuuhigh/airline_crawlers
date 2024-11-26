import requests
from botasaurus_requests import request
from botasaurus_driver.user_agent import UserAgent
from curl_cffi import requests as crequests
import json
proxy_user = "ihgproxy1"
proxy_pass = "ihgproxy1234_country-us"
proxy_host = "geo.iproyal.com"
proxy_port = "12321"

proxy_attr = {
    "http": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
    "https": f'http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}',
}
cookies = {
    '_transaction_id': '',
    'VSSESSION': 'l0F4OIJ79n4njsZ0CGkpl8wgO2-mjCj2dUuQzJla.aa-orbflsearch-33-8c72f',
    '__gtm_pageLoadTimes': '{"/orb_chooseflight":1725549507921}',
    'AKAMAI_SAA_COUNTRY_COOKIE': 'VN',
    'AKAMAI_SAA_LOCALE_COOKIE': 'en_UK',
    'FARE_DEALS_LISTING_COOKIE': 'false',
    '_cls_v': '0f400e6a-0ab2-4f64-a5e3-d48b8ccc3bf0',
    '_fbp': 'fb.1.1718735453282.98088518743225044',
    '__qca': 'P0-1599368743-1718735453416',
    'AKAMAI_HOME_PAGE_ACCESSED': 'true',
    'rememberMeCookie': 'silverado5160@gmail.com',
    '_gac_UA-17015991-1': '1.1722015851.CjwKCAjwko21BhAPEiwAwfaQCDr9H-RV1LoK49t0RAINWBj_17bN_JNl58X_VAKZz6HvouXgsY2gxBoC6fgQAvD_BwE',
    '_gcl_gs': '2.1.k1$i1722015849',
    '_gcl_aw': 'GCL.1722015868.CjwKCAjwko21BhAPEiwAwfaQCDr9H-RV1LoK49t0RAINWBj_17bN_JNl58X_VAKZz6HvouXgsY2gxBoC6fgQAvD_BwE',
    '_gcl_dc': 'GCL.1722015868.CjwKCAjwko21BhAPEiwAwfaQCDr9H-RV1LoK49t0RAINWBj_17bN_JNl58X_VAKZz6HvouXgsY2gxBoC6fgQAvD_BwE',
    'LOGIN_POPUP_COOKIE': 'false',
    '_ga': 'GA1.1.2021632100.1718735453',
    'itm_source': 'hm_masthead_sea_sqvn_ta_aug24',
    'AKAMAI_SAA_AIRPORT_COOKIE': 'SIN',
    'RU_LOGIN_COOKIE': 'false',
    'SQCLOGIN_COOKIE': 'false',
    'cookieStateSet': 'hybridState',
    'AKAMAI_SAA_KF_TIER_COOKIE': 'K',
    'hybridState': 'ALLOWED',
    'emcid': 'F-IpdvhvYtI',
    'saadevice': 'desktop',
    'AKAMAI_SAA_DEVICE_COOKIE': 'desktop',
    '6b29450cab647be0f08ef134c7afc9a1': '8c88796e70dc9a710686b10f97ae28c2',
    'dtCookie': 'v_4_srv_7_sn_38118F60C6217A577C437C50F8509D94_perc_100000_ol_0_mul_1_app-3A7bacf3aecd29efdf_1',
    'hvsc': 'true',
    'bm_mi': '8B8BECC4882080B1637DC34A5573897E~YAAQ31JNGyL2dZeRAQAASSCMwhll7VZbQmlX/ZSUAjAwRqAXeytRmUx+n0rwGhrrNcbW9lE4vPbF18I2RUDThIwRJNwfan+rANJNYk8CFLUDT+ixvdOjP8GsFrXow5lE4608ZjeRo9leR48R86dlMb+UBiIGZzFwuaocReCjehrr9NlIn7ppkzzdn5yDlCtZe/Ya9mnAt+1dvMUL+LqvFZO4FY7Qmt+kyEBaMBvoDRTPJAYop3Wr/AuaRj+ysua/KMSwoTIUBfT6AGOyyza/GnSmP6Fx2lJ8O9GghlyIC8W6GQLzMV8A1TOsTbMPfpxprgWZv+2w6u/I9AznYf0=~1',
    'rxVisitor': '1725545847639P03NAOP0A53ULD1SIQI4VJIQ2RLBJ4NM',
    '_cls_s': '5f1028f7-782a-4863-840e-cde51e410333:1',
    'rto': 'c0',
    'ak_bmsc': '870333A6EF2CADAF885AA13468950B9A~000000000000000000000000000000~YAAQ31JNG3X2dZeRAQAAnSqMwhlgT6xmny3lf/p6hPBZd8v0iB1LOOgQ5yN7sMi6v8kw157quwYacUPmgD39su5yyxvsqI/Mdyus0nLSRsJP9fTF7aGOBBpxxi5KO/0PCYKx4FPgevqrYhbQRQSmnYCimsfGmevPPAtZtGh8E/V+d6XCxYrzUI00xumSNi+G4lWs4G25uChi8HHnY55x7C9bbnJ38Gs/ONB+7jkeCHRazkQXhEBln8IDEqQAzMgBvPSQhu3lu6/I80jNhxjQ/r/d/1BRMzOD19JHRKFKFVgsyKE889F80WIc7BpH0TZi+/VUNqU7ql0zrN2c84uFmdQjwRVnrVXzdDJz8/YuzOzsbeAkutKmO6G8mnhFKgufHNTIvHqesDeadbb5DLNTgVsyrmerkwvmjw8wdHhjsqON/VCpjOFK7687i3IA/KyeQqXieku5Xb/rBzD5LDn1HRrbg360hf51lY38atQwGjnEm2O3DIW2LqcwB1Jmew==',
    'JSESSIONID': '8KPCjCufoZuA2EUEVcl6KBsJXbC_kzriOvtvy4D_mLN4hgmVA6qi!-1551670046',
    'AKAMAI_SAA_DEVICE_COOKIE': 'desktop',
    '3ba97d27af5935dec41e5b77d437b307': '6cf28cfa7b7a16a536e01314108e0e3b',
    'ndcd': 'wc1.1.w-729460.1.2.knIPY6eWZ37GsZOqrQ6Fdg%252C%252C.yyYxK8Eyc4rMWV_OI_j-FsAI6hsDjm5U-DpDz-8fnG-GI5zQ2q4OIHAiK_IWJ34UogFdLIUOopvkhY2S00WxNAoWw8kURHV7jvz6ZZlMSvCBRdM2Rm65RKPdAUxrTz-zHE7KzWAjb9yrSG1MjywKJHaLKgR4lv4xI6684ZWze7pif46JQOC2LYvHAop-_g66',
    '_gcl_au': '1.1.664431811.1718735453.1447416254.1725546665.1725546664',
    'LOGIN_COOKIE': 'true',
    'VSUUID': '03b919cea16e5eda789c0f0c90de29a8e7b88d58a3c77811c1750d278d0621b2.saa-home-56-bwbwr.1725546669688',
    'kfMagic': 'K_5fe445ab2603ddd9c32cf01e4a81b192a8f83855f802435a8c54453e63d95bdf',
    'AWSALB': 'zuT9re7+BqOGr+c6fKUPEmDXwYp2Va7HBBqkzawVrpFEv7yWpyFsvKyKw+BxWTExEhFMzKQ9AWkHmwu5/MsATmPWvSjgZgPZFwSNLLJHNAA9z2nHtKC42pi8gKBA',
    'AWSALBCORS': 'zuT9re7+BqOGr+c6fKUPEmDXwYp2Va7HBBqkzawVrpFEv7yWpyFsvKyKw+BxWTExEhFMzKQ9AWkHmwu5/MsATmPWvSjgZgPZFwSNLLJHNAA9z2nHtKC42pi8gKBA',
    'disableXB': 'true',
    'bcd4e19bb5e920747bf377600682edcf': '5857fa8d0450992eb58e0325999e4de1',
    'HSESSIONID': 'bSHidoZE8ZCcyTzRqeaSmheXVtW3gnPRVp42vDCI.saa-home-56-bwbwr',
    'AKA_A2': 'A',
    'SEARCH_SAA_CIB_COOKIE': 'HAN|SIN|O|25/10/2024|economy|1|0|0|05/09/2024 23:17:37|SIN',
    'bm_sz': '74943A2BC96A69DB72FA1B2A794CB558~YAAQ31JNG78JeJeRAQAAvDDQwhmau6gP5xwRyWMSiYF0jEeg2GtVyibBMZPi70FaRu0s5EqONwR+qBchAPmEgrD+AteF99mO+XC1Y2YnZrM1QUuP/7UOGW5Ql7mzEWl6Dx1wIt0LZpEtwLsk6Z9UEEk8SEaneZiN02/3AwUMBd+6TtDI3MfW/0yvojSHALF03dVOcpqROYLao6AnexavV4ttlv5NOHvvkUIR/wh/2mj+fjJ6ASKS6Ac+HcxiNjBRNm9FepIj9qpFZa0y3tyT5cCtR3bkYp44wmXmrUP/snnGsJQH/hCZkXOEF0ozdbZscVQytotIt7kR9ywtFVPz7u7h3FCrmdNhDwxmk5p3hLvPINeHpMSqCnlmLfATcjzuVv5khhCVMHDevNXXxmt6yJesy3h7Qwacw3Wg5n/CiwfVqeA1AMbGCk1VMwTO1MZ+5+3XnVykwt82vr6hXDhIoBZ4nPwKYSdrGv6yeSekWM0DF8tcNii8E4dJ5xz9yrO70FGuxDoXv3HK00vJB64ZGQDqQ3EqwVV0xR58a9k=~4276784~4338245',
    'rxvt': '1725552112225|1725549108923',
    'dtPC': '7$550309859_736h-vPOPHURKNAAMIJPGHQREBKSCMWHKRLHUF-0e0',
    '_uetsid': '824aeb606a1b11ef8d11ebb00a6445c7',
    '_uetvid': 'e5230f502da011efb8b7c7ec6a2b3fd8',
    'CIB_SEARCH_HISTORY_0': 'SGN|SIN|O|12/10/2024|economy|1|0|0|05/09/2024 10:31:50|SIN',
    'CIB_SEARCH_HISTORY_1': 'HAN|SIN|O|25/10/2024|economy|1|0|0|05/09/2024 11:17:37|SIN',
    'dtSa': 'true%7CC%7C-1%7CSEARCH%7C-%7C1725550341440%7C550309859_736%7Chttps%3A%2F%2Fwww.singaporeair.com%2Fen_5FUK%2Fvn%2Fhome%3FerrorCategory%3DflightsearchORB%26errorKey%3DflightSearch.noFlight%7C%7C%7C%2Fbook%2Fredeemflight%7C',
    '_ga_9L60TJMNML': 'GS1.1.1725549420.12.1.1725550341.28.0.0',
    'bm_sv': '0817995536DCC03A4FD4E4D9541B7CCD~YAAQ31JNG5sNeJeRAQAAvq/QwhmNQ//Fx4Wcd/Ebq3SkQr3Md58NK4F6sHRMpFA7QOzSp/fzgdZFh24P20ICOqWgAm9RYCcWT0u78VFk+7hmwl01QLn1q/jWn6PqClH+Om94oN7BNcV4g96mM3AVcJDZ5Vum9bJhNdphoSkoGUDHYIq7LPLgTOYHX75iBJ5mAkfWyqWcbUB7QOJXp4QWFVr+aNqVOCH7U8IOc5Xyp1dd1x2FgsbxeibtlhDx7CTrN5mcUa7JJ9Y=~1',
    '_abck': '75081EA01F840B801FD852FAD988454D~-1~YAAQ31JNG8sNeJeRAQAAk7bQwgz/EEfZSXS2rmwSPiVEGx7i1WwAxniL6+jTwopqHI0xU81sBgZrwgQs2L7Iz78Dgj+NhRQ/5rqyrNfiSVfdCHVuI1sfvZ3J7Od+E+faP2ffAPnOpUTeVBB7uWjE+RDimmdj//xyrVgDfTlESDIWyphy0bwULgLbzetvaFif2kTfAfbgxfgubNkifV/wzHw9b7XIPs2WUwfWcKgqTeu/rcXABC/QVdN1lOYnC3nNdcsYvqx24AQJwLMKaIacTteCPUo4csnLz2SkVhNwkkkPCxnY6gtcTlSaV2A4nGpPhuRlqNPcx7yNTqrgJ26pji8E63a2QPZVRoYWhElEsPk0GqwDfgaOqNJ8e6V88Tu5Jp6RMFfZQJMG+QuETGxbN9pqhlbUf73L90ABSDus5Fn7aTOB0citNujTKDV3Sip71yFpix2gNI3zcrLenaCaaPEIGHS93S7x+NWUwss3up0YjwFu2fLIt+kVSl+AKLJHWSmennVNMGVTrZWbkbIkzuR5G/2xndQQpOtdHVGaIJwqbXUzo39Yy1tJf/H70kUZROB8kLkKJBe9mjxs3gophE7sOaXBQ8/LjmglzzX50vgel2m7ASHU3XZt3lDWDAHU3tvr2ajPSwX9lIMmE0Bpu4l/L3x8d3Wv2Eri9Pl7CGm54W2IMv45A6+H2inDT0C/xje9bdNABxRG6kRrEQ==~-1~-1~-1',
    'sec_cpt': '5C1E80FA8D4B3B5CA4FC5BA60D35392A~3~YAAQ31JNG2AOeJeRAQAAtMzQwguU2vkb27XuDAHOENPNl/E6YojLMqlDG+V8qB+sy5yMlG7OSWN1ypGQo0oUs03D6Fn+YweUiEv64UkRoqU879edE01TSrOea3LxcTzCX9uqX/hbgfRg8oEQwVroLZBHjYAtbzPQO/HfKHKJJxis2ydwCV9C+uRb7B3CwHq0kw7acEFJ2OtReXn4xqwCSOGGkEV+KchbT2wKEMAl+iqgE8wQnjnq5jKoRIPYKjnxnJ5612PchakT5/u60Xk9SBwdDghvIHAlhLFUV6CTGPyWtt84z/HCD5kYiT0fPyIp6cSXA6/V7jeliW7p/Tn7sAFpfkdupGak94wka6LO0VFA4C/Xs5mAayrFezegbxCV6kZ09jUZ6fbdK1vOSqThKY/cLABtCpjSvEHsDAos/KpghnJk1L8T2ttZ6LHBOhnPuezf9nHPHSg9Y78pEDyMkf1UFY+gAZClwLGMql2E5xQoc/SyfKx3u1TX/KBm6ZcEB8YooglHmPhZDHs2ILQQh1gFYPJ4HzlLWMGNVlRODh6NyS8iKNEUieB0zGxvVC2WxZgQfBIGaf7e70PWo/CuR+qHPQTbib2QZtVbvMgW1B1RsjRCHwFOE6n2Xqjkx9iFXrth1Ave9bJSWtit5V1djc0gRjdfjiHWi0O1w/SbTZKNj/ScKBQc2/m79cHeDwlI5zlUit5nCArBC8hUlUNsGO02pAnptIhtXYfkNdiiS610o2ZN1uf445AbSvNtilx4RGucQKOmHIXqSNIi8S1vuKTxkAWl2xBg9o3GRSF2dibfD5TeJ3eSLmc/+pYOO+ati1PD6f06cu50EnXrKmx8Bjte4lzl4irMyt3fdZwgvnjS+/8fHfl+VBFewwvXZlH4Juyv2a5A3/n7zJxVqwe2fdrbUhv3awJJ143H1LKfnlHOa0KmYjqS2ezTgNONq6KpbvOsRFVoX2rJAffd4wraW8UdPFBEy/3AG2CiQu9siBGtSwYY9K/t+w==',
    'RT': '"z=1&dm=singaporeair.com&si=a19d35ab-72aa-4604-99ac-19a1520f6112&ss=m0pdg0yx&sl=k&tt=ax8&obo=g&rl=1&ld=2oi0l&r=je7j8xhu&ul=2oi0n"',
}
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
    'cache-control': 'max-age=0',
    'content-type': 'application/x-www-form-urlencoded',
    # 'cookie': '_transaction_id=; VSSESSION=l0F4OIJ79n4njsZ0CGkpl8wgO2-mjCj2dUuQzJla.aa-orbflsearch-33-8c72f; __gtm_pageLoadTimes={"/orb_chooseflight":1725549507921}; AKAMAI_SAA_COUNTRY_COOKIE=VN; AKAMAI_SAA_LOCALE_COOKIE=en_UK; FARE_DEALS_LISTING_COOKIE=false; _cls_v=0f400e6a-0ab2-4f64-a5e3-d48b8ccc3bf0; _fbp=fb.1.1718735453282.98088518743225044; __qca=P0-1599368743-1718735453416; AKAMAI_HOME_PAGE_ACCESSED=true; rememberMeCookie=silverado5160@gmail.com; _gac_UA-17015991-1=1.1722015851.CjwKCAjwko21BhAPEiwAwfaQCDr9H-RV1LoK49t0RAINWBj_17bN_JNl58X_VAKZz6HvouXgsY2gxBoC6fgQAvD_BwE; _gcl_gs=2.1.k1$i1722015849; _gcl_aw=GCL.1722015868.CjwKCAjwko21BhAPEiwAwfaQCDr9H-RV1LoK49t0RAINWBj_17bN_JNl58X_VAKZz6HvouXgsY2gxBoC6fgQAvD_BwE; _gcl_dc=GCL.1722015868.CjwKCAjwko21BhAPEiwAwfaQCDr9H-RV1LoK49t0RAINWBj_17bN_JNl58X_VAKZz6HvouXgsY2gxBoC6fgQAvD_BwE; LOGIN_POPUP_COOKIE=false; _ga=GA1.1.2021632100.1718735453; itm_source=hm_masthead_sea_sqvn_ta_aug24; AKAMAI_SAA_AIRPORT_COOKIE=SIN; RU_LOGIN_COOKIE=false; SQCLOGIN_COOKIE=false; cookieStateSet=hybridState; AKAMAI_SAA_KF_TIER_COOKIE=K; hybridState=ALLOWED; emcid=F-IpdvhvYtI; saadevice=desktop; AKAMAI_SAA_DEVICE_COOKIE=desktop; 6b29450cab647be0f08ef134c7afc9a1=8c88796e70dc9a710686b10f97ae28c2; dtCookie=v_4_srv_7_sn_38118F60C6217A577C437C50F8509D94_perc_100000_ol_0_mul_1_app-3A7bacf3aecd29efdf_1; hvsc=true; bm_mi=8B8BECC4882080B1637DC34A5573897E~YAAQ31JNGyL2dZeRAQAASSCMwhll7VZbQmlX/ZSUAjAwRqAXeytRmUx+n0rwGhrrNcbW9lE4vPbF18I2RUDThIwRJNwfan+rANJNYk8CFLUDT+ixvdOjP8GsFrXow5lE4608ZjeRo9leR48R86dlMb+UBiIGZzFwuaocReCjehrr9NlIn7ppkzzdn5yDlCtZe/Ya9mnAt+1dvMUL+LqvFZO4FY7Qmt+kyEBaMBvoDRTPJAYop3Wr/AuaRj+ysua/KMSwoTIUBfT6AGOyyza/GnSmP6Fx2lJ8O9GghlyIC8W6GQLzMV8A1TOsTbMPfpxprgWZv+2w6u/I9AznYf0=~1; rxVisitor=1725545847639P03NAOP0A53ULD1SIQI4VJIQ2RLBJ4NM; _cls_s=5f1028f7-782a-4863-840e-cde51e410333:1; rto=c0; ak_bmsc=870333A6EF2CADAF885AA13468950B9A~000000000000000000000000000000~YAAQ31JNG3X2dZeRAQAAnSqMwhlgT6xmny3lf/p6hPBZd8v0iB1LOOgQ5yN7sMi6v8kw157quwYacUPmgD39su5yyxvsqI/Mdyus0nLSRsJP9fTF7aGOBBpxxi5KO/0PCYKx4FPgevqrYhbQRQSmnYCimsfGmevPPAtZtGh8E/V+d6XCxYrzUI00xumSNi+G4lWs4G25uChi8HHnY55x7C9bbnJ38Gs/ONB+7jkeCHRazkQXhEBln8IDEqQAzMgBvPSQhu3lu6/I80jNhxjQ/r/d/1BRMzOD19JHRKFKFVgsyKE889F80WIc7BpH0TZi+/VUNqU7ql0zrN2c84uFmdQjwRVnrVXzdDJz8/YuzOzsbeAkutKmO6G8mnhFKgufHNTIvHqesDeadbb5DLNTgVsyrmerkwvmjw8wdHhjsqON/VCpjOFK7687i3IA/KyeQqXieku5Xb/rBzD5LDn1HRrbg360hf51lY38atQwGjnEm2O3DIW2LqcwB1Jmew==; JSESSIONID=8KPCjCufoZuA2EUEVcl6KBsJXbC_kzriOvtvy4D_mLN4hgmVA6qi!-1551670046; AKAMAI_SAA_DEVICE_COOKIE=desktop; 3ba97d27af5935dec41e5b77d437b307=6cf28cfa7b7a16a536e01314108e0e3b; ndcd=wc1.1.w-729460.1.2.knIPY6eWZ37GsZOqrQ6Fdg%252C%252C.yyYxK8Eyc4rMWV_OI_j-FsAI6hsDjm5U-DpDz-8fnG-GI5zQ2q4OIHAiK_IWJ34UogFdLIUOopvkhY2S00WxNAoWw8kURHV7jvz6ZZlMSvCBRdM2Rm65RKPdAUxrTz-zHE7KzWAjb9yrSG1MjywKJHaLKgR4lv4xI6684ZWze7pif46JQOC2LYvHAop-_g66; _gcl_au=1.1.664431811.1718735453.1447416254.1725546665.1725546664; LOGIN_COOKIE=true; VSUUID=03b919cea16e5eda789c0f0c90de29a8e7b88d58a3c77811c1750d278d0621b2.saa-home-56-bwbwr.1725546669688; kfMagic=K_5fe445ab2603ddd9c32cf01e4a81b192a8f83855f802435a8c54453e63d95bdf; AWSALB=zuT9re7+BqOGr+c6fKUPEmDXwYp2Va7HBBqkzawVrpFEv7yWpyFsvKyKw+BxWTExEhFMzKQ9AWkHmwu5/MsATmPWvSjgZgPZFwSNLLJHNAA9z2nHtKC42pi8gKBA; AWSALBCORS=zuT9re7+BqOGr+c6fKUPEmDXwYp2Va7HBBqkzawVrpFEv7yWpyFsvKyKw+BxWTExEhFMzKQ9AWkHmwu5/MsATmPWvSjgZgPZFwSNLLJHNAA9z2nHtKC42pi8gKBA; disableXB=true; bcd4e19bb5e920747bf377600682edcf=5857fa8d0450992eb58e0325999e4de1; HSESSIONID=bSHidoZE8ZCcyTzRqeaSmheXVtW3gnPRVp42vDCI.saa-home-56-bwbwr; AKA_A2=A; SEARCH_SAA_CIB_COOKIE=HAN|SIN|O|25/10/2024|economy|1|0|0|05/09/2024 23:17:37|SIN; bm_sz=74943A2BC96A69DB72FA1B2A794CB558~YAAQ31JNG78JeJeRAQAAvDDQwhmau6gP5xwRyWMSiYF0jEeg2GtVyibBMZPi70FaRu0s5EqONwR+qBchAPmEgrD+AteF99mO+XC1Y2YnZrM1QUuP/7UOGW5Ql7mzEWl6Dx1wIt0LZpEtwLsk6Z9UEEk8SEaneZiN02/3AwUMBd+6TtDI3MfW/0yvojSHALF03dVOcpqROYLao6AnexavV4ttlv5NOHvvkUIR/wh/2mj+fjJ6ASKS6Ac+HcxiNjBRNm9FepIj9qpFZa0y3tyT5cCtR3bkYp44wmXmrUP/snnGsJQH/hCZkXOEF0ozdbZscVQytotIt7kR9ywtFVPz7u7h3FCrmdNhDwxmk5p3hLvPINeHpMSqCnlmLfATcjzuVv5khhCVMHDevNXXxmt6yJesy3h7Qwacw3Wg5n/CiwfVqeA1AMbGCk1VMwTO1MZ+5+3XnVykwt82vr6hXDhIoBZ4nPwKYSdrGv6yeSekWM0DF8tcNii8E4dJ5xz9yrO70FGuxDoXv3HK00vJB64ZGQDqQ3EqwVV0xR58a9k=~4276784~4338245; rxvt=1725552112225|1725549108923; dtPC=7$550309859_736h-vPOPHURKNAAMIJPGHQREBKSCMWHKRLHUF-0e0; _uetsid=824aeb606a1b11ef8d11ebb00a6445c7; _uetvid=e5230f502da011efb8b7c7ec6a2b3fd8; CIB_SEARCH_HISTORY_0=SGN|SIN|O|12/10/2024|economy|1|0|0|05/09/2024 10:31:50|SIN; CIB_SEARCH_HISTORY_1=HAN|SIN|O|25/10/2024|economy|1|0|0|05/09/2024 11:17:37|SIN; dtSa=true%7CC%7C-1%7CSEARCH%7C-%7C1725550341440%7C550309859_736%7Chttps%3A%2F%2Fwww.singaporeair.com%2Fen_5FUK%2Fvn%2Fhome%3FerrorCategory%3DflightsearchORB%26errorKey%3DflightSearch.noFlight%7C%7C%7C%2Fbook%2Fredeemflight%7C; _ga_9L60TJMNML=GS1.1.1725549420.12.1.1725550341.28.0.0; bm_sv=0817995536DCC03A4FD4E4D9541B7CCD~YAAQ31JNG5sNeJeRAQAAvq/QwhmNQ//Fx4Wcd/Ebq3SkQr3Md58NK4F6sHRMpFA7QOzSp/fzgdZFh24P20ICOqWgAm9RYCcWT0u78VFk+7hmwl01QLn1q/jWn6PqClH+Om94oN7BNcV4g96mM3AVcJDZ5Vum9bJhNdphoSkoGUDHYIq7LPLgTOYHX75iBJ5mAkfWyqWcbUB7QOJXp4QWFVr+aNqVOCH7U8IOc5Xyp1dd1x2FgsbxeibtlhDx7CTrN5mcUa7JJ9Y=~1; _abck=75081EA01F840B801FD852FAD988454D~-1~YAAQ31JNG8sNeJeRAQAAk7bQwgz/EEfZSXS2rmwSPiVEGx7i1WwAxniL6+jTwopqHI0xU81sBgZrwgQs2L7Iz78Dgj+NhRQ/5rqyrNfiSVfdCHVuI1sfvZ3J7Od+E+faP2ffAPnOpUTeVBB7uWjE+RDimmdj//xyrVgDfTlESDIWyphy0bwULgLbzetvaFif2kTfAfbgxfgubNkifV/wzHw9b7XIPs2WUwfWcKgqTeu/rcXABC/QVdN1lOYnC3nNdcsYvqx24AQJwLMKaIacTteCPUo4csnLz2SkVhNwkkkPCxnY6gtcTlSaV2A4nGpPhuRlqNPcx7yNTqrgJ26pji8E63a2QPZVRoYWhElEsPk0GqwDfgaOqNJ8e6V88Tu5Jp6RMFfZQJMG+QuETGxbN9pqhlbUf73L90ABSDus5Fn7aTOB0citNujTKDV3Sip71yFpix2gNI3zcrLenaCaaPEIGHS93S7x+NWUwss3up0YjwFu2fLIt+kVSl+AKLJHWSmennVNMGVTrZWbkbIkzuR5G/2xndQQpOtdHVGaIJwqbXUzo39Yy1tJf/H70kUZROB8kLkKJBe9mjxs3gophE7sOaXBQ8/LjmglzzX50vgel2m7ASHU3XZt3lDWDAHU3tvr2ajPSwX9lIMmE0Bpu4l/L3x8d3Wv2Eri9Pl7CGm54W2IMv45A6+H2inDT0C/xje9bdNABxRG6kRrEQ==~-1~-1~-1; sec_cpt=5C1E80FA8D4B3B5CA4FC5BA60D35392A~3~YAAQ31JNG2AOeJeRAQAAtMzQwguU2vkb27XuDAHOENPNl/E6YojLMqlDG+V8qB+sy5yMlG7OSWN1ypGQo0oUs03D6Fn+YweUiEv64UkRoqU879edE01TSrOea3LxcTzCX9uqX/hbgfRg8oEQwVroLZBHjYAtbzPQO/HfKHKJJxis2ydwCV9C+uRb7B3CwHq0kw7acEFJ2OtReXn4xqwCSOGGkEV+KchbT2wKEMAl+iqgE8wQnjnq5jKoRIPYKjnxnJ5612PchakT5/u60Xk9SBwdDghvIHAlhLFUV6CTGPyWtt84z/HCD5kYiT0fPyIp6cSXA6/V7jeliW7p/Tn7sAFpfkdupGak94wka6LO0VFA4C/Xs5mAayrFezegbxCV6kZ09jUZ6fbdK1vOSqThKY/cLABtCpjSvEHsDAos/KpghnJk1L8T2ttZ6LHBOhnPuezf9nHPHSg9Y78pEDyMkf1UFY+gAZClwLGMql2E5xQoc/SyfKx3u1TX/KBm6ZcEB8YooglHmPhZDHs2ILQQh1gFYPJ4HzlLWMGNVlRODh6NyS8iKNEUieB0zGxvVC2WxZgQfBIGaf7e70PWo/CuR+qHPQTbib2QZtVbvMgW1B1RsjRCHwFOE6n2Xqjkx9iFXrth1Ave9bJSWtit5V1djc0gRjdfjiHWi0O1w/SbTZKNj/ScKBQc2/m79cHeDwlI5zlUit5nCArBC8hUlUNsGO02pAnptIhtXYfkNdiiS610o2ZN1uf445AbSvNtilx4RGucQKOmHIXqSNIi8S1vuKTxkAWl2xBg9o3GRSF2dibfD5TeJ3eSLmc/+pYOO+ati1PD6f06cu50EnXrKmx8Bjte4lzl4irMyt3fdZwgvnjS+/8fHfl+VBFewwvXZlH4Juyv2a5A3/n7zJxVqwe2fdrbUhv3awJJ143H1LKfnlHOa0KmYjqS2ezTgNONq6KpbvOsRFVoX2rJAffd4wraW8UdPFBEy/3AG2CiQu9siBGtSwYY9K/t+w==; RT="z=1&dm=singaporeair.com&si=a19d35ab-72aa-4604-99ac-19a1520f6112&ss=m0pdg0yx&sl=k&tt=ax8&obo=g&rl=1&ld=2oi0l&r=je7j8xhu&ul=2oi0n"',
    'origin': 'https://www.singaporeair.com',
    'priority': 'u=0, i',
    'referer': 'https://www.singaporeair.com/redemption/searchFlight.form',
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
}
cookies2 = cookies.update({
    'ORB_SEARCH_HISTORY_2': 'SGN|SIN|O|13/11/2024|business|1|0|0|05/09/2024 22:46:32|SIN'
})
data = {
    '_payByMiles': 'on',
    'payByMiles': 'true',
    'fromHomePage': 'true',
    'orbOrigin': 'SGN',
    'orbDestination': 'SIN',
    '_tripType': 'on',
    'tripType': 'O',
    'departureMonth': '2024-11-13',
    'returnMonth': '',
    'cabinClass': 'J',
    'numOfAdults': '1',
    'numOfChildren': '0',
    'numOfInfants': '0',
    'flowIdentifier': 'redemptionBooking',
    '_eventId_flightSearchEvent': '',
    'isLoggedInUser': 'true',
    'numOfChildrenNominees': '1',
    'numOfAdultNominees': '1',
    'flexibleDates': 'off',
}

# session = request.Session()
response = crequests.post(
    'https://www.singaporeair.com/redemption/searchFlight.form',
    cookies=cookies, 
    headers=headers,
    proxies=proxy_attr,
    data=data
)
# print(f"response0: >>>>>>>>>>>>>>>..{response.status_code}")
# print(session.cookies.get_dict())

# response = session.get(
#     'https://www.singaporeair.com/redemption/loadFlightSearchPage.form', 
#     # cookies=cookies2, 
#     headers=headers,
#     # user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
#     # impersonate="chrome124",
# )
print(f">>>>>>>>>>>>>>>..{response.status_code}")
try:
    if response.status_code == 200 and 'pageData = ' in response.text:
        page_data_content = response.text.split('pageData = ')[-1].split('var ajax_urls')[0]
        page_data_content = page_data_content.strip().strip('; ')
        page_data = json.loads(page_data_content)
        with open(f"test_sq.json", "w") as f:
            json.dump(page_data, f, indent=2)
        print(f">>>>>>>>>>>>>>>..{page_data}")
    else:
        print(f">>>>>>>>>>>>can't find pageData")
except:
    print(f"error: {response.text}")