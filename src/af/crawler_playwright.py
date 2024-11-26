import base64
import datetime
import glob
import json
import logging
import os
import re
import shutil
import time
from typing import Iterator, Optional
from xml.dom import minidom

from scrapy import Selector

from playwright.sync_api import Locator, Page
from src import constants as c
from src.af.constants import CAPTCHA_MODEL, CabinClassCodeMapping
from src.exceptions import NoSearchResult
from src.playwright.base import PlaywrightBaseAirlineCrawler
from src.proxy import PrivateProxyService
from src.schema import CashFee, Flight, FlightSegment
from src.utils import (
    convert_time_string_to_iso_format,
    extract_currency_and_amount,
    extract_digits,
    extract_flight_number,
    extract_k_digits,
    extract_letters,
    parse_date,
    parse_time,
    sanitize_text,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class AirFrancePlaywrightCrawler(PlaywrightBaseAirlineCrawler):
    AIRLINE = c.Airline.AirFrance
    REQUIRED_LOGIN = True
    HOME_PAGE_URL = "https://wwws.airfrance.us/"
    RESPONSE_FORMAT: Optional[c.ResponseFormat] = c.ResponseFormat.Streaming

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._compute_latest_user_data_dir()

    def __del__(self):
        self._clean_outdate_user_data_dir()

    def _copytree(self, src, dst):
        """
        shutil.copytree didn't work as expected, use this simple command to
        preserve attributes/permissions of original folder
        """
        os.system("cp -a " + src + " " + dst)

    def _compute_latest_user_data_dir(self):
        """
        check if exist last user_data_dir belong to current user,
        if yes, clone this user_data_dir into new dir to keep last sesion session
        if no, return new latest empty dir
        """
        utc_now = datetime.datetime.utcnow().isoformat()
        pattern = re.sub("[@.:]", "-", f"user_data_dir_{self.username}*")
        user_data_dir_pattern = os.path.join(BASE_DIR, pattern)

        user_data_name = f"user_data_dir_{self.username}_{utc_now}"
        user_data_name = re.sub("[@.:]", "-", user_data_name)
        new_user_data_dir = os.path.join(BASE_DIR, user_data_name)
        # logger.info(f"new_user_data_name: {new_user_data_dir}")

        all_user_data_dirs = glob.glob(user_data_dir_pattern)
        # logger.info(f"all_user_data_dirs: {all_user_data_dirs}")

        if all_user_data_dirs:
            latest_user_data_dir = max(all_user_data_dirs, key=os.path.getmtime)
            logger.info(f"found latest user_data_dir: {latest_user_data_dir}")
            self._copytree(latest_user_data_dir, new_user_data_dir)
            time.sleep(5)

        self._user_data_dir = new_user_data_dir

    def _clean_outdate_user_data_dir(self):
        """
        Clean up all user_data_dir, only keep the latest one
        only delete user_data_dir of folder
        older than 15 minutes avoid to delete running chrome windows.
        (Assumed that each window has maxiumum 15 minutes to complete)
        """
        user_data_dir = os.path.join(BASE_DIR, re.sub("[@.:]", "-", f"user_data_dir_{self.username}*"))

        all_user_data_dirs = glob.glob(user_data_dir)
        MAX_COMPLETE_TIME = 60 * 15
        now = time.time()
        if all_user_data_dirs:
            last_user_data_dir = max(all_user_data_dirs, key=os.path.getmtime)
            logger.info(f"> cleanup oudate user_data_dir except for latest one: " f"{last_user_data_dir}")
            for user_data_dir in all_user_data_dirs:
                try:
                    if user_data_dir == last_user_data_dir:
                        continue
                    if os.path.getmtime(user_data_dir) < now - MAX_COMPLETE_TIME:
                        logger.info(
                            f"> cleanup oudate folder older than {(MAX_COMPLETE_TIME/60)}m user_data_dir: "
                            f"{user_data_dir}"
                        )
                        shutil.rmtree(user_data_dir)
                except Exception:
                    pass

    def get_proxy(self):
        return {
            "user": "ihgproxy1",
            "pwd": "ihgproxy1234_country-us",
            "ip": "geo.iproyal.com",
            "port": "12321",
        }

    def solve_captcha(self, captcha_svg: str, model: str = CAPTCHA_MODEL, length=4) -> str:
        """
        Solve SVG captcha using a predefined model.

        :param captcha_svg: svg captcha as xml string
        :param model: predefine model (base64string)
        :param length: amount of characters in the captcha
        :return: captcha solved value
        """
        logger.info(f"{self.AIRLINE.value}: solving capcha...")
        parsed_model = dict(json.loads(base64.b64decode(model)))
        element = minidom.parseString(captcha_svg)
        paths = element.getElementsByTagName("path")
        """Remove strokes"""
        nostroke_paths = [path for path in paths if len(path.getAttribute("stroke")) == 0]

        vals = [int(p.getAttribute("d").split(".")[0].replace("M", "")) for p in nostroke_paths]
        sorted_vals = sorted(vals)
        solution = [""] * length
        logger.info(f"{self.AIRLINE.value}: solving captcha....")
        for i, path in enumerate(nostroke_paths):
            try:
                pattern = re.sub("[\\d.\\s]*", "", path.getAttribute("d"))
                solution[sorted_vals.index(vals[i])] = parsed_model[pattern]
            except Exception as e:
                logger.error(f"{self.AIRLINE.value}: solve_captcha exception: {e}")

        return "".join(solution)

    def resolve_captcha_checkbox(self, *args, **kwargs):
        """
        <div class="rc-anchor-center-container">
            <div class="rc-anchor-center-item rc-anchor-checkbox-holder">
                <span class="recaptcha-checkbox goog-inline-block recaptcha-checkbox-unchecked rc-anchor-checkbox" role="checkbox" aria-checked="false" id="recaptcha-anchor" tabindex="0" dir="ltr" aria-labelledby="recaptcha-anchor-label">
                    <div class="recaptcha-checkbox-border" role="presentation"></div>
                    <div class="recaptcha-checkbox-borderAnimation" role="presentation"></div>
                    <div class="recaptcha-checkbox-spinner" role="presentation">
                        <div class="recaptcha-checkbox-spinner-overlay"></div>
                    </div>
                    <div class="recaptcha-checkbox-checkmark" role="presentation"></div>
                </span>
            </div>
        </div>
        """
        page: Page = kwargs.get("page")
        try:
            captcha = page.click("span.recaptcha-checkbox")
        except Exception as e:
            logger.error(f"{self.AIRLINE.value}: resolve captcha exception: {e}")

    def resolve_captcha_text(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        try:
            captcha = page.locator(".asfc-svg-captcha")
            captcha.wait_for(timeout=20000)
            captcha_text = ""
            captcha_success = False
            while len(captcha_text) != 4 or captcha_success is False:
                content = page.locator("span.asfc-svg-captcha svg").evaluate("el => el.outerHTML")
                logger.info(f"{self.AIRLINE.value}: resolving capcha...")
                captcha_text = self.solve_captcha(content)
                # resolve_recaptcha_api(content)
                logger.info(f"{self.AIRLINE.value}: resolved capcha: {captcha_text}")
                if len(captcha_text) != 4:
                    # click refresh new captcha:
                    page.click(".asfc-svg-content button")
                    logger.info(f"{self.AIRLINE.value}: resolved capcha is not successul, retry new captcha")
                    time.sleep(1)
                else:
                    self.human_typing(page, page.locator("input#mat-input-3"), captcha_text)
                    page.click("button[data-test=button-QCUpXk0XAP]")
                    try:
                        time.sleep(2)
                        error_element = page.locator("asfc-form-error")
                        error_element.wait_for(timeout=2000)
                        captcha_text = ""
                    except Exception:
                        captcha_success = True

        except Exception as e:
            logger.error(f"{self.AIRLINE.value}: resolve captcha exception: {e}")

    def _select_miles(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.click("#mat-tab-label-1-1")
        time.sleep(2)

    def _select_oneway(self, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.locator('select[formcontrolname="tripKind"]').select_option("oneway")
        time.sleep(0.5)

    def _select_origin(self, origin: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.fill('input[data-test-value="origin"]', origin)
        page.locator('input[data-test-value="origin"]').press("Enter")
        time.sleep(0.5)

    def _select_destination(self, destination: str, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.fill('input[data-test-value="destination"]', destination)
        page.locator('input[data-test-value="destination"]').press("Enter")
        time.sleep(0.5)

    def _select_cabin_class(self, cabin_class: c.CabinClass, *args, **kwargs) -> None:
        try:
            page: Page = kwargs.get("page")
            cabin_class_code = CabinClassCodeMapping[cabin_class]
            page.locator("[data-test='bwsfe-widget__cabin-class-select']").select_option(cabin_class_code)
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"{self.AIRLINE.value}: can't select cabin class {e}")
            raise NoSearchResult(airline=self.AIRLINE)

    def _select_date(self, departure_date: datetime.date, *args, **kwargs) -> None:
        page: Page = kwargs.get("page")
        page.click('button[data-test="bwsfe-widget__open-search-button"]')
        time.sleep(1)
        month_year = departure_date.strftime("%B %Y")
        if datetime.date.today().year == departure_date.year:
            month_year = departure_date.strftime("%B")
        departure_date_str = departure_date.strftime("%d %B %Y")
        # page.click("input[data-test=bwsfe-datepicker__input]")
        page.locator("bwc-date-picker-toggle-button[data-test='bwsfe-datepicker__toggle-button'] button").click()
        time.sleep(0.5)

        while True:
            try:
                found = False
                calendar_months = page.locator("bwc-month h2").all()
                for calendar_month in calendar_months:
                    calendar_month = calendar_month.text_content().strip()
                    print(f">>>>>>>>> {calendar_month} - {month_year}")
                    print(f">>>>>>>>> {departure_date_str}")
                    if calendar_month == month_year:
                        page.click(f"button[aria-label='{departure_date_str}']")
                        time.sleep(0.5)
                        page.click(f"button[data-test='bwc-calendar__confirm']")
                        time.sleep(0.5)
                        found = True
                        break
                if found:
                    break
                page.click("button[data-test='bwc-calendar__next-month-button']")
            except Exception as e:
                logger.error(f"{self.AIRLINE.value}: _select_date exception: {e}")
                page.click("button[data-test='bwc-calendar__next-month-button']")
                time.sleep(0.5)

        time.sleep(1)

    def _select_passengers(self, *args, **kwargs):
        pass

    def _submit(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        page.click("button[data-test='bwsfe-widget__search-button']")
        time.sleep(2)
        max_time = 60
        while page.locator('ol[data-test="bwsfe-itinerary-list"]').count() == 0 and max_time > 0:
            logger.info(f"{self.AIRLINE.value}: submitted - waiting for results: " f"{max_time}s remaining ")
            time.sleep(1)
            max_time -= 1

    def _close_cookie_popup(self, page):
        try:
            cookie = page.locator("#accept_cookies_btn")
            cookie.wait_for(timeout=2000)
            page.click("button#accept_cookies_btn")
            logger.info("clicked accept cookie popup")
        except Exception as e:
            logger.error(f"click accept cookie popup error: {e}")
            pass

    def _login(self, *args, **kwargs):
        page: Page = kwargs.get("page")
        username: str = kwargs.get("username")
        password: str = kwargs.get("password")
        if username is None or password is None:
            username = self.username
            password = self.password

        try:
            profile = page.locator("span.bwc-o-body-variant.bwc-logo-header__user-name")
            profile.wait_for(timeout=20000)
            need_login = False
        except Exception as e:
            logger.error(f"need to login exeption: {e}")
            need_login = True

        if need_login:
            self._close_cookie_popup(page)

            page.click("button.bwc-logo-header__login-button")
            time.sleep(10)
            page.click('a[data-test="prefer-password-Gio6I8Xv3U"]')
            time.sleep(10)
            self.human_typing(page, page.locator('input[formcontrolname="loginId"]'), username)
            time.sleep(2)
            self.human_typing(page, page.locator('input[formcontrolname="password"]'), password)
            time.sleep(1)

            # sometimes, cookie popup shows lately, to be sure, we check again here
            self._close_cookie_popup(page)

            page.click("button[data-test=button-QCUpXk0XAP]")
            time.sleep(2)
            self.resolve_captcha_checkbox(page=page)

    def _is_no_flights(self, page):
        """
        Check warning when there is no flights:
            Sorry, there are no flights with seats
            available in the cabin you selected.
            Alternative options in the Business cabin are listed below.
        @return:
            True: can't find avaible flights
            False: there is flights, continue to extract
        """
        try:
            no_flights_notfication_ele = page.locator("div.bwc-notification__container div.bwc-notification__main p")
            no_flights_notfication_ele.wait_for(timeout=3000)
            warning_text = self.get_text(no_flights_notfication_ele)
            return "there are no flights with seats" in warning_text
        except Exception:
            return False

    def extract_points(self, cabin_class: c.CabinClass, flight_row_element: Locator) -> Optional[int]:
        target_cabin_class = CabinClassCodeMapping[cabin_class].title()
        for card_ele in flight_row_element.locator("bwsfc-cabin-class-card").all():
            try:
                header_ele = card_ele.locator("button.bwsfc-cabin-class-card__header-button span")
                header_ele.wait_for(timeout=200)
                header_cabin_class = self.get_text(header_ele)
                if header_cabin_class != target_cabin_class:
                    continue

                points_ele = card_ele.locator(
                    "div.bwsfc-cabin-class-card__content div.bwsfc-cabin-class-card__price-content"
                )
                points_ele.wait_for(timeout=200)
                points = self.get_text(points_ele)
                return int(extract_k_digits(points))
            except Exception as e:
                logger.error(f"{self.AIRLINE.value}: look for cabin class points error: {e}")

    def parse_old_ui_flights(self, page, departure_date: datetime.date, cabin_class: c.CabinClass) -> Iterator[Flight]:
        content = page.content()
        dom = Selector(text=content)
        flight_search_results = dom.xpath("//bw-itinerary-list/ol/li")
        logger.info(f"{self.AIRLINE.value}: Found {len(flight_search_results)}flights...")
        for index, flight_row_element in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Parsing {index}th flight...")
            origin_airport_element = flight_row_element.xpath(".//bws-flight-locations/ol/li[1]/text()")
            origin = origin_airport_element and extract_letters(origin_airport_element[0].get()) or ""

            destination_airport_element = flight_row_element.xpath(".//bws-flight-locations/ol/li[last()]/text()")
            destination = destination_airport_element and extract_letters(destination_airport_element[0].get()) or ""

            departure_time = convert_time_string_to_iso_format(
                sanitize_text(flight_row_element.xpath(".//bws-flight-times/span/time[1]/text()").get())
            )
            arrival_time = convert_time_string_to_iso_format(
                sanitize_text(flight_row_element.xpath(".//bws-flight-times/span/time[last()]/text()").get())
            )

            days_change = flight_row_element.xpath(
                ".//bws-flight-times//span[contains(@class, 'bws-flight-times__day-change')]/text()"
            ).get()
            if days_change:
                days = extract_digits(days_change)
                arrival_date = departure_date + datetime.timedelta(days=int(days))
            else:
                arrival_date = departure_date
            duration = flight_row_element.xpath(".//bws-flight-duration/div/time/text()").get()

            stops = len(flight_row_element.xpath(".//bws-flight-locations/ol/li")) - 2

            points = flight_row_element.xpath(".//bw-itinerary-select/button//bw-price/span[1]/text()").get()
            points = extract_digits(points)
            cash_fee = flight_row_element.xpath(".//bw-itinerary-select/button//bw-price/span[last()]/text()").get()
            currency, amount = extract_currency_and_amount(cash_fee)
            segments_element = flight_row_element.xpath(".//bws-flight-operators//bwc-carrier-logo")
            segments = []
            segments_length = len(segments_element)
            for segment_index, segment_element in enumerate(segments_element):
                label = segment_element.xpath("./@aria-label").get()
                origin_city, destination_city = label.split(",")[0].split(" to ")
                carrier, flight_number = extract_flight_number(label)

                segment_departure_date = departure_date.isoformat() if segment_index == 0 else None
                segment_departure_time = departure_time if segment_index == 0 else None
                segment_arrival_date = arrival_date.isoformat() if segment_index == segments_length - 1 else None
                segment_arrival_time = arrival_time if segment_index == segments_length - 1 else None
                segment_origin = origin if stops == 0 or segment_index == 0 else origin_city
                segment_destination = (
                    destination if stops == 0 or segment_index == segments_length - 1 else destination_city
                )

                segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_date,
                        departure_time=segment_departure_time,
                        departure_timezone="",
                        arrival_date=segment_arrival_date,
                        arrival_time=segment_arrival_time,
                        arrival_timezone="",
                        duration="",
                        aircraft="",
                        flight_number=flight_number,
                        carrier=carrier,
                    )
                )

            yield Flight(
                airline=str(self.AIRLINE.value),
                origin=origin,
                destination=destination,
                cabin_class=str(cabin_class.value),
                airline_cabin_class=str(cabin_class.value),
                points=points,
                cash_fee=CashFee(amount=amount, currency=currency),
                segments=segments,
                duration=duration,
            )

    def parse_new_ui_flights(self, page, departure_date: datetime.date, cabin_class: c.CabinClass) -> Iterator[Flight]:
        logger.info(f"{self.AIRLINE.value}: extracting result")
        try:
            flight_search_results = page.locator("//bwsfe-search-result-list/section/ol/li").all()
            logger.info(f"Found {len(flight_search_results)}flights...")
        except TimeoutError:
            raise NoSearchResult(airline=self.AIRLINE)

        for index, flight_row_element in enumerate(flight_search_results):
            logger.info(f"{self.AIRLINE.value}: Parsing {index}th flight...")

            points = self.extract_points(cabin_class, flight_row_element)
            if points is None:
                continue

            offer_card = flight_row_element.locator("div.bwsfc-flight-offer__flight-card")
            # carrier = ""
            # try:
            #     carrier_ele = offer_card.locator("bwsfc-operating-carrier bwc-carrier-logo.bwc-carrier-logo")
            #     carrier_ele.wait_for(timeout=200)
            #     carrier_ele.get_attribute("aria-label")
            # except Exception:
            #     pass
            #
            # try:
            #     carrier_ele = offer_card.locator("bwsfc-operating-carrier span.bwsfc-operating-carrier__name")
            #     carrier_ele.wait_for(timeout=200)
            #     carrier = self.get_text(carrier_ele)
            # except Exception:
            #     pass
            #
            # departure_time_ele = (
            #     offer_card.locator("bwsfc-itinerary-station-node")
            #     .nth(0)
            #     .locator("div.bwsfc-itinerary-station-node__scheduled-time time")
            # )
            # departure_time = self.get_text(departure_time_ele)
            #
            # arrival_time_ele = (
            #     offer_card.locator("bwsfc-itinerary-station-node")
            #     .nth(1)
            #     .locator("div.bwsfc-itinerary-station-node__scheduled-time time")
            # )
            # arrival_time = self.get_text(arrival_time_ele)
            #
            # origin_airport_ele = (
            #     offer_card.locator("bwsfc-itinerary-station-node")
            #     .nth(0)
            #     .locator("div.bwsfc-itinerary-station-node__station-code")
            # )
            # origin = self.get_text(origin_airport_ele)
            #
            # destination_airport_ele = (
            #     offer_card.locator("bwsfc-itinerary-station-node")
            #     .nth(1)
            #     .locator("div.bwsfc-itinerary-station-node__station-code")
            # )
            # destination = self.get_text(destination_airport_ele)

            segments = []

            offer_card.locator("button.bwsfc-flight-offer__flight-details-button").click()
            time.sleep(2)
            while page.locator("mat-dialog-content.bwsfc-flight-details__content").count() == 0:
                logger.info(f"{self.AIRLINE.value}: waiting for loading flights details")
                time.sleep(1)

            segment_eles = page.locator("mat-dialog-content.bwsfc-flight-details__content ol li").all()
            for segment_ele in segment_eles:
                origin_destination_section = segment_ele.locator(
                    "div.bwsfc-flight-details__segment bwsfc-segment-nodes "
                    "div.bwsfc-segment-nodes__station-nodes bwsfc-segment-station-node"
                )
                origin_section = origin_destination_section.nth(0)

                departure_date_ele = origin_section.locator("div.bwsfc-segment-station-node__scheduled-date time")
                segment_departure_date = self.get_text(departure_date_ele)

                segment_departure_date = parse_date(segment_departure_date, "%a %d %b")
                segment_departure_date = datetime.date.fromisoformat(segment_departure_date).replace(
                    year=departure_date.year
                )
                segment_departure_date = segment_departure_date.isoformat()

                departure_time_ele = origin_section.locator("div.bwsfc-segment-station-node__time-code span time")
                segment_departure_time = self.get_text(departure_time_ele)
                segment_departure_time = parse_time(segment_departure_time, "%I:%M %p")

                origin_airport_ele = origin_section.locator("div.bwsfc-segment-station-node__time-code p")
                segment_origin = self.get_text(origin_airport_ele)

                #######
                destination_section = origin_destination_section.nth(1)
                arrival_date_ele = destination_section.locator("div.bwsfc-segment-station-node__scheduled-date time")
                segment_arrival_date = self.get_text(arrival_date_ele)
                segment_arrival_date = parse_date(segment_arrival_date, "%a %d %b")
                segment_arrival_date = datetime.date.fromisoformat(segment_arrival_date).replace(
                    year=departure_date.year
                )
                segment_arrival_date = segment_arrival_date.isoformat()
                arrival_time_ele = destination_section.locator("div.bwsfc-segment-station-node__time-code span time")
                segment_arrival_time = parse_time(self.get_text(arrival_time_ele), "%I:%M %p")

                destination_airport_ele = destination_section.locator("div.bwsfc-segment-station-node__time-code p")
                segment_destination = self.get_text(destination_airport_ele)

                ####
                connector_section = segment_ele.locator(
                    "div.bwsfc-flight-details__segment bwsfc-segment-nodes "
                    "bwsfc-segment-node-connector.bwsfc-segment-nodes__node-connector"
                )
                duration_ele = connector_section.locator("div.bwsfc-segment-node-connector__duration")
                duration = self.get_text(duration_ele).replace("Duration:", "").strip()

                # operator = ""
                # try:
                #     operator_ele = connector_section.locator("bwsfc-operating-carrier bwc-carrier-logo")
                #     operator_ele.wait_for(200)
                #     operator = operator_ele.get_attribute("aria-label")
                # except Exception:
                #     pass
                #
                # try:
                #     operator_ele = connector_section.locator("bwsfc-operating-carrier span")
                #     operator_ele.wait_for(200)
                #     operator = self.get_text(operator_ele)
                # except Exception:
                #     pass

                # segment_carrier = ""
                # try:
                #     carrier_ele = connector_section.locator(
                #         "bwsfc-operating-carrier bwc-carrier-logo.bwc-carrier-logo"
                #     )
                #     carrier_ele.wait_for(timeout=200)
                #     segment_carrier = carrier_ele.get_attribute("aria-label")
                # except Exception:
                #     pass
                #
                # try:
                #     carrier_ele = connector_section.locator(
                #         "bwsfc-operating-carrier span.bwsfc-operating-carrier__name"
                #     )
                #     carrier_ele.wait_for(timeout=200)
                #     segment_carrier = self.get_text(carrier_ele)
                # except Exception:
                #     pass

                flight_number_aircraft_ele = connector_section.locator("div.bwsfc-segment-node-connector__equipment")
                flight_number_aircraft = self.get_text(flight_number_aircraft_ele)
                flight_number_aircraft = flight_number_aircraft.split(",")
                flight_number = flight_number_aircraft and flight_number_aircraft[0] or ""
                segment_carrier, flight_number = extract_flight_number(flight_number)
                aircraft = flight_number_aircraft and flight_number_aircraft[1] or ""

                segments.append(
                    FlightSegment(
                        origin=segment_origin,
                        destination=segment_destination,
                        departure_date=segment_departure_date,
                        departure_time=segment_departure_time,
                        departure_timezone="",
                        arrival_date=segment_arrival_date,
                        arrival_time=segment_arrival_time,
                        arrival_timezone="",
                        duration=duration,
                        aircraft=aircraft,
                        flight_number=flight_number,
                        carrier=segment_carrier,
                    )
                )

            page.click("button.bwsfc-flight-details__close-button")
            duration_ele = offer_card.locator(
                "bwsfc-itinerary-node-connector div.bwsfc-itinerary-node-connector__content div"
            ).nth(1)
            duration = self.get_text(duration_ele)
            amount = 0
            currency = ""
            yield Flight(
                airline=str(self.AIRLINE.value),
                origin=segments[0].origin,
                destination=segments[-1].destination,
                cabin_class=str(cabin_class.value),
                airline_cabin_class=str(cabin_class.value),
                points=points,
                cash_fee=CashFee(amount=amount, currency=currency),
                segments=segments,
                duration=duration,
            )

    def parse_flights(self, page, departure_date: datetime.date, cabin_class: c.CabinClass) -> Iterator[Flight]:
        is_no_flights = self._is_no_flights(page)
        if is_no_flights:
            return NoSearchResult(airline=self.AIRLINE)

        if page.locator("//bwsfe-search-result-list/section/ol/li").count():
            for flight in self.parse_new_ui_flights(page, departure_date, cabin_class):
                yield flight
        else:
            for flight in self.parse_old_ui_flights(page, departure_date, cabin_class):
                yield flight


if __name__ == "__main__":
    from dataclasses import asdict

    def run(origin, destination, cabin_class):
        start_time = time.perf_counter()
        crawler = AirFrancePlaywrightCrawler()
        departure_date = datetime.date.today() + datetime.timedelta(days=14)
        departure_date = datetime.date(year=2024, month=6, day=24)

        flights = list(
            crawler.run(
                origin=origin,
                destination=destination,
                departure_date=departure_date.isoformat(),
                cabin_class=cabin_class,
            )
        )
        end_time = time.perf_counter()

        if flights:
            with open(f"{crawler.AIRLINE.value}-{origin}-{destination}-{cabin_class.value}.json", "w") as f:
                json.dump([asdict(flight) for flight in flights], f, indent=2)
        else:
            print("No result")
        print(f"It took {end_time - start_time} seconds.")

    # run("PVG", "ICN", c.CabinClass.Economy)
    run("JFK", "CDG", c.CabinClass.Business)
    # run("YVR", "YYZ", c.CabinClass.PremiumEconomy)
    # run("YVR", "YYZ", c.CabinClass.Business)
    # run("KUL", "YYZ", c.CabinClass.First)
