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
import zipfile
import imaplib
import email
import re
from email.header import decode_header
from bs4 import BeautifulSoup
from PIL import Image, ImageChops

proxy_host = "zproxy.lum-superproxy.io"
proxy_port = 22225
proxy_username = "lum-customer-hl_9827956f-zone-data_center-country-ch"
proxy_password = "xr3grz5w0cr8"

URL_MAIN = "https://carauction.axa.ch/"
LOGIN_URL = "https://carauction.axa.ch/auction.html"
TARGET_DIR = "axa"
FINAL_LOGS = {
    "all_count": 0,
    "downloaded_count": 0,
    "success": False,
    "error": "",
    "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
}

from PIL import Image, ImageChops


def trim(im: Image) -> Image:
    """
    Trim the black borders from an image.

    Parameters:
    - im: a PIL Image object.

    Returns:
    - A new PIL Image object with the borders removed.
    """
    im = im.convert("RGB")
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return im
def crop_black_borders(image_path: str) -> Image:
    """
    Remove black borders from the left and right sides of the image.
    
    Parameters:
    - image_path: a string representing the path to the image.
    
    Returns:
    - The cropped image as a PIL Image object.
    """
    # Load the image from the provided path
    img = Image.open(image_path)

    # Trim the black borders from the image
    trimmed_img = trim(img)

    return trimmed_img

def save_final_logs():
    with open("/web_apps/app_download/axa.status", "w") as f:
        json.dump(FINAL_LOGS, f)


manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version": "22.0.0"
}
"""

background_js = """
var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
        },
        bypassList: ["localhost"]
    }
};

chrome.proxy.settings.set({ value: config, scope: "regular" }, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    { urls: ["<all_urls>"] },
    ["blocking"]
);
""" % (
    proxy_host,
    proxy_port,
    proxy_username,
    proxy_password,
)


manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version": "22.0.0"
}
"""

background_js = """
var config = {
    mode: "fixed_servers",
    rules: {
        singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
        },
        bypassList: ["localhost"]
    }
};

chrome.proxy.settings.set({ value: config, scope: "regular" }, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    { urls: ["<all_urls>"] },
    ["blocking"]
);
""" % (
    proxy_host,
    proxy_port,
    proxy_username,
    proxy_password,
)


def get_chromedriver(use_proxy=False, user_agent=None, chrome_options=None):
    path = os.path.dirname(os.path.abspath(__file__))
    chrome_options = chrome_options or ChromeOptions()
    if use_proxy:
        pluginfile = "proxy_auth_plugin.zip"

        with zipfile.ZipFile(pluginfile, "w") as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        chrome_options.add_extension(pluginfile)
    if user_agent:
        chrome_options.add_argument("--user-agent=%s" % user_agent)
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def save_final_logs():
    with open(os.path.join(dir_path, "axa.status"), "w") as f:
        json.dump(FINAL_LOGS, f)


