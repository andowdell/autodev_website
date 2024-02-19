import os
import re
import shutil
import json
import requests
from bs4 import BeautifulSoup
from configparser import ConfigParser
from datetime import datetime, timedelta
from sentry_sdk import capture_exception
from data_logger.data_logger import DataLogger
logger = DataLogger.get_logger(__name__)

PROXIES = {
    'https': 'https://lum-customer-hl_9827956f-zone-data_center-country-ch:xr3grz5w0cr8@zproxy.lum-superproxy.io:22225',
}
URL_MAIN = 'https://carauction.axa.ch/'
LOGIN_URL = 'https://carauction.axa.ch/auction.html'
TARGET_DIR = 'axa'
FINAL_LOGS = {
    "all_count": 0,
    "downloaded_count": 0,
    "success": False,
    "error": "",
    "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
}

def save_final_logs():
    with open("/web_apps/app_download/axa.status", "w") as f:
        json.dump(FINAL_LOGS, f)


class AxaExtractor():
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    json_list = []

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

        try:
            self._login()
        except Exception as e:
            capture_exception(e)  
            FINAL_LOGS["error"] = "Could not login."
            save_final_logs()
        try:
            cars = self.get_all_cars()
        except Exception as e:
            capture_exception(e)
            FINAL_LOGS["success"] = True
            save_final_logs()
            raise e
        
        i = 0
        for car_url in cars:
            try:
                FINAL_LOGS['all_count'] += 1
                self.get_car(car_url, i)
                FINAL_LOGS['downloaded_count'] += 1
                #self.get_car(cars[0], 0)
            except Exception as e:
                capture_exception(e)
                FINAL_LOGS['error'] += 'Exception axa at: {}'.format(cars[0])
                raise e
            i = i + 1
        
        FINAL_LOGS["success"] = True
        save_final_logs()

    def get_all_cars(self):
        ''' Returns list of all url cars '''

        car_urls = list()
        url_page = 'https://carauction.axa.ch/auction/list/EN'
        response = self.session.get(url_page, headers=self.headers, verify=False)
        self.json_list = json.loads(response.text).get('list')
        car_links = ['https://carauction.axa.ch/' + el['au'] for el in self.json_list]
        for car_link in car_links:
            car_urls.append(car_link)
        return car_urls

    def get_car(self, car_url, index):
        ''' Returns json for car '''
        response = self.session.get(car_url, headers=self.headers, verify=False)
        html_string = response.text
        car = dict()
        car = self.set_car_data(car, html_string, index)
        car_json_path = os.path.join(
            self.data_path, '{}.json'.format(
                car['provider_id']
            )
        )
        if '/moto/' in car_url:
            car['data']['moto'] = True
        else:
            car['data']['moto'] = False

        with open("/web_apps/app_download/xtra.txt", "a") as f:
             print(car['end_date'], file=f)

        if os.path.isfile(car_json_path):
            with open(car_json_path, 'r') as f:
                prev_car_data = json.load(f)

            if prev_car_data['end_date'] != car['end_date']:
                prev_car_data['end_date'] = car['end_date']
                with open(car_json_path, 'w') as f:
                    json.dump(prev_car_data, f)
                logger.info('[Downloader][AXA][%s] Updated auction end date' % car['provider_id'])

            logger.info('[Downloader][AXA][%s] The auction was already downloaded - cancelling...' % car['provider_id'])
            return

        self.set_car_images(car, html_string, index)
        logger.info('[Downloader][AXA][%s] New auction downloaded' % car['provider_id'])

        with open(car_json_path, 'w') as f:
            json.dump(car, f)

        return car

    def set_car_data(self, car, html_string, index):
        ''' Assigns basic cars data '''
        soup_car = BeautifulSoup(html_string, 'html.parser')
        car_table = soup_car.find('table', {'class', 'table table-striped articledetail'})
        keys_values = car_table.find_all('tr')
        keys = []
        values = []
        for el in keys_values:
            key = el.find_all('td')[0].text.replace('\n', '').replace('\t', '').strip()
            value = el.find_all('td')[1].text.replace('\n', '').replace('\t', '').strip()
            if key == 'Mileage':
                continue
            keys.append(key)
            values.append(value)

        for i in range(0, len(keys)):
            car[keys[i]] = values[i]

        car['to_end'] = int(soup_car.find('h3', {'class' : 'countdown time-container'}).get('data-seconds'))
        car['auction_nr'] = str(self.json_list[index]['a'])

        ret_car = dict()
        ret_car['title'] = str(self.json_list[index]['at']).strip()
        end_date = datetime.now() + timedelta(0, car.pop('to_end', None))
        ret_car['end_date'] = end_date.strftime("%Y-%m-%d %H:%M:%S")
        ret_car['start_date'] = None
        ret_car['images_count'] = -1
        ret_car['provider_name'] = 'axa'
        ret_car['provider_id'] = car.pop('auction_nr', None)
        ret_car['brand_name'] = ret_car['title'].split(" ")[0]
        ret_car['production_date'] = datetime.strptime(car.pop('1. Inv.', None), "%m/%Y").strftime("%Y-%m-%d")
        try:
            ret_car['run'] = self.json_list[index]['km']
        except:
            ret_car['run'] = 0
        
        car['Special equipment'] = soup_car.find('div', {'id' : 'special'}).text.strip().split(',')
        car['Serial equipment'] = soup_car.find('div', {'id' : 'serien'}).text.strip()
        car['Damages'] = soup_car.find('div', {'id' : 'damage'}).text.strip().split(',')
        try:
            car['Previous Damages'] = soup_car.find('div', {'id' : 'preDamagesPart'}).text.strip()
        except:
            pass
        
        try:
            car['More Information'] = soup_car.find('div', {'id' : 'addinfo'}).text.strip()
        except:
            pass
        car['Usable parts'] = soup_car.find('div', {'id' : 'usablePart'}).text.strip().split(',')
        car['Condition'] = soup_car.find('div', {'id' : 'state'}).text.replace('\n', ' ').strip()
        description = soup_car.find('div', {'id' : 'description'}).find_all('tr')
        for el in description:
            key = el.find_all('td')[0].text.replace('\n', '').replace('\t', '').strip()
            value = el.find_all('td')[1].text.replace('\n', '').replace('\t', '').strip()
            car[key] = value

        ret_car['data'] = car

        return ret_car

    def set_car_images(self, car, html_string, index):
        ''' Assigns list of images '''
    
        soup_car = BeautifulSoup(html_string, 'html.parser')
        # find image url here
        img_urls = ['https://carauction.axa.ch' + el.get('src') for el in soup_car.find('div', {'id' : 'slider'}).find_all('img')]

        car['images'] = list()
        i = 0
        for img_url in img_urls:
            img_http_url = img_url
            img_data = self.session.get(img_http_url, stream=True, verify=False)
            img_data.raw.decode_content = True

            img_url = str(self.json_list[index]['a']) + '_' + str(i)
            img_path = os.path.join(self.data_path, '{}.jpg'.format(img_url))

            with open(img_path, 'wb') as f:
                shutil.copyfileobj(img_data.raw, f)

            car['images'].append(img_url+'.jpg')
            i = i + 1

    def _login(self):
        response = self.session.get(LOGIN_URL, headers=self.headers)
        soup_doc = BeautifulSoup(response.text, 'html.parser')
        view_state_obj = soup_doc.find(attrs={"name": "javax.faces.ViewState"})
        view_state = view_state_obj['value']

        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'loginForm:loginBtn',
            'javax.faces.partialExecute': 'loginForm:loginBtn loginForm:username loginForm:password',
            'loginForm:loginBtn': 'loginForm:loginBtn',
            'loginForm': 'loginForm',
            'loginForm:username': self.codes.get('account', 'login'),
            'loginForm:password': self.codes.get('account', 'pass'),
            'javax.faces.ViewState': view_state,
        }
        response = self.session.post(LOGIN_URL, data=data, headers=self.headers)

        data = {
            'javax.faces.source': 'loginForm:j_idt121',
            'javax.faces.partial.ajax':	'true',
            'primefaces.resetvalues': 'true',
            'javax.faces.partial.execute':	"@all",
            'javax.faces.partial.render':	"mfaDialog",
            'loginForm:j_idt121':	"loginForm:j_idt121",
            'loginForm':	"loginForm",
            'loginForm:username':	self.codes.get('account', 'login'),
            'loginForm:password':	self.codes.get('account', 'pass'),
            'javax.faces.ViewState': view_state,
        }
        response = self.session.post(LOGIN_URL, data=data, headers=self.headers)

        data = {
            'javax.faces.partial.ajax':	"true",
            'javax.faces.source':	"loginForm:remoteToLogin",
            'javax.faces.partial.execute':	"@all",
            'loginForm:remoteToLogin':	"loginForm:remoteToLogin",
            'loginForm':	"loginForm",
            'loginForm:username': self.codes.get('account', 'login'),
            'loginForm:password': self.codes.get('account', 'pass'),
            'javax.faces.ViewState': view_state,
        }
        response = self.session.post(LOGIN_URL, data=data, headers=self.headers)

        if response.status_code != 200:
            capture_exception("[AXA] Could not login!")
