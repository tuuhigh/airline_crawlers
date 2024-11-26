import requests
from curl_cffi import requests as crequests

cookies = {
    'VAA_ENSIGHTEN_PRIVACY_BANNER_LOADED': '1',
    'VAA_ENSIGHTEN_PRIVACY_Functional': '1',
    'VAA_ENSIGHTEN_PRIVACY_Analytics': '1',
    'VAA_ENSIGHTEN_PRIVACY_Marketing': '1',
    'VAA_ENSIGHTEN_PRIVACY_BANNER_VIEWED': '1',
    'mdLogger': 'false',
    'kampyle_userid': '1386-90cf-78e6-b29b-9823-3977-22ad-8ec2',
    'uuid': 'cfa7e65f-f0c0-418d-9e38-a5cdfadd016c',
    'QuantumMetricUserID': '75dba26c79119e14a578613f44b1c757',
    'kampylePageLoadedTimestamp': '1716486209810',
    'TLTUID': '3CC5C59E6C82106CD3C2D590A74F4993',
    's_ecid': 'MCMID%7C21671391093743674450823337801396417234',
    'cjevent': '',
    'prefConf': 'N',
    'DL_PER': 'true',
    'AAMC_virginatlantic_0': 'REGION%7C3',
    'fltk': 'segID%3D5617196%2CsegID%3D8008213',
    'aam_uuid': '21698014878257832910820361166915612156',
    'mobile': 'N',
    'hpr_user': 'y',
    'prefUI': 'en-ca',
    'TLTSID': '139C45787EF0107E6C6291A95EA3AF66',
    'home_page': 'rhp',
    'xssid': '94c51017-e9bd-4a0a-b9e9-a4b6fac5e015',
    'JSESSIONID': '0000W7AWXLWF1RlnCfrB1RVNTus:-1',
    'akaalb_alb_www_virginatlantic_com': '~op=www_virginatlantic_com_dc:www_virginatlantic_com_DC|~rv=64~m=www_virginatlantic_com_DC:0|~os=71e6a92f9cb2d64c9c61538232f5fe10~id=7a743ad9b3977bfc82af2b4a7eec8ff5',
    'ak_bmsc': '58AF56DB4E5BA41D6C6951CC2F847C8D~000000000000000000000000000000~YAAQSp42F8KKRiuSAQAAPx18QRmsU/GoLYxTzVS5xEM7lNgBtgrmNpBDz6sYv9w1d9XE8sI4pANmgBJ6rU5gqPkxXoKPI1bH29SA63Rvle1PlJrAIP3cvw8TCkLeJ9aY/Oi1Vr2FnnBhebjUyWpWVMiXU4mGz/aG3MhlHLbU16ycZwGbqCEGyQs+JWIhmDMiu20YpmfZSRJ9QSw85IomRGg5XlpJMO1UDRMPD8ghv97GmSC/DGPao1Qj3BEGizb1f6CLIIAoJHkwtVjuF8xm7Fv4gS/9FIZ7RYPgsQNrfxAGAd/qEtVw2IkCO+wIuETtUOW6hNjLq0T+jzb/6torNBS4iCrPDbK2jqg7GGX3vJbC84viFeduBCLaAgcmUzR6qE3aGNFgA4K68sCb40tfulZb',
    'rxVisitor': '17276755064060QC5ECHDPS8L821O239N2BDGK09G6ORV',
    'ens_flightNumberDeparture': '',
    'ens_flightNumberReturn': '',
    'at_check': 'true',
    'ens_linkNameClicked': '',
    'AMCVS_30516EBF55FC098E7F000101%40AdobeOrg': '1',
    'ens_referrer': '',
    'mboxEdgeCluster': '38',
    'AMCV_30516EBF55FC098E7F000101%40AdobeOrg': '690614123%7CMCIDTS%7C19997%7CMCMID%7C21671391093743674450823337801396417234%7CMCAAMLH-1728280306%7C3%7CMCAAMB-1728280306%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1727682706s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-20004%7CvVersion%7C3.1.0',
    'seenRecently': '1',
    'ENS_AES': '%7B%22lclt%22%3A1727675507848%2C%22lcot%22%3Anull%7D',
    'IBMID': 'W7AWXLWF1RlnCfrB1RVNTus:1',
    'ens_loggedIn': '0',
    'ens_loginMethod': '',
    '_cs_mk': '0.3531537471195625_1727675510644',
    's_cc': 'true',
    'kampyleUserSession': '1727675511532',
    'kampyleUserSessionsCount': '48',
    'kampyleUserPercentile': '18.1667122002666',
    'QuantumMetricSessionID': '8fb4defb42a3b23121cfa80e3bebef46',
    'hideSignUpTooltip': 'true',
    'dtCookie': 'v_4_srv_5_sn_F310A5868CDE7A14C750F03D045AD475_app-3Add20c31d92c971bd_1_ol_0_perc_100000_mul_1',
    'trip_type': '',
    'AKA_A2': 'A',
    '_uetsid': '156d06407ef011efa05a358dbe1fdfde',
    '_uetvid': '2d23fde003f211ef8714cf0b2ec9bb1c|de6hph|1721143806870|2|1|bat.bing.com/p/insights/c/z',
    'kampyleSessionPageCounter': '2',
    's_sq': 'virginatlanticair4prod%3D%2526c.%2526a.%2526activitymap.%2526page%253DRevenue%252520Booking%252520Full%252520Search%2526link%253DSUBMIT%2526region%253Dbooking%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DRevenue%252520Booking%252520Full%252520Search%2526pidt%253D1%2526oid%253DSUBMIT%2526oidt%253D3%2526ot%253DSUBMIT',
    'bm_sv': '2CA0AD2B406F5AAED8A9F46DF0D782E5~YAAQSp42F+OfRiuSAQAAZpp9QRloxqwKNTM4ABowOf/LnL73SJZ9NcQ3pTDjjV+AWh07MfRGGkHVXxYEPsn/AUdoY5U0UEl9b2uFS3cViaaOAUJGlChKBuPXU/cIfOXnaRRmwg4ylSdWwMxO4I0dQRDsXwv3rXVp3dXa80KNjKsKN+qp2wrpQlSqGm+RbYnPYGUs14uG1Ahv+bMXJPP5+vex+87mxWAlQFqrg60NUcvgjL+jSvJ9Gtpwxoma5/iCppGg8RIemNm+~1',
    'bm_sz': '36E6280728B3F450C991C2C0C3DCC102~YAAQSp42F+SfRiuSAQAAZpp9QRkT3R4kJ28g2rtioeKxKWLT//+FHAUSTH7b86Op1Lu03eEq/OLvBK0PAMXB2fJRW+DNfsw6X9H/blBcVD8v7gHrWJ+O4OHfLaC10X1J0VY3AAOfzsjsOTD+Zw4jfHH5pgYqXaFKNaeil/6j72FmSoKdAzcKakOFq/fyM1u2KRliWSm5GuPE+cMbQ3RJYtp8A4jnhha+lJs1Q4MBpYASKemVhfcgl4c+QHTTjYYo3K/7rWXl1EdlgmMTqUZvuF6U2H6ZS0OuHoMdXaFshPkc8SNkiBNOcEUuIl/7ajCxiAEhfkyCuj22BIs+nRzbz2u1YdVFwRldyUyCeUEb8BkEjiQgHgp3VDuSMMnAdTVM3gElvog/WZdrq6V7qSdmrhRzJrVTR2VPYu/6+6LU4LRK+9b0LgLoQj8gVEmGx9c+/+iP7s8B9A==~3163440~4339782',
    'dtLatC': '4',
    'dtSa': '-',
    'ens_origReferrer': 'https%3A%2F%2Fwww.virginatlantic.com%2Fflight-search%2Fbook-a-flight%3FcacheKeySuffix%3D98f8edd4-bad8-4d50-90e2-918a3cf0bde1',
    'RT': '"z=1&dm=virginatlantic.com&si=a4688094-1544-4795-8ee2-85bf94cbd3df&ss=m1oldzm4&sl=2&tt=8m3&bcn=%2F%2F684d0d41.akstat.io%2F&rl=1"',
    'mbox': 'PC#aeb9ec9f3e614ae4a863c6f3af34b0b9.38_0#1790920405|session#ce6d2423322f41138bc0550decaf37cc#1727677465',
    '_abck': 'E6F416B2EE57EB9C366480C8B6403100~-1~YAAQSp42Fz2gRiuSAQAAT599QQyAPWe00liyC+LSJFuj7SDWJMbMoq1l9nDt9Acn3lbrwdQf5nfBxKKVaXdLUULV50K5R3UoK4jl5lYPK0FPBxPw71uUx3WqlUZYGfxsMIo5Rv7gUTEsMo2NQh3XkUKTmnTq2MRoITfFEETic9QI/D9bTxla7i4AhgSQtG22cBacnyqMEHWsPm2IQkOCttUjt9md1zjf3IwBVT8dnhxuop78Wo4Lgdhv/WmW1c2RMbZp1xIng/WUT5+PBoi3wAojcKiDZPuH7LC2hgu/VuTAUz7V4Y7Uyz6cl4pdaMBLlwzKKybu0fv/zD6iqSK9GGLHNXHNsBtRHbJwmoJ7PzWNleLhD2HN+lxAlU/C72nAKfRCC3jaHT0fXvy0rZ2lIcEz9tup1chxArK2rDHT9BRVFY9vmcZkxkknhC/60MXsWVa1X/FF82jDuC9uqrk2/ITffiFuHVPD5RMVazSmtvVuyJRCCoLWatC7eLF2W9gM+kXVp0Epdur71jQtkFuy/x05tTZgDtEDbALx3Eo4tdZt3roNvZBGcDeErkywFiwRMSSGqFnWo+nc2awAhK0LA+I6BsshYjjDTLERIH0xoY8LN5/uMRXPPJPCKPXWJQjBsNTo8UmkKf6FF8lwBKrDywP4YM1yOI1R8NnY/yhiNAz7LwbNASvHHUjZGPtRqJm0Dht2mX/fIUfOmdP/nexlMoyKgbV3PJPNP8SeOEtbwmwncQKknJhEAz42S64bnbBbZiUap5E6Cq4m0EoCO3REr0TOCs6MHKq7d4935Q8b3ozhjODL8x7ZqDDZ3pCYB2JTHvOWRf3E1rkNfcyp0Ehk+foPlyfb~-1~||0||~1727679109',
    'rxvt': '1727677405036|1727675506408',
    'dtPC': '5$275603889_920h13vPPVRFCONCAMRFATJDCPFOPOTHINAUGNI-0e0',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
    'cachekey': '98f8edd4-bad8-4d50-90e2-918a3cf0bde1',
    'content-type': 'application/json; charset=UTF-8',
    # 'cookie': 'VAA_ENSIGHTEN_PRIVACY_BANNER_LOADED=1; VAA_ENSIGHTEN_PRIVACY_Functional=1; VAA_ENSIGHTEN_PRIVACY_Analytics=1; VAA_ENSIGHTEN_PRIVACY_Marketing=1; VAA_ENSIGHTEN_PRIVACY_BANNER_VIEWED=1; mdLogger=false; kampyle_userid=1386-90cf-78e6-b29b-9823-3977-22ad-8ec2; uuid=cfa7e65f-f0c0-418d-9e38-a5cdfadd016c; QuantumMetricUserID=75dba26c79119e14a578613f44b1c757; kampylePageLoadedTimestamp=1716486209810; TLTUID=3CC5C59E6C82106CD3C2D590A74F4993; s_ecid=MCMID%7C21671391093743674450823337801396417234; cjevent=; prefConf=N; DL_PER=true; AAMC_virginatlantic_0=REGION%7C3; fltk=segID%3D5617196%2CsegID%3D8008213; aam_uuid=21698014878257832910820361166915612156; mobile=N; hpr_user=y; prefUI=en-ca; TLTSID=139C45787EF0107E6C6291A95EA3AF66; home_page=rhp; xssid=94c51017-e9bd-4a0a-b9e9-a4b6fac5e015; JSESSIONID=0000W7AWXLWF1RlnCfrB1RVNTus:-1; akaalb_alb_www_virginatlantic_com=~op=www_virginatlantic_com_dc:www_virginatlantic_com_DC|~rv=64~m=www_virginatlantic_com_DC:0|~os=71e6a92f9cb2d64c9c61538232f5fe10~id=7a743ad9b3977bfc82af2b4a7eec8ff5; ak_bmsc=58AF56DB4E5BA41D6C6951CC2F847C8D~000000000000000000000000000000~YAAQSp42F8KKRiuSAQAAPx18QRmsU/GoLYxTzVS5xEM7lNgBtgrmNpBDz6sYv9w1d9XE8sI4pANmgBJ6rU5gqPkxXoKPI1bH29SA63Rvle1PlJrAIP3cvw8TCkLeJ9aY/Oi1Vr2FnnBhebjUyWpWVMiXU4mGz/aG3MhlHLbU16ycZwGbqCEGyQs+JWIhmDMiu20YpmfZSRJ9QSw85IomRGg5XlpJMO1UDRMPD8ghv97GmSC/DGPao1Qj3BEGizb1f6CLIIAoJHkwtVjuF8xm7Fv4gS/9FIZ7RYPgsQNrfxAGAd/qEtVw2IkCO+wIuETtUOW6hNjLq0T+jzb/6torNBS4iCrPDbK2jqg7GGX3vJbC84viFeduBCLaAgcmUzR6qE3aGNFgA4K68sCb40tfulZb; rxVisitor=17276755064060QC5ECHDPS8L821O239N2BDGK09G6ORV; ens_flightNumberDeparture=; ens_flightNumberReturn=; at_check=true; ens_linkNameClicked=; AMCVS_30516EBF55FC098E7F000101%40AdobeOrg=1; ens_referrer=; mboxEdgeCluster=38; AMCV_30516EBF55FC098E7F000101%40AdobeOrg=690614123%7CMCIDTS%7C19997%7CMCMID%7C21671391093743674450823337801396417234%7CMCAAMLH-1728280306%7C3%7CMCAAMB-1728280306%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1727682706s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-20004%7CvVersion%7C3.1.0; seenRecently=1; ENS_AES=%7B%22lclt%22%3A1727675507848%2C%22lcot%22%3Anull%7D; IBMID=W7AWXLWF1RlnCfrB1RVNTus:1; ens_loggedIn=0; ens_loginMethod=; _cs_mk=0.3531537471195625_1727675510644; s_cc=true; kampyleUserSession=1727675511532; kampyleUserSessionsCount=48; kampyleUserPercentile=18.1667122002666; QuantumMetricSessionID=8fb4defb42a3b23121cfa80e3bebef46; hideSignUpTooltip=true; dtCookie=v_4_srv_5_sn_F310A5868CDE7A14C750F03D045AD475_app-3Add20c31d92c971bd_1_ol_0_perc_100000_mul_1; trip_type=; AKA_A2=A; _uetsid=156d06407ef011efa05a358dbe1fdfde; _uetvid=2d23fde003f211ef8714cf0b2ec9bb1c|de6hph|1721143806870|2|1|bat.bing.com/p/insights/c/z; kampyleSessionPageCounter=2; s_sq=virginatlanticair4prod%3D%2526c.%2526a.%2526activitymap.%2526page%253DRevenue%252520Booking%252520Full%252520Search%2526link%253DSUBMIT%2526region%253Dbooking%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DRevenue%252520Booking%252520Full%252520Search%2526pidt%253D1%2526oid%253DSUBMIT%2526oidt%253D3%2526ot%253DSUBMIT; bm_sv=2CA0AD2B406F5AAED8A9F46DF0D782E5~YAAQSp42F+OfRiuSAQAAZpp9QRloxqwKNTM4ABowOf/LnL73SJZ9NcQ3pTDjjV+AWh07MfRGGkHVXxYEPsn/AUdoY5U0UEl9b2uFS3cViaaOAUJGlChKBuPXU/cIfOXnaRRmwg4ylSdWwMxO4I0dQRDsXwv3rXVp3dXa80KNjKsKN+qp2wrpQlSqGm+RbYnPYGUs14uG1Ahv+bMXJPP5+vex+87mxWAlQFqrg60NUcvgjL+jSvJ9Gtpwxoma5/iCppGg8RIemNm+~1; bm_sz=36E6280728B3F450C991C2C0C3DCC102~YAAQSp42F+SfRiuSAQAAZpp9QRkT3R4kJ28g2rtioeKxKWLT//+FHAUSTH7b86Op1Lu03eEq/OLvBK0PAMXB2fJRW+DNfsw6X9H/blBcVD8v7gHrWJ+O4OHfLaC10X1J0VY3AAOfzsjsOTD+Zw4jfHH5pgYqXaFKNaeil/6j72FmSoKdAzcKakOFq/fyM1u2KRliWSm5GuPE+cMbQ3RJYtp8A4jnhha+lJs1Q4MBpYASKemVhfcgl4c+QHTTjYYo3K/7rWXl1EdlgmMTqUZvuF6U2H6ZS0OuHoMdXaFshPkc8SNkiBNOcEUuIl/7ajCxiAEhfkyCuj22BIs+nRzbz2u1YdVFwRldyUyCeUEb8BkEjiQgHgp3VDuSMMnAdTVM3gElvog/WZdrq6V7qSdmrhRzJrVTR2VPYu/6+6LU4LRK+9b0LgLoQj8gVEmGx9c+/+iP7s8B9A==~3163440~4339782; dtLatC=4; dtSa=-; ens_origReferrer=https%3A%2F%2Fwww.virginatlantic.com%2Fflight-search%2Fbook-a-flight%3FcacheKeySuffix%3D98f8edd4-bad8-4d50-90e2-918a3cf0bde1; RT="z=1&dm=virginatlantic.com&si=a4688094-1544-4795-8ee2-85bf94cbd3df&ss=m1oldzm4&sl=2&tt=8m3&bcn=%2F%2F684d0d41.akstat.io%2F&rl=1"; mbox=PC#aeb9ec9f3e614ae4a863c6f3af34b0b9.38_0#1790920405|session#ce6d2423322f41138bc0550decaf37cc#1727677465; _abck=E6F416B2EE57EB9C366480C8B6403100~-1~YAAQSp42Fz2gRiuSAQAAT599QQyAPWe00liyC+LSJFuj7SDWJMbMoq1l9nDt9Acn3lbrwdQf5nfBxKKVaXdLUULV50K5R3UoK4jl5lYPK0FPBxPw71uUx3WqlUZYGfxsMIo5Rv7gUTEsMo2NQh3XkUKTmnTq2MRoITfFEETic9QI/D9bTxla7i4AhgSQtG22cBacnyqMEHWsPm2IQkOCttUjt9md1zjf3IwBVT8dnhxuop78Wo4Lgdhv/WmW1c2RMbZp1xIng/WUT5+PBoi3wAojcKiDZPuH7LC2hgu/VuTAUz7V4Y7Uyz6cl4pdaMBLlwzKKybu0fv/zD6iqSK9GGLHNXHNsBtRHbJwmoJ7PzWNleLhD2HN+lxAlU/C72nAKfRCC3jaHT0fXvy0rZ2lIcEz9tup1chxArK2rDHT9BRVFY9vmcZkxkknhC/60MXsWVa1X/FF82jDuC9uqrk2/ITffiFuHVPD5RMVazSmtvVuyJRCCoLWatC7eLF2W9gM+kXVp0Epdur71jQtkFuy/x05tTZgDtEDbALx3Eo4tdZt3roNvZBGcDeErkywFiwRMSSGqFnWo+nc2awAhK0LA+I6BsshYjjDTLERIH0xoY8LN5/uMRXPPJPCKPXWJQjBsNTo8UmkKf6FF8lwBKrDywP4YM1yOI1R8NnY/yhiNAz7LwbNASvHHUjZGPtRqJm0Dht2mX/fIUfOmdP/nexlMoyKgbV3PJPNP8SeOEtbwmwncQKknJhEAz42S64bnbBbZiUap5E6Cq4m0EoCO3REr0TOCs6MHKq7d4935Q8b3ozhjODL8x7ZqDDZ3pCYB2JTHvOWRf3E1rkNfcyp0Ehk+foPlyfb~-1~||0||~1727679109; rxvt=1727677405036|1727675506408; dtPC=5$275603889_920h13vPPVRFCONCAMRFATJDCPFOPOTHINAUGNI-0e0',
    'origin': 'https://www.virginatlantic.com',
    'priority': 'u=1, i',
    'referer': 'https://www.virginatlantic.com/flight-search/search-results?cacheKeySuffix=98f8edd4-bad8-4d50-90e2-918a3cf0bde1',
    'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'x-app-channel': 'sl-sho',
    'x-app-refresh': '',
    'x-app-route': 'SL-RSB',
}

