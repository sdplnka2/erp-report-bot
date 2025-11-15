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

# ============================
# CONFIGURATION (ENV VARIABLES)
# ============================

USERNAME = os.getenv("ERP_USERNAME")          # sabari_2194
PASSWORD = os.getenv("ERP_PASSWORD")          # anoop12345678
LOGIN_URL = "https://cloud01-in.ivydms.com/web/DMS/Welcome#"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RUN_TOKEN = os.getenv("RUN_TOKEN")            # for protection

# Chrome paths from Dockerfile
CHROME_BINARY = os.getenv("CHROME_BINARY", "/usr/bin/chromium")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

# Download folder
DOWNLOAD_DIR = "/tmp"

# Flask app
app = Flask(__name__)


# ============================
# SEND REPORT TO TELEGRAM
# ============================
def send_file_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": TELEGRAM_CHAT_ID}
        r = requests.post(url, data=data, files=files, timeout=120)
    return r.status_code, r.text


# ============================
# AUTO-DETECT IFRAME
# ============================
def switch_to_iframe_with_element(driver, element_id, wait):
    iframes = driver.find_elements(By.TAG_NAME, "iframe")

    # Try first-level iframes
    for idx in range(len(iframes)):
        driver.switch_to.default_content()
        driver.switch_to.frame(idx)
        time.sleep(0.5)
        if element_id in driver.page_source:
            return True

    # Try nested iframes
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


# ============================
# MAIN SELENIUM JOB
# ============================
def run_job():
    # Chrome options for Render
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BINARY
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

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

        # OPEN REPORT
        search = wait.until(EC.element_to_be_clickable((By.ID, "MenuSearchBox")))
        search.clear()
        search.send_keys("sbd")
        time.sleep(2)

        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "ul#ui-id-1 li.ui-menu-item"))).click()
        time.sleep(4)

        # Find correct iframe
        if not switch_to_iframe_with_element(driver, "PeriodFromMonth", wait):
            driver.quit()
            return {"status": "error", "msg": "Period dropdown not found"}

        # Select Month & Year
        now = datetime.datetime.now()
        month_name = now.strftime("%B")
        year_name = str(now.year)

        dropdowns = driver.find_elements(By.CSS_SELECTOR, "input.select-dropdown")
        if len(dropdowns) < 2:
            driver.quit()
            return {"status": "error", "msg": "Dropdowns not found"}

        dropdowns[0].click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//span[text()='{month_name}']/parent::li"))).click()

        dropdowns[1].click()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//span[text()='{year_name}']/parent::li"))).click()

        # Click Report
        report_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[contains(text(),'Report')]")))
        
        try:
            report_btn.click()
        except:
            driver.execute_script("arguments[0].click();", report_btn)

        time.sleep(20)

        # Download icon
        download_icon = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "i.fa.fa-download"))
        )

        try:
            download_icon.click()
        except:
            driver.execute_script("arguments[0].click();", download_icon)

        # Wait for download
        time.sleep(6)

        # Identify downloaded file
        files = os.listdir(DOWNLOAD_DIR)
        cand = None

        for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)), reverse=True):
            if f.lower().endswith(('.xlsx', '.xls', '.csv', '.pdf')):
                cand = f
                break

        if not cand:
            driver.quit()
            return {"status": "error", "msg": "Download failed", "files": files}

        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        final_name = f"report_{timestamp}{os.path.splitext(cand)[1]}"
        final_path = os.path.join(DOWNLOAD_DIR, final_name)

        shutil.move(os.path.join(DOWNLOAD_DIR, cand), final_path)

        # SEND TO TELEGRAM
        code, text = send_file_to_telegram(final_path)

        driver.quit()
        return {
            "status": "ok",
            "file": final_name,
            "telegram_status": code,
            "telegram_resp": text
        }

    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return {"status": "error", "exception": str(e)}


# ============================
# ROUTES
# ============================

@app.route("/run", methods=["GET"])
def run_handler():
    token = request.args.get("token")
    if RUN_TOKEN and token != RUN_TOKEN:
        return jsonify({"status": "error", "msg": "invalid token"}), 403

    result = run_job()
    return jsonify(result)


@app.route("/", methods=["GET"])
def health():
    return "OK"


# Local test server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
