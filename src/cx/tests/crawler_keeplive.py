from botasaurus_requests import request
cookies = {
    '_hjSessionUser_358709': 'eyJpZCI6ImZiODU1MTZiLWUzYjUtNTQ2Ny04ZTcwLTQ2YWMyNGRiODQ5NiIsImNyZWF0ZWQiOjE3MTg5MDY3OTAwMzMsImV4aXN0aW5nIjp0cnVlfQ==',
    'visid_incap_2313958': 'yy9WrmdnTX+AsOUIOYCmcRNwdGYAAAAAQUIPAAAAAADNGA8g5jGxlkEZKseRp0IS',
    'f83b3ad950411e3414e1276ee43ce204': '754f48f9244e978570add1e2c08118a1',
    'optimizelyEndUserId': 'oeu1718906788977r0.8890886921400423',
    'AMCVS_21683A5857FCAE5A0A495DC5%40AdobeOrg': '1',
    's_ecid': 'MCMID%7C22117646739942201930851154590627858086',
    's_cc': 'true',
    '_fbp': 'fb.1.1724087717939.185826328575060335',
    'lastLoginType': '1',
    'LoginCookie': '0.7375161666185728',
    '_gcl_au': '1.1.1332212776.1724087761',
    '_ga': 'GA1.1.807630469.1724087761',
    '_yjsu_yjad': '1724087761.b4348c1a-9b9f-4308-aaf9-d3dcca1ad97d',
    '__tmbid': 'sg-1718906790-ea10012ba2424e20aacc1a705f6ced7d',
    'isLoggedIn': 'true',
    'polling_request': '0',
    'flights/_campaignpopup_display': 'false',
    'OptanonAlertBoxClosed': '2024-08-19T17:29:54.263Z',
    '056c1fd49d864b61a16255cdb7a82105': '75b8820dadbfe67faf6939321d59b10b',
    'dc85ac4f0435a31e4b9fb8eca9f182e7': '001df81b62af7751af65c05c6690bfab',
    'OPTOUTMULTI': '0:0%7Cc1:0',
    'nlbi_2313958': 'GjoIN/DT4S88MjEW1o+NvQAAAABB60WwhsZTWl7a/6yIJzAR',
    '56ca038ea46ddc63e5a9c230844ee843': '8b01d9b17c7553d079fdb0ff64eee09d',
    'incap_ses_573_2313958': 'LbhaclnvIiv7p1ODibTzBx+Bw2YAAAAAiW8mnWmbED+eOCE3OQDYVA==',
    '__clickidc': '172408860913986467',
    '_cls_v': '25a71a5c-02d6-448a-9592-b58afb746258',
    '_cls_s': '797df4c7-9b40-453c-a523-6d5fa85d3d01:0',
    'cbfw.sid': 's%3ASHhYM8SspJjOBpvodEz-j6iHiMBMwQyR.hfCg%2BCLL8m647CWu1vha%2Fed33PBUzMo7n0RqsYq63V8',
    'pxcts': 'b1b91a0a-5e50-11ef-966e-3ebd44f7b340',
    '_pxvid': 'b1b90a2b-5e50-11ef-966b-3a4f0fa21351',
    '__pxvid': 'b1f56262-5e50-11ef-bdcd-0242ac120003',
    'incap_ses_428_2313958': '2sLybK9bYE3j/QAqx4/wBf6Gw2YAAAAACcciuG1+57V4FE6Rx6wOUg==',
    'incap_ses_165_2313958': 'aAoKHzJ9+2SDUQPmxzJKAoqNw2YAAAAAkzZhqluUBOVVINeJ2WQBzg==',
    'incap_ses_1562_2313958': 'D0CfQ127fj84V6jC11atFQePw2YAAAAAxdt3JLz3osBQ7W4fj7J7YA==',
    'ak_bmsc': 'D5C6CF29865808556A84CFA4922F263D~000000000000000000000000000000~YAAQjlJNG66fvV+RAQAABK+TcBgsQOAF46JxHVjwPXUfSLWh+Y22nDNinFu+aYvv+iJm7B/5bDq0c+8+UiTMtMlbItY9JYWaRJRADPHSOccWolSPUeAn2JY8PdXGm6tP7B7cyi6Hip/xWxBkgQn9pBOaJSex9WChyVTm53/TpecXRpV/h9dMq0cNAiIVYfeJPG6jOhGBd7+4AKN5hGzbImKafcQVZNsk6AlkHIidLcn1OMZsuW2rMUxXAdDLe1t6EVGuOpPLAEND8YPkPA45nQVmhBYPxagRWpKJ6slE9+H7MHjxFwyvcKpWmTUu5/uHASom6vlosLUvzvQen1tPtK3mcrYM8dTAlU5+wo9B1fO//Cr+TG7UvWnHJVpkvjatvYwcVr4XxozXYWt1PMuDZBBqfODw1VYdoV6ctmrJXjIoKcfyxZEq0Bl1ZpE8xxWwTRzACwthOYJF6j0U/526PsjDBns=',
    'mlc_prelogin': '1',
    'CXMPO_JSESSIONID': '01549657-2aeb-4f9f-9189-030ce40eddd4',
    '_hjSession_358709': 'eyJpZCI6IjE0NzljMjJmLWFmZTYtNGI3ZS04YzU2LWI5OGUxZDViZDg1MiIsImMiOjE3MjQxNzMwNzA1NTAsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=',
    'QueueITAccepted-SDFrts345E-V3_milesflight': 'EventId%3Dmilesflight%26QueueId%3Dddff8332-2a15-45eb-9dd9-9c0b0a0a2cf7%26RedirectType%3Dsafetynet%26IssueTime%3D1724173078%26Hash%3D08cc74b7836304136761933a78442ffa400457c05a7a83d49549b0b299d63e5f',
    'RT': '"z=1&dm=cathaypacific.com&si=8b877fc3-eb53-459c-928c-6c631d069d74&ss=m02o4wr9&sl=0&tt=0"',
    'ADRUM': 's=1724174845944&r=https%3A%2F%2Fwww.cathaypacific.com%2Fverachatbot%2F%3F-1475824490',
    'incap_ses_1206_2313958': 'cE7lcTnSiW5UmOmppZK8EP3RxGYAAAAAjycwiyE845KT4cPFDUN7KA==',
    'XSRF-TOKEN': '0907731a-fbf1-4639-afb5-78e250ec3f08',
    'AKA_A2': 'A',
    'QueueITAccepted-SDFrts345E-V3_helloibefcfscom': 'EventId%3Dhelloibefcfscom%26QueueId%3Dd8ce7db1-a4b7-42df-b35b-1b4faf2df50a%26RedirectType%3Dsafetynet%26IssueTime%3D1724174972%26Hash%3Df019fdb1dd8b95c3e1c5a8d32273d88173cb6beaf963de3884fc59526c6ffbb4',
    'IBE_JSESSIONID': 'OTM1YzA4MDMtNmFjMi00NDU3LTgwMDMtZGJiMjY2ODRlMDQ2',
    '_abck': '3C8511AF26714CB396821042763FAC5F~0~YAAQhlJNG5a5/mmRAQAAYkzWcAzDQmy3ppRHFpq4mAbHlxw4hDfGHo6PnrwMeNfzUY18fQYmJqQNRj+vQ/8Z8n7Uxx5r0OMMx5TLOYWNeN1UKC7vPFC2c6M3xsMtkg0kJDZo7aCoeHTdHut/pTkRWDQz6uOzWuQJqya+bJdVWUB9oQ/gs/zd+3/RT31UApLUUe89SULmvBasbSZiUw8yw0Hs15HgOB6Lqhv1Zx1hbZ27aij2Yp8jBB6d4pmQtLNp/ui1XXwoinkYXGh8R6URgphu2YM96XIgCqe4CSVhNsgBjN7q9mTew7qWDwq/nS7Qmqb9H+aykFcBTyacexKU7QTFSh48b5yEdS4YwQxxR3LFr3VlnslF07IObuRMC4pwKJ948lCsLL5ALOsVT7fHgmwl11PVAzo3DPXtW+knjIZitokS7pE1ZJu809XttuiWgpLNtxxvqXPoL13kq40QUSNivFNEL7CEBPk=~-1~-1~-1',
    'bm_sz': 'A706DB96677E567AB81B886E0307618E~YAAQhlJNG5i5/mmRAQAAYkzWcBgfh8mmIUIHdJ9b42Sf3tf8LAROn2a85yd/RlYWdGEoPairDFaIZ3qOUsfgokjKy4BA+RVGRp1wWDNTb/PH2b+cLyS2DFYHUkn55CFJB0tiH+UNnEHjOfnj+/XrS0uEGdmMADUaW7kSyGwyeE9f9phh5bwAIVgoAmeCLfOatomObjFCN9WtA61CH7w1YkDr2W+Zg27VO0JB/30MpZSpyk72jEkDQ+Jo3wxStx1kVsNuKYEI4+PVUTQB2A9lkdDVM/CHvFv1/dOIjhyVGQdSZR5xGzziLX93ErYOwta1/oCcg60Qzvc/gMuEe2mA6RDebjbpGPzZQ6qu8lvobJvcx2fGq648tLI3fQIh8QYGRzJo28olRZge9OvWFc5rI0iAa5KGl1f/lRWS01TZ+bPGU4BQ8rHWNn+DFZF1+8zrN0Lfd6zrjXZsZdEJaxNHzLwg36Kt7LpxrtXAhpqP9BGMurSYSqwTw/9JSv1jNCK+12ADauHuSGZ6AUETh30DyF75c8KT6vlt0w4=~4601923~3553593',
    'AMCV_21683A5857FCAE5A0A495DC5%40AdobeOrg': '1176715910%7CMCIDTS%7C19955%7CMCMID%7C22117646739942201930851154590627858086%7CMCAAMLH-1724779780%7C3%7CMCAAMB-1724779780%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1724182180s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-19962%7CvVersion%7C5.4.0',
    'incap_ses_431_2313958': '/3JBMioC0icc86tsRTj7BYPSxGYAAAAABEJdnsT7YzIpEAe1azzw9g==',
    'a_ppn': 'RIBE%2FREVENUE%2FREVENUE_FLEXPRICER%2FOUTBOUND',
    '_ga_YZZSK5YYZR': 'GS1.1.1724173070.3.1.1724174981.52.0.0',
    'incap_ses_1047_2313958': 'gDf/ROIG3U7ort5K/bCHDoXSxGYAAAAAjXl49PUH5US4GfS2KLYzXA==',
    'tfpsi': '13a3bb6c-3c3c-4786-aa15-2783ca9447a8',
    'OptanonConsent': 'isGpcEnabled=0&datestamp=Wed+Aug+21+2024+00%3A29%3A44+GMT%2B0700+(Indochina+Time)&version=6.38.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&geolocation=VN%3BSG',
    'utag_main': 'vapi_domain:cathaypacific.com$last_logged_in_customer_id:a34e39a0024618e1cd8dd9cda4cdf1a357163dc9ef54298b2c6e07312fa163fc$dc_visit:7$_sn:1$ses_id:1724174970818%3Bexp-session$_se:4%3Bexp-session$_ss:0%3Bexp-session$_st:1724176783967%3Bexp-session$_pn:4%3Bexp-session$dc_event:4%3Bexp-session$dc_region:us-east-1%3Bexp-session$dcsyncran:1%3Bexp-session$ttd_uuid:9cdebd11-c294-4807-8596-d3be5b52f982%3Bexp-session$cms_1168:1%3Bexp-session',
    'RT': '"z=1&dm=www.cathaypacific.com&si=8b877fc3-eb53-459c-928c-6c631d069d74&ss=m02p9n7t&sl=0&tt=0"',
    'nlbi_2313958_2147483392': 'C84nN2hsb2kShURB1o+NvQAAAAB9HI2XNbYD6hYrgNd99/cF',
    'bm_sv': 'ACA4F58A06A801BCA1F7B7C2C9E4BD80~YAAQhlJNG6Qd/2mRAQAAsDPgcBh8f+0MOMjdimwC9i5i6p+UZPfcPpejBST4JPeA7nJLD4YfPPjBGijr7xR/DxHOsQkjaNQsxigipHmnBvdxD8bz1w+3/KCQQZ8/QDvsok16rp4ATUPfUDKDpa7ltoD4cblg9B1ub4Ge+Zqfx30E+4gh4gc6DCSqwZrHOexnawlKuKvEKmbSFrEkh02FVywdcqI6AxlxljjQfU2E7DPqX5PTYXYOHoL1kq/LBQ30ke6vlc4yIdo=~1',
    'reese84': '3:saARixMTJQIVtowseedWFg==:T6sJysNviOpDBOgycrq9E3eAWyTXJTECgLuS1Dz9iSeD8Eg0vaxCBR4tGJ0ieAX5q5K72D6qNDI2+H6kwdtH2Oxe79sQHjO9hMCiIpCqJDuVwLF7c+0CE1TcnK0t7lG5hZK8tqnebbe3+37I93kzDq9n1RTpOrmoLqSVKjJO46IUkPAbEqRiRu6MFIE43HpwLC1p3tw8Km7bGv/++lKAtsjwuKp1ywizVh+M7fPeCgADd4hTi2YtplZwEtzGVuGoei8zVjJY0KM6+6Hicm/2YuQZpCQ9SCERQH0dp5hb3kVwaSE/5p6EQrJaI0LZnbJY2LU4rqQ/ZKU7092qUIa7P3ToQc+AF7oXQ1SNQCcDLZ7ItAGxhY+PAxX2Gww832ta+ez386mAhxmRfkMkfJh+pYiiD1tmQXrcJjdruKB5ZSBptNus6NHI6uvv9oIOAQCgWEA+oxpjxud97odrqQhoTY+9IfuDACT9BS5KZJSd6PvgKFCFsKF4No0ShIJCJpbRH+jxMqWz5gziqTzbTsdUhdB0IXyhqpQQI3xNcAcMZDRJdwd+IoXIol1HZVf2MJ+v3vfkFwD9bQ5k3BLvkJe4VhWOJ0YpUzdTJ4XlSnhDY9V37DH6yjaz0l/EyrA5ltTdoBs4o3iP50mBoIURNa3xX/zwASTz+rmJPA8GNY9SLqDo6OZJ5D3ceqf+VDUMPV1/CFA/m7LO6eJ4lXwrqRgY1dVSF5cO3yvT3o2kRFqGyo741uCvD8ayXsEzC0PP0HO3:fLB6HnpC5b4MLRrI7jh4NwBTIK2xB/0oFGdCokp4d0k=',
    's_sq': 'asiaml-cx-globalmaster-prd%3D%2526c.%2526a.%2526activitymap.%2526page%253DRIBE%25252FREVENUE%25252FREVENUE_FLEXPRICER%25252FOUTBOUND%2526link%253DContinue%2526region%253Dribe-overlay-black%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DRIBE%25252FREVENUE%25252FREVENUE_FLEXPRICER%25252FOUTBOUND%2526pidt%253D1%2526oid%253DContinue%2526oidt%253D3%2526ot%253DSUBMIT',
}

headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
    # 'cookie': '_hjSessionUser_358709=eyJpZCI6ImZiODU1MTZiLWUzYjUtNTQ2Ny04ZTcwLTQ2YWMyNGRiODQ5NiIsImNyZWF0ZWQiOjE3MTg5MDY3OTAwMzMsImV4aXN0aW5nIjp0cnVlfQ==; visid_incap_2313958=yy9WrmdnTX+AsOUIOYCmcRNwdGYAAAAAQUIPAAAAAADNGA8g5jGxlkEZKseRp0IS; f83b3ad950411e3414e1276ee43ce204=754f48f9244e978570add1e2c08118a1; optimizelyEndUserId=oeu1718906788977r0.8890886921400423; AMCVS_21683A5857FCAE5A0A495DC5%40AdobeOrg=1; s_ecid=MCMID%7C22117646739942201930851154590627858086; s_cc=true; _fbp=fb.1.1724087717939.185826328575060335; lastLoginType=1; LoginCookie=0.7375161666185728; _gcl_au=1.1.1332212776.1724087761; _ga=GA1.1.807630469.1724087761; _yjsu_yjad=1724087761.b4348c1a-9b9f-4308-aaf9-d3dcca1ad97d; __tmbid=sg-1718906790-ea10012ba2424e20aacc1a705f6ced7d; isLoggedIn=true; polling_request=0; flights/_campaignpopup_display=false; OptanonAlertBoxClosed=2024-08-19T17:29:54.263Z; 056c1fd49d864b61a16255cdb7a82105=75b8820dadbfe67faf6939321d59b10b; dc85ac4f0435a31e4b9fb8eca9f182e7=001df81b62af7751af65c05c6690bfab; OPTOUTMULTI=0:0%7Cc1:0; nlbi_2313958=GjoIN/DT4S88MjEW1o+NvQAAAABB60WwhsZTWl7a/6yIJzAR; 56ca038ea46ddc63e5a9c230844ee843=8b01d9b17c7553d079fdb0ff64eee09d; incap_ses_573_2313958=LbhaclnvIiv7p1ODibTzBx+Bw2YAAAAAiW8mnWmbED+eOCE3OQDYVA==; __clickidc=172408860913986467; _cls_v=25a71a5c-02d6-448a-9592-b58afb746258; _cls_s=797df4c7-9b40-453c-a523-6d5fa85d3d01:0; cbfw.sid=s%3ASHhYM8SspJjOBpvodEz-j6iHiMBMwQyR.hfCg%2BCLL8m647CWu1vha%2Fed33PBUzMo7n0RqsYq63V8; pxcts=b1b91a0a-5e50-11ef-966e-3ebd44f7b340; _pxvid=b1b90a2b-5e50-11ef-966b-3a4f0fa21351; __pxvid=b1f56262-5e50-11ef-bdcd-0242ac120003; incap_ses_428_2313958=2sLybK9bYE3j/QAqx4/wBf6Gw2YAAAAACcciuG1+57V4FE6Rx6wOUg==; incap_ses_165_2313958=aAoKHzJ9+2SDUQPmxzJKAoqNw2YAAAAAkzZhqluUBOVVINeJ2WQBzg==; incap_ses_1562_2313958=D0CfQ127fj84V6jC11atFQePw2YAAAAAxdt3JLz3osBQ7W4fj7J7YA==; ak_bmsc=D5C6CF29865808556A84CFA4922F263D~000000000000000000000000000000~YAAQjlJNG66fvV+RAQAABK+TcBgsQOAF46JxHVjwPXUfSLWh+Y22nDNinFu+aYvv+iJm7B/5bDq0c+8+UiTMtMlbItY9JYWaRJRADPHSOccWolSPUeAn2JY8PdXGm6tP7B7cyi6Hip/xWxBkgQn9pBOaJSex9WChyVTm53/TpecXRpV/h9dMq0cNAiIVYfeJPG6jOhGBd7+4AKN5hGzbImKafcQVZNsk6AlkHIidLcn1OMZsuW2rMUxXAdDLe1t6EVGuOpPLAEND8YPkPA45nQVmhBYPxagRWpKJ6slE9+H7MHjxFwyvcKpWmTUu5/uHASom6vlosLUvzvQen1tPtK3mcrYM8dTAlU5+wo9B1fO//Cr+TG7UvWnHJVpkvjatvYwcVr4XxozXYWt1PMuDZBBqfODw1VYdoV6ctmrJXjIoKcfyxZEq0Bl1ZpE8xxWwTRzACwthOYJF6j0U/526PsjDBns=; mlc_prelogin=1; CXMPO_JSESSIONID=01549657-2aeb-4f9f-9189-030ce40eddd4; _hjSession_358709=eyJpZCI6IjE0NzljMjJmLWFmZTYtNGI3ZS04YzU2LWI5OGUxZDViZDg1MiIsImMiOjE3MjQxNzMwNzA1NTAsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; QueueITAccepted-SDFrts345E-V3_milesflight=EventId%3Dmilesflight%26QueueId%3Dddff8332-2a15-45eb-9dd9-9c0b0a0a2cf7%26RedirectType%3Dsafetynet%26IssueTime%3D1724173078%26Hash%3D08cc74b7836304136761933a78442ffa400457c05a7a83d49549b0b299d63e5f; RT="z=1&dm=cathaypacific.com&si=8b877fc3-eb53-459c-928c-6c631d069d74&ss=m02o4wr9&sl=0&tt=0"; ADRUM=s=1724174845944&r=https%3A%2F%2Fwww.cathaypacific.com%2Fverachatbot%2F%3F-1475824490; incap_ses_1206_2313958=cE7lcTnSiW5UmOmppZK8EP3RxGYAAAAAjycwiyE845KT4cPFDUN7KA==; XSRF-TOKEN=0907731a-fbf1-4639-afb5-78e250ec3f08; AKA_A2=A; QueueITAccepted-SDFrts345E-V3_helloibefcfscom=EventId%3Dhelloibefcfscom%26QueueId%3Dd8ce7db1-a4b7-42df-b35b-1b4faf2df50a%26RedirectType%3Dsafetynet%26IssueTime%3D1724174972%26Hash%3Df019fdb1dd8b95c3e1c5a8d32273d88173cb6beaf963de3884fc59526c6ffbb4; IBE_JSESSIONID=OTM1YzA4MDMtNmFjMi00NDU3LTgwMDMtZGJiMjY2ODRlMDQ2; _abck=3C8511AF26714CB396821042763FAC5F~0~YAAQhlJNG5a5/mmRAQAAYkzWcAzDQmy3ppRHFpq4mAbHlxw4hDfGHo6PnrwMeNfzUY18fQYmJqQNRj+vQ/8Z8n7Uxx5r0OMMx5TLOYWNeN1UKC7vPFC2c6M3xsMtkg0kJDZo7aCoeHTdHut/pTkRWDQz6uOzWuQJqya+bJdVWUB9oQ/gs/zd+3/RT31UApLUUe89SULmvBasbSZiUw8yw0Hs15HgOB6Lqhv1Zx1hbZ27aij2Yp8jBB6d4pmQtLNp/ui1XXwoinkYXGh8R6URgphu2YM96XIgCqe4CSVhNsgBjN7q9mTew7qWDwq/nS7Qmqb9H+aykFcBTyacexKU7QTFSh48b5yEdS4YwQxxR3LFr3VlnslF07IObuRMC4pwKJ948lCsLL5ALOsVT7fHgmwl11PVAzo3DPXtW+knjIZitokS7pE1ZJu809XttuiWgpLNtxxvqXPoL13kq40QUSNivFNEL7CEBPk=~-1~-1~-1; bm_sz=A706DB96677E567AB81B886E0307618E~YAAQhlJNG5i5/mmRAQAAYkzWcBgfh8mmIUIHdJ9b42Sf3tf8LAROn2a85yd/RlYWdGEoPairDFaIZ3qOUsfgokjKy4BA+RVGRp1wWDNTb/PH2b+cLyS2DFYHUkn55CFJB0tiH+UNnEHjOfnj+/XrS0uEGdmMADUaW7kSyGwyeE9f9phh5bwAIVgoAmeCLfOatomObjFCN9WtA61CH7w1YkDr2W+Zg27VO0JB/30MpZSpyk72jEkDQ+Jo3wxStx1kVsNuKYEI4+PVUTQB2A9lkdDVM/CHvFv1/dOIjhyVGQdSZR5xGzziLX93ErYOwta1/oCcg60Qzvc/gMuEe2mA6RDebjbpGPzZQ6qu8lvobJvcx2fGq648tLI3fQIh8QYGRzJo28olRZge9OvWFc5rI0iAa5KGl1f/lRWS01TZ+bPGU4BQ8rHWNn+DFZF1+8zrN0Lfd6zrjXZsZdEJaxNHzLwg36Kt7LpxrtXAhpqP9BGMurSYSqwTw/9JSv1jNCK+12ADauHuSGZ6AUETh30DyF75c8KT6vlt0w4=~4601923~3553593; AMCV_21683A5857FCAE5A0A495DC5%40AdobeOrg=1176715910%7CMCIDTS%7C19955%7CMCMID%7C22117646739942201930851154590627858086%7CMCAAMLH-1724779780%7C3%7CMCAAMB-1724779780%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1724182180s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-19962%7CvVersion%7C5.4.0; incap_ses_431_2313958=/3JBMioC0icc86tsRTj7BYPSxGYAAAAABEJdnsT7YzIpEAe1azzw9g==; a_ppn=RIBE%2FREVENUE%2FREVENUE_FLEXPRICER%2FOUTBOUND; _ga_YZZSK5YYZR=GS1.1.1724173070.3.1.1724174981.52.0.0; incap_ses_1047_2313958=gDf/ROIG3U7ort5K/bCHDoXSxGYAAAAAjXl49PUH5US4GfS2KLYzXA==; tfpsi=13a3bb6c-3c3c-4786-aa15-2783ca9447a8; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Aug+21+2024+00%3A29%3A44+GMT%2B0700+(Indochina+Time)&version=6.38.0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&geolocation=VN%3BSG; utag_main=vapi_domain:cathaypacific.com$last_logged_in_customer_id:a34e39a0024618e1cd8dd9cda4cdf1a357163dc9ef54298b2c6e07312fa163fc$dc_visit:7$_sn:1$ses_id:1724174970818%3Bexp-session$_se:4%3Bexp-session$_ss:0%3Bexp-session$_st:1724176783967%3Bexp-session$_pn:4%3Bexp-session$dc_event:4%3Bexp-session$dc_region:us-east-1%3Bexp-session$dcsyncran:1%3Bexp-session$ttd_uuid:9cdebd11-c294-4807-8596-d3be5b52f982%3Bexp-session$cms_1168:1%3Bexp-session; RT="z=1&dm=www.cathaypacific.com&si=8b877fc3-eb53-459c-928c-6c631d069d74&ss=m02p9n7t&sl=0&tt=0"; nlbi_2313958_2147483392=C84nN2hsb2kShURB1o+NvQAAAAB9HI2XNbYD6hYrgNd99/cF; bm_sv=ACA4F58A06A801BCA1F7B7C2C9E4BD80~YAAQhlJNG6Qd/2mRAQAAsDPgcBh8f+0MOMjdimwC9i5i6p+UZPfcPpejBST4JPeA7nJLD4YfPPjBGijr7xR/DxHOsQkjaNQsxigipHmnBvdxD8bz1w+3/KCQQZ8/QDvsok16rp4ATUPfUDKDpa7ltoD4cblg9B1ub4Ge+Zqfx30E+4gh4gc6DCSqwZrHOexnawlKuKvEKmbSFrEkh02FVywdcqI6AxlxljjQfU2E7DPqX5PTYXYOHoL1kq/LBQ30ke6vlc4yIdo=~1; reese84=3:saARixMTJQIVtowseedWFg==:T6sJysNviOpDBOgycrq9E3eAWyTXJTECgLuS1Dz9iSeD8Eg0vaxCBR4tGJ0ieAX5q5K72D6qNDI2+H6kwdtH2Oxe79sQHjO9hMCiIpCqJDuVwLF7c+0CE1TcnK0t7lG5hZK8tqnebbe3+37I93kzDq9n1RTpOrmoLqSVKjJO46IUkPAbEqRiRu6MFIE43HpwLC1p3tw8Km7bGv/++lKAtsjwuKp1ywizVh+M7fPeCgADd4hTi2YtplZwEtzGVuGoei8zVjJY0KM6+6Hicm/2YuQZpCQ9SCERQH0dp5hb3kVwaSE/5p6EQrJaI0LZnbJY2LU4rqQ/ZKU7092qUIa7P3ToQc+AF7oXQ1SNQCcDLZ7ItAGxhY+PAxX2Gww832ta+ez386mAhxmRfkMkfJh+pYiiD1tmQXrcJjdruKB5ZSBptNus6NHI6uvv9oIOAQCgWEA+oxpjxud97odrqQhoTY+9IfuDACT9BS5KZJSd6PvgKFCFsKF4No0ShIJCJpbRH+jxMqWz5gziqTzbTsdUhdB0IXyhqpQQI3xNcAcMZDRJdwd+IoXIol1HZVf2MJ+v3vfkFwD9bQ5k3BLvkJe4VhWOJ0YpUzdTJ4XlSnhDY9V37DH6yjaz0l/EyrA5ltTdoBs4o3iP50mBoIURNa3xX/zwASTz+rmJPA8GNY9SLqDo6OZJ5D3ceqf+VDUMPV1/CFA/m7LO6eJ4lXwrqRgY1dVSF5cO3yvT3o2kRFqGyo741uCvD8ayXsEzC0PP0HO3:fLB6HnpC5b4MLRrI7jh4NwBTIK2xB/0oFGdCokp4d0k=; s_sq=asiaml-cx-globalmaster-prd%3D%2526c.%2526a.%2526activitymap.%2526page%253DRIBE%25252FREVENUE%25252FREVENUE_FLEXPRICER%25252FOUTBOUND%2526link%253DContinue%2526region%253Dribe-overlay-black%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DRIBE%25252FREVENUE%25252FREVENUE_FLEXPRICER%25252FOUTBOUND%2526pidt%253D1%2526oid%253DContinue%2526oidt%253D3%2526ot%253DSUBMIT',
    'origin': 'https://book.cathaypacific.com',
    'priority': 'u=1, i',
    'referer': 'https://book.cathaypacific.com/',
    'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
}

params = {
    'ACTION': 'KEEP_ALIVE',
    'LANGUAGE': 'GB',
    'SITE': 'CXRECXRE',
    'BOOKING_FLOW': 'REVENUE',
    'SKIN': 'CX',
    'EXTERNAL_ID': '935c0803-6ac2-4457-8003-dbb26684e046',
    'FROM_SITE': 'CX',
    'COUNTRY': 'VN',
    'CC_CHECK': 'N',
}

response = request.get('https://www.cathaypacific.com/wdsibe/IBEFacade', params=params, cookies=cookies, headers=headers)
print(f">>>>>>>>>{response.status_code} - {response.json()}")