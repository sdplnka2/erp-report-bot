import os
import time
import datetime
import shutil
from flask import Flask, jsonify, request
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

USERNAME = os.getenv("ERP_USERNAME")
PASSWORD = os.getenv("ERP_PASSWORD")
LOGIN_URL = "https://cloud01-in.ivydms.com/web/DMS/Welcome#"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RUN_TOKEN = os.getenv("RUN_TOKEN")

CHROME_BINARY = os.getenv("CHROME_BINARY", "/opt/chromium/chrome")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

DOWNLOAD_DIR = "/tmp"

app = Flask(__name__)


def send_file_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        send = {"document": f}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        r = requests.post(url, data=data, files=send)
    return r.status_code, r.text


def switch_to_iframe_with_element(driver, element_id):
    iframes = driver.find_elements(By.TAG_NAME, "iframe")

    # Level 1
    for i in range(len(iframes)):
        driver.switch_to.default_content()
        driver.switch_to.frame(i)
        time.sleep(0.4)
        if element_id in driver.page_source:
            return True

    # Level 2
    for i in range(len(iframes)):
        driver.switch_to.default_content()
        driver.switch_to.frame(i)
        nested = driver.find_elements(By.TAG_NAME, "iframe")
        for n in range(len(nested)):
            driver.switch_to.default_content()
            driver.switch_to.frame(i)
            driver.switch_to.frame(n)
            time.sleep(0.4)
            if element_id in driver.page_source:
                return True

    driver.switch_to.default_content()
    return False


def run_job():

    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY

    # ULTRA-LOW MEMORY MODE
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--single-process")
    options.add_argument("--no-zygote")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1280,720")

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)
    wait = WebDriverWait(driver, 40)

    try:
        # LOGIN
        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.ID, "UserName"))).send_keys(USERNAME)
        driver.find_element(By.ID, "Password").send_keys(PASSWORD)
        wait.until(EC.element_to_be_clickable((By.ID, "Login"))).click()
        time.sleep(5)

        # SEARCH REPORT
        search = wait.until(EC.element_to_be_clickable((By.ID, "MenuSearchBox")))
        search.clear()
        search.send_keys("sbd")
        time.sleep(2)

        wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "ul#ui-id-1 li.ui-menu-item"))
        ).click()

        time.sleep(4)

        if not switch_to_iframe_with_element(driver, "PeriodFromMonth"):
            driver.quit()
            return {"status": "error", "msg": "iframe not found"}

        now = datetime.datetime.now()
        month_name = now.strftime("%B")
        year_name = str(now.year)

        dropdowns = driver.find_elements(By.CSS_SELECTOR, "input.select-dropdown")

        dropdowns[0].click()
        wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//span[text()='{month_name}']/parent::li"))
        ).click()

        dropdowns[1].click()
        wait.until(
            EC.element_to_be_clickable((By.XPATH, f"//span[text()='{year_name}']/parent::li"))
        ).click()

        # Generate Report
        btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Report')]"))
        )
        driver.execute_script("arguments[0].click();", btn)

        time.sleep(20)

        # Download
        icon = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "i.fa.fa-download"))
        )
        driver.execute_script("arguments[0].click();", icon)

        time.sleep(8)

        # Detect file
        files = os.listdir(DOWNLOAD_DIR)
        cand = None
        for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)), reverse=True):
            if f.lower().endswith(('.xlsx', '.xls', '.csv', '.pdf')):
                cand = f
                break

        if not cand:
            driver.quit()
            return {"status": "error", "msg": "No downloaded file"}

        final_name = f"report_{now.strftime('%Y-%m-%d_%H-%M-%S')}{os.path.splitext(cand)[1]}"
        final_path = os.path.join(DOWNLOAD_DIR, final_name)

        shutil.move(os.path.join(DOWNLOAD_DIR, cand), final_path)

        code, resp = send_file_to_telegram(final_path)

        driver.quit()
        return {"status": "ok", "file": final_name, "telegram_status": code}

    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return {"status": "error", "exception": str(e)}


@app.route("/run")
def run_handler():
    token = request.args.get("token")
    if RUN_TOKEN and token != RUN_TOKEN:
        return jsonify({"status": "error", "msg": "invalid token"}), 403
    return jsonify(run_job())


@app.route("/")
def home():
    return "OK"
