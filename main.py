import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

ERP_URL = "https://your-erp-login.com"
USERNAME = os.getenv("ERP_USER")
PASSWORD = os.getenv("ERP_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(file_path, 'rb') as f:
        requests.post(url, data={"chat_id": CHAT_ID}, files={"document": f})

def run_bot():
    # Chrome setup
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    # LOGIN
    driver.get(ERP_URL)
    time.sleep(3)

    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "loginButton").click()
    time.sleep(3)

    # REPORT PAGE
    driver.get("https://your-erp-report-url.com")
    time.sleep(3)

    # DOWNLOAD BUTTON CLICK
    driver.find_element(By.ID, "btnDownload").click()
    time.sleep(5)

    file_path = "/tmp/report.xlsx"
    send_to_telegram(file_path)

    driver.quit()

if __name__ == "__main__":
    run_bot()
