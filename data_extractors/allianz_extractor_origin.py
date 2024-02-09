import os
import shutil
import json
import requests
import smtplib
from email import message_from_string
from email.mime.text import MIMEText
from email.header import Header
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.wait import WebDriverWait
from configparser import ConfigParser
from datetime import datetime, timedelta
from sentry_sdk import capture_exception
from selenium.webdriver.common.by import By
from pathlib import Path
from time import sleep
from email.header import decode_header
from bs4 import BeautifulSoup

from sentry_sdk import capture_exception
import logging

# from data_logger.data_logger import DataLogger
# logger = DataLogger.get_logger(__name__)
logger = logging.getLogger(__name__)
# 2022-11-28
PROXIES = {
    'https': 'https://lum-customer-hl_9827956f-zone-data_center-country-ch:rvd5pz7fhjr4@zproxy.lum-superproxy.io:22225',
}
#

ALLIANZ_MAIN = 'https://www.allianz.ch/gwapps/startapp/rwzwelcome.nsf/Welcome.xsp'
LOGIN_URL = 'https://www.allianz.ch/mednew-dmz/login'

TARGET_DIR = 'allianz'


class AllianzExtractor():
    def __init__(self, dir_path, codes_file):
        self.codes = ConfigParser()
        self.codes.read(codes_file)

        self.session = requests.Session()
        self.session.proxies.update(PROXIES)
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

        self._login()
        cars_data = self.get_all_cars()

        for car_data in cars_data:
            try:
                self.get_car(car_data)
            except Exception as e:
                capture_exception(e)

    def get_all_cars(self):
        ''' Returns list of all url cars '''

        downloaded = False
        while not downloaded:
            response = self.session.get('https://www.allianz.ch/gwapps/rwz/restwertzentrale.nsf/ServiceAllCars.xsp/jsoncars')
            if response.status_code == 200:
                downloaded = True
                continue
        
        cars = json.loads(response.text)
        cars_data = list()

        for car in cars:
            car_url = 'https://www.allianz.ch/gwapps/rwz/restwertzentrale.nsf/ServiceCarOffer.xsp/jsoncaroffer?KeyCar={}'.format(car['KeyCar'])

            data = {
                    'url': car_url,
                    'universal_id': car['UniversalID'],
                    'main_image': car['Image'],
            }

            cars_data.append(data)

        return cars_data

    def get_car(self, car_data):
        car_url = car_data['url']
        universal_id = car_data['universal_id']
        main_image = car_data['main_image']

        downloaded = False
        while not downloaded:
            response = self.session.get(car_url)
            if response.status_code == 200:
                downloaded = True
                continue
        car = json.loads(response.text)[0]

        ret_car = dict()
        ret_car['title'] = car.pop('Automarke', None)
        ret_car['start_date'] = car.pop('PublicDate', "").replace('T', ' ').replace('Z', '')
        ret_car['end_date'] = car.pop('EndPublicDate', "").replace('T', ' ').replace('Z', '')
        ret_car['end_date'] = ret_car['end_date'][0:len(ret_car['end_date'])-len('22:00:00')] + '22:00:00'
        if ret_car['end_date'].strip() == '22:00:00':
            ret_car['end_date'] = datetime.strftime(now, "%Y-%m-%d") + ' 22:00:00'
        ret_car['end_date'] = self._get_upcoming_sunday_if_needed(ret_car['end_date'])
        ret_car['images_count'] = -1
        ret_car['provider_name'] = 'allianz'
        ret_car['provider_id'] = car.pop('KeyCar', None)
        ret_car['brand_name'] = car.pop('CarType', None)
        ret_car['production_date'] = car.pop('Inv', "")[:10]
        try:
            ret_car['run'] = int(car.pop('KM', None))
        except:
            ret_car['run'] = 0
        ret_car['data'] = car

        car_json_path = os.path.join(
            self.data_path, '{}.json'.format(
                ret_car['provider_id']
            )
        )

        # ommit when exist
        if os.path.isfile(car_json_path):
            logger.info('[Downloader][ALLIANZ][%s] The auction was already downloaded' % ret_car['provider_id'])
            return

        ret_car['images'] = list()

        for img_name in car['AttachmentNames']:
            downloaded = False
            while not downloaded:
                img_url = 'https://www.allianz.ch/gwapps/rwz/restwertzentrale.nsf/app/{}/$FILE/{}'.format(universal_id, img_name)

                img_data = self.session.get(img_url, stream=True)
                if img_data.status_code != 200:
                    continue
                img_data.raw.decode_content = True

                if img_name == main_image:
                    img_name = 'fzbild-00.jpg'

                img_filename = '{}_{}'.format(universal_id, img_name)
                img_path = os.path.join(self.data_path, img_filename)

                ret_car['images'].append(img_filename)

                with open(img_path, 'wb') as f:
                   shutil.copyfileobj(img_data.raw, f)

                downloaded = True

        logger.info('[Downloader][ALLIANZ][%s] New auction downloaded' % ret_car['provider_id'])
        with open(car_json_path, 'w') as f:
            json.dump(ret_car, f)
    
    def _get_upcoming_sunday_if_needed(self, given_date):
        sunday_indx = 6
        parsed_date = datetime.strptime(given_date, "%Y-%m-%d %H:%M:%S")
        weekday = parsed_date.weekday()
        if weekday < 4:
            return given_date
        diff_num_of_days = sunday_indx - weekday
        ret_date = parsed_date + timedelta(days=diff_num_of_days)
        ret_date = datetime.strftime(ret_date, "%Y-%m-%d") + ' 22:00:00'
        
        return ret_date

    def _login(self):
        response = self.session.get(ALLIANZ_MAIN)
        response = self.session.get('https://www.allianz.ch/gwapps/rwz/restwertzentrale.nsf/redirect.xsp?lang=de')
        response = self.session.get(LOGIN_URL)
        login_soup = BeautifulSoup(response.text, 'html.parser')

        token = login_soup.find('form', id='mainform').find('input')['value']

        login = self.codes.get('account', 'login')
        password = self.codes.get('account', 'pass')

        data = {
            'USERNAME': login,
            'PASSWORD': password,
            'FORM_TOKEN': token,
            'TOKEN': 'Weiter',
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
            'Referer': 'https://www.allianz.ch/mednew-dmz/login',
            'Upgrade-Insecure-Requests': '1',
        }

        response = self.session.post(LOGIN_URL, data=data, headers=headers)


if __name__ == '__main__':
    ext = AllianzExtractor('../extracted', '../codes/allianz.codes')
    ext.get_data()