class AxaExtractor:
    chrome_driver_path = ChromeDriverManager().install()

    def __init__(self, dir_path, codes_file):
        self.codes = ConfigParser()
        self.codes.read(codes_file)

        data_path = os.path.join(dir_path, TARGET_DIR)

        try:
            os.mkdir(data_path)
        except FileExistsError:
            pass

        self.data_path = data_path

        # Configure Chrome WebDriver with proxy

        userdatadir = os.path.join(dir_path, "profile")
        try:
            if not os.path.exists(userdatadir):
                os.makedirs(userdatadir, exist_ok=True)
        except PermissionError:
            print(f"Permission denied when trying to create directory: {userdatadir}")
        except OSError as error:
            print(f"Error occurred when trying to create directory: {error}")
        chrome_options = ChromeOptions()
        #chrome_options.add_argument('--profile-directory=Default')
        #chrome_options.add_argument(f"--user-data-dir={userdatadir}")
        chrome_options.add_argument(f"--headless=new")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(
            "--proxy-server=https://%s:%s@%s:%s"
            % (proxy_username, proxy_password, proxy_host, proxy_port)
        )
        # chrome_options.add_argument('--incognito')
        chrome_options.add_argument("--start-maximized")
        # chrome_options.add_argument('--disable-popup-blocking')
        self.driver = get_chromedriver(use_proxy=True, chrome_options=chrome_options)

    def get_data(self):
        """
        Returns json list of objects
        """

        try:
            self._login()
            sleep(5)
        except Exception as e:
            print(e)
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
                FINAL_LOGS["all_count"] += 1
                self.get_car(car_url, i)
                FINAL_LOGS["downloaded_count"] += 1
                # self.get_car(cars[0], 0)
            except Exception as e:
                capture_exception(e)
                FINAL_LOGS["error"] += "Exception axa at: {}".format(cars[0])
                raise e
            i = i + 1

        FINAL_LOGS["success"] = True
        save_final_logs()

    def get_all_cars(self):
        """Returns list of all url cars"""
        car_urls = list()
        url_page = "https://carauction.axa.ch/auction/list/EN"
        self.driver.get(url_page)
        sleep(1)
        response = self.driver.page_source
        soup = BeautifulSoup(response, "html.parser")
        json_string = soup.get_text()

        self.json_list = json.loads(json_string).get("list")

        car_links = ["https://carauction.axa.ch/" + el["au"] for el in self.json_list]
        for car_link in car_links:
            car_urls.append(car_link)
        return car_urls

    def get_car(self, car_url, index):
        """Returns json for car"""
        self.driver.get(car_url)
        html_string = self.driver.page_source
        car = dict()
        car = self.set_car_data(car, html_string, index)
        car_json_path = os.path.join(
            self.data_path, "{}.json".format(car["provider_id"])
        )
        if "/moto/" in car_url:
            car["data"]["moto"] = True
        else:
            car["data"]["moto"] = False

        with open("/web_apps/app_download/xtra.txt", "a") as f:
            print(car["end_date"], file=f)

        if os.path.isfile(car_json_path):
            with open(car_json_path, "r") as f:
                prev_car_data = json.load(f)

            if prev_car_data["end_date"] != car["end_date"]:
                prev_car_data["end_date"] = car["end_date"]
                with open(car_json_path, "w") as f:
                    json.dump(prev_car_data, f)
                # logger.info('[Downloader][AXA][%s] Updated auction end date' % car['provider_id'])

            # logger.info('[Downloader][AXA][%s] The auction was already downloaded - cancelling...' % car['provider_id'])
            return

        self.set_car_images(car, html_string, index)
        # logger.info('[Downloader][AXA][%s] New auction downloaded' % car['provider_id'])

        with open(car_json_path, "w") as f:
            json.dump(car, f)

        return car

    def set_car_data(self, car, html_string, index):
        """Assigns basic car data"""
        soup_car = BeautifulSoup(html_string, "html.parser")
        car_table = soup_car.find(
            "table", {"class", "table table-striped articledetail"}
        )
        keys_values = car_table.find_all("tr")
        keys = []
        values = []
        for el in keys_values:
            key = el.find_all("td")[0].text.replace("\n", "").replace("\t", "").strip()
            value = (
                el.find_all("td")[1].text.replace("\n", "").replace("\t", "").strip()
            )
            if key == "Mileage":
                continue
            keys.append(key)
            values.append(value)

        for i in range(0, len(keys)):
            car[keys[i]] = values[i]
        car["to_end"] = 0
        try:
            car["to_end"] = int(
                soup_car.find("h3", {"class": "countdown time-container"}).get(
                "data-seconds"
                )
            )
        except:
            pass
        car["auction_nr"] = str(self.json_list[index]["a"])

        ret_car = dict()
        ret_car["title"] = str(self.json_list[index]["at"]).strip()
        end_date = datetime.now() + timedelta(0, car.pop("to_end", None))
        ret_car["end_date"] = end_date.strftime("%Y-%m-%d %H:%M:%S")
        ret_car["start_date"] = None
        ret_car["images_count"] = -1
        ret_car["provider_name"] = "axa"
        ret_car["provider_id"] = car.pop("auction_nr", None)
        ret_car["brand_name"] = ret_car["title"].split(" ")[0]
        ret_car["production_date"] = datetime.strptime(
            car.pop("1. Inv.", None), "%m/%Y"
        ).strftime("%Y-%m-%d")
        try:
            ret_car["run"] = self.json_list[index]["km"]
        except:
            ret_car["run"] = 0

        car["Special equipment"] = (
            soup_car.find("div", {"id": "special"}).text.strip().split(",")
        )
        car["Serial equipment"] = soup_car.find("div", {"id": "serien"}).text.strip()
        car["Damages"] = soup_car.find("div", {"id": "damage"}).text.strip().split(",")
        try:
            car["Previous Damages"] = soup_car.find(
                "div", {"id": "preDamagesPart"}
            ).text.strip()
        except:
            pass

        try:
            car["More Information"] = soup_car.find(
                "div", {"id": "addinfo"}
            ).text.strip()
        except:
            pass
        car["Usable parts"] = (
            soup_car.find("div", {"id": "usablePart"}).text.strip().split(",")
        )
        car["Condition"] = (
            soup_car.find("div", {"id": "state"}).text.replace("\n", " ").strip()
        )
        description = soup_car.find("div", {"id": "description"}).find_all("tr")
        for el in description:
            key = el.find_all("td")[0].text.replace("\n", "").replace("\t", "").strip()
            value = (
                el.find_all("td")[1].text.replace("\n", "").replace("\t", "").strip()
            )
            car[key] = value

        ret_car["data"] = car

        return ret_car

    def set_car_images(self, car, html_string, index):
        """Downloads images for a car"""
        soup_car = BeautifulSoup(html_string, "html.parser")
        # find image url here
        img_urls = [
            "https://carauction.axa.ch" + el.get("src")
            for el in soup_car.find("div", {"id": "slider"}).find_all("img")
        ]

        car["images"] = list()
        i = 0
        for img_url in img_urls:
            self.driver.set_window_size(4000,3000)
            print(f"image {img_url}")
            try:
                img_http_url = img_url
                img_url = str(self.json_list[index]["a"]) + "_" + str(i)
                img_path = os.path.join(self.data_path, "{}.jpg".format(img_url))
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.driver.get(img_http_url)

                # Get the image dimensions
                image_element = self.driver.find_element(By.TAG_NAME, "img")
                image_width = int(image_element.get_attribute("width"))
                image_height = int(image_element.get_attribute("height"))
                if image_width < 100 or image_height < 100:
                    self.driver.save_screenshot(img_path)
                    cropped_img = crop_black_borders(img_path)
                    cropped_img.save(img_path)

                    self.driver.close()

                    # Switch back to the original tab
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    continue
                # Resize the window to match the image dimensions
                self.driver.set_window_size(image_width, image_height)

                # Save the image
                self.driver.save_screenshot(img_path)
                cropped_img = crop_black_borders(img_path)
                cropped_img.save(img_path)
                self.driver.close()

                # Switch back to the original tab
                self.driver.switch_to.window(self.driver.window_handles[0])

                car["images"].append(img_url + ".jpg")
                i = i + 1
            except Exception as e:
                print(e)
        self.driver.maximize_window()
    def _login(self):
        print("login process")
        self.driver.set_window_size(4000,3000)
        self.driver.get(LOGIN_URL)
        sleep(1)
        elem = self.driver.find_element(
            By.CSS_SELECTOR,
            "#navbar > div.navbar-header > div > div.pull-right > div.dropdown.pull-left.visible-md.visible-lg > a",
        )
        elem.click()
        sleep(1)
        # Perform login actions here
        # Assume the username field has the name attribute "username"
        username_field = self.driver.find_element(
            By.CSS_SELECTOR, "#loginForm\\:username"
        )
        username_field.send_keys(
            self.codes.get("account", "login")
        )  # Replace <username> with actual username

        # Assume the password field has the name attribute "password"
        password_field = self.driver.find_element(
            By.CSS_SELECTOR, "#loginForm\\:password"
        )
        password_field.send_keys(
            self.codes.get("account", "pass")
        )  # Replace <password> with actual password
        password_field.send_keys(Keys.RETURN)
        # Assume the login button has the type attribute "submit"
        # submit_button = self.driver.find_element(By.XPATH,"//button[@type='submit']")
        # submit_button.click()

        # Wait for the verification code email
        try:
            sleep(3)
            code_field = self.driver.find_element(By.CSS_SELECTOR, "#mfaForm\\:mfaCode")
            print("login success,verifying")
            verification_code = self._get_verification_code()

            # Enter the verification code in the appropriate field
            print(f"verfication code {verification_code}")
            code_field.send_keys(verification_code)
            code_field.send_keys(Keys.RETURN)
            sleep(5)

        except Exception as e:
            pass
        print("verify success")

    def _get_verification_code(self):
        # Connect to the email server
        mail = imaplib.IMAP4_SSL(
            self.codes.get("email", "imap")
        )  # specify your IMAP server here
        mail.login(self.codes.get("email", "username"), self.codes.get("email", "pass"))
        mail.select("inbox")

        result, data = mail.uid("search", None, "ALL")  # search and return UIDs
        latest_email_uid = data[0].split()[-1]

        while True:
            # sleep for a minute before checking for new email
            sleep(5)
            result, data = mail.uid("search", None, "ALL")  # search and return UIDs

            # check if there is a new email
            if latest_email_uid != data[0].split()[-1]:
                latest_email_uid = data[0].split()[-1]
                result, email_data = mail.uid("fetch", latest_email_uid, "(BODY[])")
                raw_email = email_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                # get the email subject
                subject = decode_header(email_message["Subject"])[0][0]
                if isinstance(subject, bytes):
                    # if it's a bytes type, decode to str
                    subject = subject.decode()
                print("Subject:", subject)

                # get the email sender
                from_ = decode_header(email_message["From"])[0][0]
                if isinstance(from_, bytes):
                    # if it's a bytes type, decode to str
                    from_ = from_.decode()
                print("From:", from_)

                # get the email body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        # check if the email part is text/plain
                        if part.get_content_type() == "text/plain":
                            body = self.get_body(part)
                        # check if the email part is text/html
                        elif part.get_content_type() == "text/html":
                            body = self.get_body(part)
                else:
                    body = self.get_body(email_message)

                charset = email_message.get_content_charset()  # get the character set
                if charset is None:
                    charset = "utf-8"  # if charset is not provided, default to utf-8

                if isinstance(body, bytes):
                    body = body.decode(
                        charset, errors="replace"
                    )  # decode using the given charset

                # print('Body:', body)
                break
        # Get the verification code from the email content
        verification_code = self._extract_verification_code(body)

        # Delete the email (optional)

        return verification_code

    def get_body(self, part):
        if part.is_multipart():
            return self.get_body(part.get_payload(0))
        else:
            return part.get_payload(decode=True)

    def _extract_verification_code(self, email_message):
        # Find the MFA code pattern using regular expression
        pattern = r"Ihr MFA-Code lautet: (\d+)"
        match = re.search(pattern, email_message)

        if match:
            auth_code = match.group(1)  # Extract the authentication code
            return auth_code


dir_path = os.path.dirname(os.path.realpath(__file__))


def main():
    codes_file = os.path.join(dir_path, "codes.ini")
    extractor = AxaExtractor(dir_path, codes_file)
    extractor.get_data()


if __name__ == "__main__":
    main()