json_data = {
    'isEdocApplied': False,
    'tripType': 'ONE_WAY',
    'shopType': 'MONEY',
    'priceType': 'Revenue',
    'nonstopFlightsOnly': 'false',
    'bookingPostVerify': 'RTR_YES',
    'bundled': 'off',
    'segments': [
        {
            'origin': 'JFK',
            'destination': 'LHR',
            'originCountryCode': 'US',
            'destinationCountryCode': 'GB',
            'departureDate': '2024-10-31',
            'connectionAirportCode': None,
        },
    ],
    'destinationAirportRadius': {
        'measure': 100,
        'unit': 'MI',
    },
    'originAirportRadius': {
        'measure': 100,
        'unit': 'MI',
    },
    'flexAirport': False,
    'flexDate': False,
    'flexDaysWeeks': '',
    'passengers': [
        {
            'count': 1,
            'type': 'ADT',
        },
    ],
    'meetingEventCode': '',
    'bestFare': 'VSLT',
    'searchByCabin': True,
    'cabinFareClass': None,
    'refundableFlightsOnly': False,
    'deltaOnlySearch': 'false',
    'initialSearchBy': {
        'fareFamily': 'VSLT',
        'cabinFareClass': None,
        'meetingEventCode': '',
        'refundable': False,
        'flexAirport': False,
        'flexDate': False,
        'flexDaysWeeks': '',
        'deepLinkVendorId': None,
    },
    'searchType': 'search',
    'searchByFareClass': None,
    'pageName': 'FLIGHT_SEARCH',
    'requestPageNum': '1',
    'action': 'findFlights',
    'actionType': '',
    'priceSchedule': 'REVENUE',
    'schedulePrice': 'price',
    'shopWithMiles': '',
    'awardTravel': 'false',
    'datesFlexible': False,
    'flexCalendar': False,
    'upgradeRequest': False,
    'is_Flex_Search': True,
    'filter': None,
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
    'https://www.virginatlantic.com/shop/ow/search',
    impersonate="chrome124",
    proxies=proxy_attr, 
    cookies=cookies, headers=headers, json=json_data)

