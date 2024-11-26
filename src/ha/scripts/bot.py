import re
import csv
import time
import os
import datetime
# from playwright.sync_api import Page, expect
from undetected_playwright.sync_api import sync_playwright
from undetected_playwright.sync_api import Playwright as SyncPlaywright
from undetected_playwright.sync_api import Locator, Page
import random
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_RTC_PATH = os.path.join(BASE_DIR, "webrtc_addon")

email_providers = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com', 'aol.com', 'icloud.com', 'protonmail.com', 'zoho.com', 'mail.com', 'fastmail.com']
first_names = ['Henry', 'Sergio', 'Tomas', 'Becky', 'Jonathan']
last_names = ['Morgan', 'Calvo', 'Jonhson', 'Pinto', 'Montea']
addresses = [
    'Patona Ul., std. 5, appt. 67',
    'Komarova Kosmonavta Pr-T, bld. 1',
    'Bogatyrskaya Ul., bld. 2, appt. 338',
    'Geroev Stalingrada Pr-T, bld. 38, appt. 29',
    'Peyzazhnaya Ul., bld. 104, appt. 58'
]

def human_typing(page: Page, element: Locator, text: str, speed=(0.003, 0.005)):
        element.focus()
        for character in text:
            time.sleep(random.uniform(*speed))
            page.keyboard.press(character)

def get_unique_string():
    timestamp = datetime.datetime.now().strftime('%m%d%H%M')
    return str(timestamp[:16])

def get_random_number():
    return str(random.randint(1000000000, 9999999999))

def get_random_zipcode():
    return str(random.randint(1000, 4200))

