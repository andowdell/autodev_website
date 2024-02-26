import os
import re
import json
import imaplib
import requests
import email
import time
from configparser import ConfigParser
from datetime import datetime, timedelta
from playwright.sync_api import expect, sync_playwright
from data_logger.data_logger import DataLogger
logger = DataLogger.get_logger(__name__)

LOGIN_URL = 'https://www.allianz-carauction.ch/login.html'
MAIN_URL = 'https://www.allianz-carauction.ch/auction.html'
SESSION_FILE = "allianz.session"
TARGET_DIR = 'allianz'

class AllianzExtractor:

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
    
    def get_verification_code(self):
        logger.info('[Downloader][ALLIANZ] Wait verification...')
        print('[Downloader][ALLIANZ] Wait verification...')
        # Connect to the email server
        mail = imaplib.IMAP4_SSL(self.codes.get("email", "imap"))
        # specify your IMAP server here
        mail.login(self.codes.get("email", "username"), self.codes.get("email", "pass"))
        mail.select("inbox")
            
        # Define the time threshold (e.g., emails sent after this time will be fetched)
        time_threshold = datetime.now() - timedelta(minutes=61) # Example: 7 days ago

        # time_threshold_str = time_threshold.strftime("%d-%b-%Y %H:%M:%S")
        time_threshold_str = time_threshold.strftime("%d-%b-%Y")
        found = False
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
    
    def _save_cookies(self):
        cookies = self.context.cookies()
        with open(os.path.join('sessions', SESSION_FILE), 'w') as file:
            file.write(str(cookies))

    def _load_cookies(self):
        try:
            # Read cookies from a file
            with open(os.path.join('sessions', SESSION_FILE), 'r') as file:
                cookies = eval(file.read())  # Note: Evaluate the string to convert it to a list
            self.context.add_cookies(cookies)
        except:
            pass

    def _login(self):
        self._save_cookies()
        self.page.goto(LOGIN_URL)
        login = self.codes.get('account', 'login')
        password = self.codes.get('account', 'password')
        self.page.get_by_placeholder('Benutzername').fill(login)
        self.page.get_by_placeholder('Passwort').fill(password)
        self.page.get_by_role("button", name="Einloggen").click() 
        if self._is_main_page():
            self._save_cookies()
            return True
        elif self._is_verification_page():
            try:
                self.page.locator("input[name=\"mfaForm\\:mfaCode\"]").click()
                verification_code = self.get_verification_code()
                self.page.locator("input[name=\"mfaForm\\:mfaCode\"]").fill(verification_code)
                self.page.get_by_role("button", name="Senden").click()
                self._save_cookies()
                return True
            except:
                self._save_cookies()
                return False
        else:
            return False

    def get_car_data(self):
        start_time = time.time()

        while self.list is None:
            self.page.wait_for_timeout(1000)
            if time.time() - start_time >= 60:
                print('[Downloader][ALLIANZ] The main Page is not responding...')
                logger.info('[Downloader][ALLIANZ] The main Page is not responding...')
                break
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
        ret_car = dict()
        ret_car['title'] = car['at']
        ret_car['start_date'] = None
        if 'edt' in car:
            ret_car['end_date'] = datetime.strptime(car['edt'].replace(' ', ''), "%d.%m.%Y-%H:%M").strftime("%Y-%m-%d %H:%M:%S")
        else:
            ret_car['end_date'] = None
        ret_car['images_count'] = 0
        ret_car['provider_name'] = 'allianz'
        ret_car['provider_id'] = car['a']
        ret_car['brand_name'] = car['at'].strip().split(' ')[0]
        ret_car['production_date'] =  datetime.strptime(car['r'], "%m/%Y").strftime("%Y-%m-01")
        if 'km' in car:
            ret_car['run'] = car['km']
        else:
            ret_car['run'] = 0
        car_json_path = os.path.join(self.data_path, '{}.json'.format(ret_car['provider_id']))
        if os.path.exists(car_json_path):
            logger.info('[Downloader][ALLIANZ][%s] The auction was already downloaded' % ret_car['provider_id'])
            print('[Downloader][ALLIANZ][%s] The auction was already downloaded' % ret_car['provider_id'])
            return
        self.page.goto('https://www.allianz-carauction.ch/' + car['au'], timeout=10000)
        self.page.wait_for_load_state('load')
        ret_car['images'] = list()
        self.page.locator('#slider').wait_for()
        for image_element in self.page.locator("#slider").get_by_role("listitem").all():
            image_id = image_element.get_attribute("data-id")
            if image_id:
                ret_car["images"].append(f'{image_id}.jpg')
                ret_car['images_count'] += 1
            # if ret_car['images_count'] == 4:
            #     break
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
        self.page.locator('#description').wait_for()
        rows = self.page.locator('#description').locator('tr')
        for row in rows.all():
            cells = row.locator('td').all()
            if (len(cells) >= 2):
                key = cells[0].text_content()
                value = cells[1].text_content()
                car_data[key] = value
        self.page.locator('#state').wait_for()
        rows = self.page.locator('#state').locator('tr')
        for row in rows.all():
            cells = row.locator('td').all()
            if (len(cells) >= 2):
                key = cells[0].text_content()
                value = cells[1].text_content()
                car_data[key] = value
        car_data['Sonderausstattung'] = self.page.locator("#special").text_content()
        car_data['Serienausstattung'] = self.page.locator("#serien").text_content()
        ret_car['data'] = car_data
        logger.info('[Downloader][ALLIANZ][%s] New auction downloaded' % ret_car['provider_id'])
        print('[Downloader][ALLIANZ][%s] New auction downloaded' % ret_car['provider_id'])
        with open(car_json_path, 'w') as f:
            json.dump(ret_car, f)
    
    def _is_main_page(self):
        try:
            expect(self.page.locator("#auctiontable")).to_be_visible()
            return True
        except:
            return False

    def _is_verification_page(self):
        try:
            expect(self.page.locator("#mfaDialog")).to_be_visible()
            return True
        except:
            return False


    def handle(self, route):
        response = route.fetch()
        # response.raise_for_status()
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
            with open(os.path.join(self.data_path, f'id_{result}.jpg'), 'wb') as file:
                file.write(response.body())
        route.fulfill(response=response)      
  
   
    def get_data(self):
        logger.info('[Downloader][ALLIANZ] Start downloading...')
        print('[Downloader][ALLIANZ] Start downloading...')
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                proxy= {
                "server": self.codes.get("proxy", "server"),
                "username": self.codes.get("proxy", "username"),
                "password": self.codes.get("proxy", "password")
                }
            )
            self.context = self.browser.new_context()
            self.context.route("**/*.{png,jpg,jpeg}", lambda route: route.abort())
            self.context.route("https://www.allianz-carauction.ch/javax.faces.resource/dynamiccontent.properties.html?*", self.download)
            self.context.route("https://www.allianz-carauction.ch/auction/list/DE", self.handle)
            self._load_cookies()
            self.page = self.context.new_page()
            self.page.goto(MAIN_URL)
            if not self._is_main_page():
                logger.info('[Downloader][ALLIANZ] Sign in...')
                print('[Downloader][ALLIANZ] Sign in...')
                if not self._login():
                    print('[Downloader][ALLIANZ] Failed due to signing in... : ALLIANZ Server Error')
                    logger.info('[Downloader][ALLIANZ] Failed due to signing in... : ALLIANZ Server Error')
                    return
            self.get_car_data()
            logger.info('[Downloader][ALLIANZ] Finish downloading')
            print('[Downloader][ALLIANZ] Finish downloading')
        except Exception as e:
            logger.error('[Downloader][ALLIANZ] Downloading failed due to ', e)
            print('[Downloader][ALLIANZ] Downloading failed due to ', e)
            return
        # self.page.wait_for_timeout(2000000)
        self.context.close()
        self.browser.close()        
            
def main():
    extractor = AllianzExtractor('../extracted', '../codes/allianz.codes')
    extractor.get_data()

if __name__ == "__main__":
    main()