print(f">>>>>>>>>>>>>>>..{response.status_code}")
print(f">>>>>>>>>>>>>>>..{response.text}")
# Note: json_data will not be serialized by requests
# exactly as it was in the original request.
#data = '{"isEdocApplied":false,"tripType":"ONE_WAY","shopType":"MONEY","priceType":"Revenue","nonstopFlightsOnly":"false","bookingPostVerify":"RTR_YES","bundled":"off","segments":[{"origin":"JFK","destination":"LHR","originCountryCode":"US","destinationCountryCode":"GB","departureDate":"2024-10-31","connectionAirportCode":null}],"destinationAirportRadius":{"measure":100,"unit":"MI"},"originAirportRadius":{"measure":100,"unit":"MI"},"flexAirport":false,"flexDate":false,"flexDaysWeeks":"","passengers":[{"count":1,"type":"ADT"}],"meetingEventCode":"","bestFare":"VSLT","searchByCabin":true,"cabinFareClass":null,"refundableFlightsOnly":false,"deltaOnlySearch":"false","initialSearchBy":{"fareFamily":"VSLT","cabinFareClass":null,"meetingEventCode":"","refundable":false,"flexAirport":false,"flexDate":false,"flexDaysWeeks":"","deepLinkVendorId":null},"searchType":"search","searchByFareClass":null,"pageName":"FLIGHT_SEARCH","requestPageNum":"1","action":"findFlights","actionType":"","priceSchedule":"REVENUE","schedulePrice":"price","shopWithMiles":"","awardTravel":"false","datesFlexible":false,"flexCalendar":false,"upgradeRequest":false,"is_Flex_Search":true,"filter":null}'
#response = requests.post('https://www.virginatlantic.com/shop/ow/search', cookies=cookies, headers=headers, data=data)