def export_to_csv(data):
    # Check if the file already exists
    file_exists = os.path.isfile('account_data.csv')
    
    with open('account_data.csv', "a", newline="") as file:
        fieldnames = ["email", "username", "password"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        # Write the header only if the file does not already exist
        if not file_exists:
            writer.writeheader()
        
        # for item in data:
        writer.writerow(data)

def create_multiple_accounts(page: Page):
    # num_times = int(input("How many times do you want to run the function? "))

    # for i in range(3):
    account_create(page)
        # time.sleep(30)



def account_create(page: Page):
    page.goto("https://www.hawaiianairlines.com/my-account/join-hawaiianmiles", timeout=120000)
    first_name = random.choice(first_names)

    human_typing(page, page.locator('xpath=//input[@id="sign_up_first_name"]'), first_name)
    time.sleep(1)
    human_typing(page, page.locator('xpath=//input[@id="sign_up_last_name"]'), random.choice(last_names))
    time.sleep(1)

    # select gender
    page.select_option('select[name="MemberPersonalInfo.Gender"]', 'M')

    # select DOB
    page.select_option('select[name="dobMonth"]', 'string:7')
    page.select_option('select[name="dobDay"]', 'string:11')
    page.select_option('select[name="dobYear"]', 'string:1994')

    # click next button
    page.click('xpath=//a[@class="btn-primary btn-lg btn-1"]')

    # input email address
    username = first_name.lower() + get_unique_string()
    email_address = username + "@" + random.choice(email_providers)
    page.wait_for_selector('xpath=//input[@id="sign_up_email_address"]', timeout=10000)
    human_typing(page, page.locator('xpath=//input[@id="sign_up_email_address"]'), email_address)
    time.sleep(3)
    page.click('xpath=//input[@id="phone_number"]')
    time.sleep(1)
    human_typing(page, page.locator('xpath=//input[@id="phone_number"]'), get_random_number())
    time.sleep(1)

    # select country
    page.locator('xpath=//select[@id="MemberAddress.CountryData"]').select_option(label='Ukraine')

    # input zipcode
    human_typing(page, page.locator('xpath=//input[@id="zip_code"]'), "0" + get_random_zipcode())
    time.sleep(3)

    # select state
    page.locator('xpath=//select[@id="MemberAddress.StateData"]').select_option(label='Kiev')
    # page.select_option('#MemberAddress.StateData', 'object:1038')
    time.sleep(1)

    # input city
    human_typing(page, page.locator('xpath=//input[@id="city"]'), "Kiev")
    time.sleep(1)

    # input address
    human_typing(page, page.locator('xpath=//input[@id="address"]'), random.choice(addresses))
    time.sleep(1)
    
    # click next btn
    page.click('xpath=//a[@class="btn-primary btn-lg btn-2"]')
    time.sleep(3)

    # input username
    page.wait_for_selector('xpath=//input[@id="sign_up_username"]', timeout=1000000)
    human_typing(page, page.locator('xpath=//input[@id="sign_up_username"]'), username.lower())
    time.sleep(3)

    # input password
    page.click('xpath=//input[@id="password"]')
    time.sleep(1)
    human_typing(page, page.locator('xpath=//input[@id="password"]'), 'QWEqwe!@#123')
    time.sleep(1)

    # confirm password
    human_typing(page, page.locator('xpath=//input[@id="confirm_password"]'), 'QWEqwe!@#123')
    time.sleep(1)

    # click join now btn
    page.click('xpath=//button[@id="create_account"]')

    # confirm success
    try:
        success_modal = page.locator('xpath=//p[@class="congrats desktop-only"]')
        success_modal.wait_for(timeout=60000)

        new_account = {
            "email": email_address,
            "username": username,
            "password": "QWEqwe!@#123"
        }

        signin_to_complete(page, username)
        print("Successfully created!!! Username = ", username)
        return new_account
    except TimeoutError:
        print("Failed Username = ", username)

def signin_to_complete(page: Page, username):
    # login to complete signup
    page.goto("https://www.hawaiianairlines.com/my-account/login/?ReturnUrl=%2fmy-account", timeout=120000)

    # input username
    human_typing(page, page.locator('xpath=//input[@id="user_name"]'), username)
    time.sleep(3)

    # input password
    human_typing(page, page.locator('xpath=//input[@id="password"]'), 'QWEqwe!@#123')
    time.sleep(3)

    # click login button
    page.click('xpath=//button[@id="submit_login_button"]')

    # select question 1
    page.locator('xpath=//select[@id="security_question_one"]').select_option(value='1')
    time.sleep(3)

    # input question 1
    human_typing(page, page.locator('xpath=//input[@id="security_answers_one"]'), 'New York')
    time.sleep(1)

    # select question 2
    page.locator('xpath=//select[@id="security_question_two"]').select_option(value='2')
    time.sleep(3)

    # input question 2
    human_typing(page, page.locator('xpath=//input[@id="security_answers_two"]'), 'Olek')
    time.sleep(1)

    # select question 3
    page.locator('xpath=//select[@id="security_question_three"]').select_option(value='3')
    time.sleep(3)

    # input question 3
    human_typing(page, page.locator('xpath=//input[@id="security_answers_three"]'), 'Olek')
    time.sleep(1)

    # check accept terms and conditions
    page.click('label[for="trueUpTerms"]')

    # click confirm button
    page.click('xpath=//button[@id="confirm_and_sign_in"]')

    # confirm success
    try:
        profile = page.locator('xpath=//a[@id="my_account_user_dropdown"]')
        profile.wait_for(timeout=60000)
        page.close()

        dir_url = os.path.join(BASE_DIR, "user_data_dir")
        try:
            shutil.rmtree(dir_url)
        except PermissionError:
            print("Unable to delete the directory. Retrying in 5 seconds...")
            time.sleep(5)
            try:
                shutil.rmtree(dir_url)
            except PermissionError:
                print("Unable to delete the directory.")
        print("Successfully added security questions")
        return
    except TimeoutError:
        print("Failed to add security questions")


def launch_browser_with_proxy(**kwargs):
    playwright: SyncPlaywright = kwargs.get("playwright")
    args = [
        "--disable-blink-features=AutomationControlled",
        f"--disable-extensions-except={WEB_RTC_PATH}",
        f"--load-extension={WEB_RTC_PATH}",
    ]
    return playwright.chromium.launch_persistent_context(
        headless=False,  # Set to True if you do not need a browser UI
        proxy={
            'server': 'geo.iproyal.com:12321',
            'username': 'ihgproxy1',
            'password': 'ihgproxy1234_country-us'
        },
        slow_mo=100,
        user_data_dir=BASE_DIR + "/user_data_dir",
        args=args
    )

def main():
    with sync_playwright() as p:
        # Launching the browser with proxy settings
        browser = launch_browser_with_proxy(playwright=p)
        browser.set_default_navigation_timeout(200 * 1000)
        page = browser.new_page()

        # Implement your scraping logic here
        create_multiple_accounts(page)

        # Closing the browser
        browser.close()

if __name__ == '__main__':
    main()
