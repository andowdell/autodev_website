import os
import re
import json
import time
import email
import imaplib
import requests
import playwright
import requests
from datetime import datetime, timedelta
from configparser import ConfigParser
from playwright.sync_api import expect, sync_playwright
from PIL import Image, ImageChops


proxy_host = "zproxy.lum-superproxy.io"
proxy_port = 22225
proxy_server = "zproxy.lum-superproxy.io:22225"
proxy_username = "lum-customer-hl_9827956f-zone-data_center-country-ch"
proxy_password = "xr3grz5w0cr8"

LOGIN_URL = "https://carauction.axa.ch/login.html"
MAIN_URL = "https://carauction.axa.ch/auction.html"
TARGET_DIR = "axa"
SESSION_FILE = "axa_session.json"

class AxaExtractor:
    def __init__(self, dir_path, code_files):
        self.codes = ConfigParser()
        self.codes.read(code_files)
        data_path = os.path.join(dir_path, TARGET_DIR)
        try:
            os.mkdir(data_path)
        except FileExistsError:
            pass
        self.data_path = data_path
        self.list = None

    def _login(self):
        self._save_cookies()
        self.page.goto(LOGIN_URL)
        login = self.codes.get('account', 'login')
        password = self.codes.get('account', 'pass')
        self.page.get_by_placeholder('Username').fill(login)
        self.page.get_by_placeholder('Password').fill(password)
        self.page.get_by_role("button", name="Sign in").click()

        try:
            self.page.locator("input[name=\"mfaForm\\:mfaCode\"]").click()
        except:
            self._save_cookies()
            return
        
        verification_code = self.get_verification_code()
        
        self.page.locator("input[name=\"mfaForm\\:mfaCode\"]").fill(verification_code)
        self.page.get_by_role("button", name="Submit").click()
        self._is_main_page()
        self._save_cookies()
        
    def _save_cookies(self):
        cookies = self.context.cookies()
        time.sleep(5)
        with open(os.path.join('sessions', SESSION_FILE), 'w') as file:
            file.write(json.dumps(self.context.cookies()))

    def _load_cookies(self):
        try:
            with open(os.path.join('sessions', SESSION_FILE), "r") as f:
                cookies = json.loads(f.read())
                self.context.add_cookies(cookies)
        except:
            pass
        
    def get_verification_code(self):
        print('[Downloader][AXA] Wait verification...')
        mail = imaplib.IMAP4_SSL(self.codes.get("email", "imap"))
        mail.login(self.codes.get("email", "username"), self.codes.get("email", "pass"))
        mail.select("inbox")
        
        # Define the time threshold (e.g., emails sent after this time will be fetched)
        time_threshold = datetime.now() - timedelta(minutes=2) # Example: 7 days ago

        # time_threshold_str = time_threshold.strftime("%d-%b-%Y %H:%M:%S")
        time_threshold_str = time_threshold.strftime("%d-%b-%Y")
        found = False
        # print(f'(SINCE "{time_threshold_str}")')
        while not found:
            self.page.wait_for_timeout(1000)
            # Search for emails sent after the specified time
            status, messages = mail.search(None, f'(SINCE "{time_threshold_str}")')
            mail_ids = messages[0].split()

            # Loop through the email IDs and fetch the corresponding emails
            for mail_id in mail_ids:
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                email_time = datetime.strptime(email_message["Date"], "%a, %d %b %Y %H:%M:%S %z (%Z)").replace(tzinfo=None)
                if email_time < time_threshold :
                    continue
                verification_code = self._extract_verification_code(email_message)
                if verification_code:
                    print(verification_code)
                    found = True
                    break
        mail.logout()
        return verification_code
        
    def _extract_verification_code(self, email_message):
        pattern = r"Ihr MFA-Code lautet: (\d+)"
        result = None
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    match = re.search(pattern, text)
                    if match:
                        result = match.group(1)
                        break
        else:
            # If the email is not multipart, directly extract the body
            text = (email_message.get_payload(decode=True).decode("utf-8", errors="ignore"))
            match = re.search(pattern, text)
            if match:
                result = match.group(1)
        return result
       
    def get_car_data(self):
        while self.list is None:
            self.page.wait_for_timeout(100)
        for car in self.list:
            try:
                self.get_car_detail(car)       
            except Exception:
                self.get_car_detail(car)
                
    def download_image(self, url, save_path):
        try:
            response = requests.get(url, headers={'Accept':'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'})
            if response.status_code == 200:
                with open(save_path, 'wb') as file:
                    file.write(response.content)
                return True
            else:
                return False
        except Exception as e:
            return False
        
    def _get_auction_enddate(self, auction_time_str):
        current_datetime = datetime.now()
        hours = minutes = seconds = 0 
        if len(auction_time_str.split(':')) == 2:
            minutes, seconds = map(int, auction_time_str.split(':'))
        elif len(auction_time_str.split(':')) == 3:
            hours, minutes, seconds = map(int, auction_time_str.split(':'))
        duration = timedelta(hours=hours, minutes=minutes, seconds=seconds) 
        result_datetime = current_datetime + duration
        if result_datetime.minute > 30:
            rounded_datetime = (result_datetime.replace(second=0, microsecond=0, minute=0) + timedelta(hours=1)).replace(minute=0)
        else:
            rounded_datetime= result_datetime.replace(minute=0, second=0, microsecond=0)
        return rounded_datetime  
          
    def get_car_detail(self, car):
        ret_car =dict()
        ret_car['title'] = car['at']
        ret_car['start_date']=None
        if 'edt' in car:
            ret_car['end_date'] = datetime.strptime(car['edt'].replace(' ', ''), "%d.%m.%Y-%H:%M").strftime("%Y-%m-%d %H:%M:%S")
        else:
            ret_car['end_date'] = None
        ret_car['images_count'] = 0
        ret_car['provider_name'] = 'axa'
        ret_car['provider_id'] = car['a']
        ret_car['brand_name'] = car['at'].split(' ')[0]
        ret_car['production_date'] =  datetime.strptime(car['r'], "%m/%Y").strftime("%Y-%m-01")
        if 'km' in car:
            ret_car['run'] = car['km']
        else:
            ret_car['run'] = 0
        car_json_path = os.path.join(self.data_path, '{}.json'.format(ret_car['provider_id']))        
        if os.path.exists(car_json_path):
            print('[Downloader][AXA][%s] The auction was already downloaded' % ret_car['provider_id'])
            return
        # self.page.goto('https://www.carauction.axa.ch/' + car['au'], timeout=10000)
        self.page.get_by_role('img', name=car['at']).click()
        ret_car['images'] = list()
        self.page.wait_for_load_state('load')
        self.page.wait_for_selector('#slider')

        for image_element in self.page.locator("#slider").get_by_role("listitem").all():
            image_id = image_element.get_attribute("data-id")
            if image_id:
                ret_car['images_count'] += 1
                ret_car["images"].append(f'{image_id}.jpg')
                if ret_car['images_count'] == 4:
                    break
        if ret_car['end_date'] is None:
            auction_time = self.page.locator(".auction-time").text_content()
            ret_car['end_date'] = self._get_auction_enddate(auction_time).strftime("%Y-%m-%d %H:%M:%S")
        # Extract extra info
        self.page.locator('.articledetail').wait_for()
        car_data = {}
        rows = self.page.locator('.articledetail').locator('tr')
        for row in rows.all():
            cells = row.locator('td').all()
            if (len(cells) >= 2):
                key = cells[0].text_content()
                value = cells[1].text_content()
                car_data[key] = value
        ret_car['data'] = car
        print('[Downloader][AXA][%s] New auction downloaded' % ret_car['provider_id'])
        with open(car_json_path, 'w') as f:
            json.dump(ret_car, f)
        self.page.get_by_role('img', name='AXA').click()
            
    def _is_main_page(self):
        try:
            expect(self.page.locator("#myaxaId")).to_be_visible(timeout=1000)
            return True
        except:
            return False
    
    def handle(self, route):
        response = route.fetch()
        try:
            json = response.json()
            self.list = json['list']
            route.fulfill(response=response, json=json)
        except requests.exceptions.HTTPError as err:
            self.handle
    
    def download(self, route, request):
        if 'original=true' not in request.url:
            route.abort()
            return
        response = route.fetch()
        pattern = r"fileId=(\d+)"
        match = re.search(pattern, request.url)
        if match:
            result = match.group(1)
            with open(os.path.join(self.data_path, f'Id_{result}.jpg'), 'wb') as file:
                file.write(response.body())
        route.fulfill(response=response) 
            
    def get_data(self):
        print('[Downloader][AXA] Start downloading...')
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            proxy={
            "server": "zproxy.lum-superproxy.io:22225",
            "username": "lum-customer-hl_9827956f-zone-data_center-country-ch",
            "password": "xr3grz5w0cr8"
            }
        )
        self.context = self.browser.new_context()
        self.context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
        self.context.route("https://carauction.axa.ch/javax.faces.resource/dynamiccontent.properties.html?*", self.download)
        self.context.route("https://carauction.axa.ch/auction/list/DE", self.handle)
        self._load_cookies()
        self.page = self.context.new_page()
        try:
            self.page.goto(MAIN_URL)
        except:
            print('[Downloader][AXA] Server connection failed...')
            self.context.close()
            self.browser.close()
            return
        if not self._is_main_page():
            print('[Downloader][AXA] Sign in...')
            self.page.goto(LOGIN_URL)
            self._login()
        self.get_car_data()
        print('[Downloader][AXA] Finish downloading')
        # self.page.wait_for_timeout(2000000)
        self.context.close()
        self.browser.close()

def main():
    extractor = AxaExtractor('../extracted', '../codes/axa.codes')
    extractor.get_data()
    
if __name__ == "__main__":
    main()