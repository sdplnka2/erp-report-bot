# main.py
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

# Config (from env)
USERNAME = os.getenv("sabari_2194")
PASSWORD = os.getenv("a12345678")
LOGIN_URL = "https://cloud01-in.ivydms.com/web/DMS/Welcome#"

TELEGRAM_TOKEN = os.getenv("8297798805:AAEpwNeSXy7mHdgzmMj3tRG77svHKvw5PNU")
TELEGRAM_CHAT_ID = os.getenv("-4778243714")  # e.g. -100xxxxxxxxxx

# Render linux paths
CHROME_BINARY = os.getenv("CHROME_BINARY", "/usr/bin/chromium-browser")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
DOWNLOAD_DIR = "/tmp"

# Flask app
app = Flask(__name__)

def send_file_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        r = requests.post(url, data=data, files=files, timeout=120)
    return r.status_code, r.text

def switch_to_iframe_with_element(driver, element_id, wait):
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for idx in range(len(iframes)):
        driver.switch_to.default_content()
        driver.switch_to.frame(idx)
        time.sleep(0.5)
        if element_id in driver.page_source:
            return True
    # nested
    for idx in range(len(iframes)):
        driver.switch_to.default_content()
        driver.switch_to.frame(idx)
        nested = driver.find_elements(By.TAG_NAME, "iframe")
        for n in range(len(nested)):
            driver.switch_to.default_content()
            driver.switch_to.frame(idx)
            driver.switch_to.frame(n)
            time.sleep(0.5)
            if element_id in driver.page_source:
                return True
    driver.switch_to.default_content()
    return False

def run_job():
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # make downloads go to /tmp
    prefs = {"download.default_directory": DOWNLOAD_DIR,
             "download.prompt_for_download": False,
             "download.directory_upgrade": True,
             "safebrowsing.enabled": True}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)
    wait = WebDriverWait(driver, 40)

    try:
        driver.get(LOGIN_URL)
        # LOGIN
        wait.until(EC.presence_of_element_located((By.ID, "UserName"))).send_keys(USERNAME)
        driver.find_element(By.ID, "Password").send_keys(PASSWORD)
        wait.until(EC.element_to_be_clickable((By.ID, "Login"))).click()
        time.sleep(5)

        # SEARCH and open report
        search = wait.until(EC.element_to_be_clickable((By.ID, "MenuSearchBox")))
        search.clear()
        search.send_keys("sbd")
        time.sleep(2)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ul#ui-id-1 li.ui-menu-item"))).click()
        time.sleep(4)

        # find iframe with PeriodFromMonth
        if not switch_to_iframe_with_element(driver, "PeriodFromMonth", wait):
            driver.quit()
            return {"status":"error", "msg":"period select not found in any iframe"}

        # inside iframe: select month/year using materialize inputs
        now = datetime.datetime.now()
        month_name = now.strftime("%B")
        year_name = str(now.year)

        # month
        month_dd = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.select-dropdown")))
        month_dd.click()
        wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[text()='{month_name}']/parent::li"))).click()
        time.sleep(0.5)

        # year
        dropdowns = driver.find_elements(By.CSS_SELECTOR, "input.select-dropdown")
        if len(dropdowns) < 2:
            # fallback: try select tags (rare)
            try:
                sel_month = driver.find_element(By.ID, "PeriodFromMonth")
                sel_year = driver.find_element(By.ID, "PeriodFromYear")
                # JS set value or skip; but we prefer Materialize path
            except:
                pass
        else:
            dropdowns[1].click()
            wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[text()='{year_name}']/parent::li"))).click()

        time.sleep(0.5)
        # Click Report (robust)
        report_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Report')]")))
        driver.execute_script("arguments[0].scrollIntoView(true);", report_btn)
        time.sleep(0.2)
        try:
            report_btn.click()
        except:
            driver.execute_script("arguments[0].click();", report_btn)

        # wait for generation (adjust if needed)
        time.sleep(20)

        # click download
        download_icon = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "i.fa.fa-download")))
        driver.execute_script("arguments[0].scrollIntoView(true);", download_icon)
        time.sleep(0.3)
        try:
            download_icon.click()
        except:
            driver.execute_script("arguments[0].click();", download_icon)

        # wait file appear in /tmp
        time.sleep(6)

        # find latest .xlsx/.csv/.pdf depending on your ERP output
        files = os.listdir(DOWNLOAD_DIR)
        cand = None
        for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)), reverse=True):
            if f.lower().endswith(('.xlsx','.xls','.csv','.pdf')):
                cand = f
                break
        if not cand:
            driver.quit()
            return {"status":"error", "msg":"download file not found", "files":files}

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_name = f"report_{timestamp}{os.path.splitext(cand)[1]}"
        final_path = os.path.join(DOWNLOAD_DIR, final_name)
        shutil.move(os.path.join(DOWNLOAD_DIR, cand), final_path)

        # send to telegram
        code, text = send_file_to_telegram(final_path)
        driver.quit()
        return {"status":"ok", "file":final_name, "telegram_status": code, "telegram_resp": text}

    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return {"status":"error", "exception": str(e)}

# route to trigger job
@app.route("/run", methods=["GET"])
def run_handler():
    # optional simple auth token to avoid anyone triggering
    token = request.args.get("token")
    expected = os.getenv("RUN_TOKEN")
    if expected and token != expected:
        return jsonify({"status":"error","msg":"invalid token"}), 403

    result = run_job()
    return jsonify(result)

# simple health
@app.route("/", methods=["GET"])
def health():
    return "OK"

if __name__ == "__main__":
    # for local testing
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
