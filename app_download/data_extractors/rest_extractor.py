import sys
import os
import re
import shutil
import json
import traceback
from datetime import datetime
import requests
import hashlib
from bs4 import BeautifulSoup
from configparser import ConfigParser
from sentry_sdk import capture_exception
from data_logger.data_logger import DataLogger
logger = DataLogger.get_logger(__name__)


LOGIN_URL = 'https://www.restwertboerse.ch/index.php'
REST_MAIN = 'https://www.restwertboerse.ch{}'
OFFERS_URL = 'https://www.restwertboerse.ch/offers.php?page={}'
TARGET_DIR = 'rest'
FINAL_LOGS = {
    "all_count": 0,
    "downloaded_count": 0,
    "success": False,
    "error": "",
    "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
}
CAR_LOGS = {
    "error": "",
    "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
}


def save_final_logs():
    with open("/web_apps/app_download/rest.status", "w") as f:
        json.dump(FINAL_LOGS, f)

def save_car_logs():
    with open("/web_apps/app_download/rest_car.status", "w") as f:
        json.dump(CAR_LOGS, f)


class RestExtractor():
    def __init__(self, dir_path, codes_file):
        self.codes = ConfigParser()
        self.codes.read(codes_file)
        self.session = requests.Session()
        data_path = os.path.join(dir_path, TARGET_DIR)
        try:
            os.mkdir(data_path)
        except FileExistsError:
            pass

        self.data_path = data_path

    def get_data(self):
        '''
        Returns json list of objects
        '''
        logger.info('[Downloader][REST] Start downloading...')
        print('[Downloader][REST] Start downloading...')
        try:
            logger.info('[Downloader][REST] Sign in...')
            print('[Downloader][REST] Sign in...')
            self._login()
            self.get_all_cars()

            self._login_vaudoise()
            self.get_all_cars(subproviders=['Vaudoise Assurances'])
            
            logger.info('[Downloader][REST] Finish downloading...')
            print('[Downloader][REST] Finish downloading...')
            FINAL_LOGS["success"] = True
            save_final_logs()
        except Exception as e:
            capture_exception(e)
            FINAL_LOGS["success"] = False
            save_final_logs()
            raise e

    def get_request(self, url):
        response = self.session.get(url)
        if response.status_code == 305:
            proxy_url = response.headers['Location']
            original_proxies = self.session.proxies.copy()
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}
            redirected_response = self.session.get(url)
            self.session.proxies = original_proxies
            return redirected_response
        elif response.status_code == 303:
           redirected_url = response.headers['Location']
           redirected_response = requests.get(redirected_url)
           return redirected_response
        else:
            return response
        
    def get_all_cars(self, subproviders=None):
        ''' Returns list of all url cars '''

        page = 1

        while True:
            response = self.get_request(OFFERS_URL.format(page))
            soup_cars = BeautifulSoup(response.text, 'html.parser')
            car_entries = soup_cars.find('tbody').find_all('tr')
            if len(car_entries) == 0:
                break

            for car_entry in car_entries:
                current_subprovider = car_entry.find_all('td')[4].string
                if subproviders and current_subprovider not in subproviders:
                    continue

                FINAL_LOGS['all_count'] += 1
                car_link = car_entry.find('a')['href']

                try:
                    car = self.get_car(car_link, subprovider=current_subprovider)
                    FINAL_LOGS['downloaded_count'] += 1
                except Exception as e:
                    capture_exception(e)
                    continue

                if car is None:
                    continue

                car_json_path = os.path.join(
                    self.data_path, '{}.json'.format(
                        car['provider_id']
                    )
                )

                with open(car_json_path, 'w') as f:
                    json.dump(car, f)

            page += 1

    def get_car(self, car_url, subprovider=None):
        ''' Returns json for car '''

        if 'offer-files' in car_url:
            provider_id = car_url.split('?id=')[1]
            car_url = '/offer-detail?id=%s&m=all&page=' % provider_id

        car = dict()

        response = self.get_request(REST_MAIN.format(car_url))
        soup_car = BeautifulSoup(response.text, 'html.parser')

        title = soup_car.h1.text.strip().split('\t')
        title = list(filter(None, title))

        if len(title) < 2:
            car['auction_nr'] = title[0][3:]
        else:
            car['auction_nr'] = title[1][3:]

        auction_end = soup_car.find_all('div', 'box-body')[2].find_all('p')[1]
        car['auction_end'] = auction_end.string.strip()

        fahr_tbody = soup_car.find('table', 'margin-bottom-20').find('tbody')

        for tr_entry in fahr_tbody.find_all('tr'):
            tds = tr_entry.find_all('td')

            if len(tds) == 2:
                car[tds[0].string.strip()] = tds[1].string.strip() if tds[1].string else None
            elif len(tds) == 1:
                car['Information'] = str(tds[0])
                car['Information'] = car['Information'][len('<td colspan="2">'):-len('</td>')]

        werte_tbody = soup_car.find_all('table', 'margin-bottom-20')[1].find('tbody')
        for tr_entry in werte_tbody.find_all('tr'):
            tds = tr_entry.find_all('td')
            car[tds[0].string.strip()] = tds[1].string.strip() if tds[1].string else None

        car['Ausstattung'] = list()
        ausstattungs = soup_car.find_all('div', 'box-body')[1].find_all('i', 'green')
        for austattung in ausstattungs:
            name = austattung.nextSibling
            car['Ausstattung'].append(name)
        
        schadenb = soup_car.find('div', 'margin-top-20')
        if schadenb: 
            schadenb = str(schadenb)
            schadenb = schadenb.replace('/assets/images/graphics/car-side.png', '/static/website/img/car-side.png')
            schadenb = schadenb.replace('/assets/images/graphics/car-top.png', '/static/website/img/car-top.png')
            car['Schadenbeschrieb'] = schadenb

        ret_car = dict()
        ret_car['provider_id'] = car.pop('auction_nr', None)
        ret_car['end_date'] = datetime.strptime(car.pop('auction_end'), "%d.%m.%Y, %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

        car_json_path = os.path.join(
            self.data_path, '{}.json'.format(
                ret_car['provider_id']
            )
        )
        
        if os.path.isfile(car_json_path):
            with open(car_json_path, 'r') as f:
                prev_car_data = json.load(f)
            if prev_car_data['end_date'] != ret_car['end_date']:
                prev_car_data['end_date'] = ret_car['end_date']
                with open(car_json_path, 'w') as f:
                    json.dump(prev_car_data, f)
                print('[Downloader][REST][%s] Updated auction end date' % ret_car['provider_id'])
                logger.info('[Downloader][REST][%s] Updated auction end date' % ret_car['provider_id'])

            print('[Downloader][REST][%s] The auction was already downloaded - cancelling...' % ret_car['provider_id'])
            logger.info('[Downloader][REST][%s] The auction was already downloaded - cancelling...' % ret_car['provider_id'])
            return

        self.set_car_images(car, response.text)
        print('[Downloader][REST][%s] New auction downloaded' % ret_car['provider_id'])
        logger.info('[Downloader][REST][%s] New auction downloaded' % ret_car['provider_id'])
        if car['Marke'] is None:
            car['Marke'] = 'N/A'
        if car['Typ'] is None:
            car['Typ'] = 'N/A'
        ret_car['title'] = "{} {}".format(car['Marke'], car['Typ'])
        ret_car['start_date'] = None
        ret_car['images_count'] = -1
        ret_car['provider_name'] = 'rest'
        ret_car['brand_name'] = car.pop('Marke', None)
        if car.get('1. Inv.', None) is None:
            car['1. Inv.'] =  datetime.now().strftime("%d.%m.%Y")
        try:
            ret_car['production_date'] = datetime.strptime(car.pop("1. Inv.", datetime.now().strftime("%d.%m.%Y")), "%d.%m.%Y").strftime("%Y-%m-%d")
        except:
            ret_car['production_date'] = "2000-01-01"
        ret_car['run'] = car.pop('Km', '0').replace('\'', '')
        ret_car['images'] = car.pop('images', list())
        ret_car['data'] = car
        ret_car['subprovider_name'] = subprovider

        return ret_car

    def set_car_images(self, car, html_string):
        ''' Assigns list of images '''

        car['images'] = list()

        soup_car = BeautifulSoup(html_string, 'html.parser')
        try:
            images = soup_car.find('ul', 'slides').find_all('a')
        except AttributeError as e:
            # NO IMAGES LOGGING HERE IF NEEDED
            car['images'] = list()
            return car

        for image in images:
            url = image['href']
            img_data = self.session.get(REST_MAIN.format(url), stream=True)
            img_data.raw.decode_content = True

            url = url.replace('/', '_')
            img_path = os.path.join(self.data_path, url)

            with open(img_path, 'wb') as f:
                shutil.copyfileobj(img_data.raw, f)

            car['images'].append(url)

        return car

    def _login(self):
        password = self.codes.get('account', 'pass')
        m = hashlib.sha512()
        m.update(password.encode('utf-8'))
        hashed_pass = m.hexdigest()

        data = {
            'p1': hashed_pass,
            'username': self.codes.get('account', 'login'),
            'action': 'login',
            'ref': '',
            'agb': '1',
        }

        self.session = requests.Session()
        response = self.session.post(LOGIN_URL, data=data)
        if response.status_code != 200:
            raise Exception("Login Failed")

    def _login_vaudoise(self):
        password = self.codes.get('account_vaudoise', 'pass')
        m = hashlib.sha512()
        m.update(password.encode('utf-8'))
        hashed_pass = m.hexdigest()

        data = {
            'p1': hashed_pass,
            'username': self.codes.get('account_vaudoise', 'login'),
            'action': 'login',
            'ref': '',
            'agb': '1',
        }

        self.session = requests.Session()
        response = self.session.post(LOGIN_URL, data=data)
        if response.status_code != 200:
            raise Exception("Login Failed")

if __name__ == '__main__':
    ext = RestExtractor('./extracted', './codes/rest.codes')
    ext.get_data()
