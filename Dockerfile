FROM python:3.10-slim

# Install minimal dependencies
RUN apt-get update && apt-get install -y wget unzip gnupg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ========================
# INSTALL PORTABLE CHROMIUM
# ========================
RUN wget -q https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1217805/chrome-linux.zip -O /tmp/chrome.zip && \
    unzip /tmp/chrome.zip -d /tmp/ && \
    mv /tmp/chrome-linux /opt/chromium && \
    rm /tmp/chrome.zip

# ========================
# INSTALL MATCHING CHROMEDRIVER
# ========================
RUN wget -q https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1217805/chromedriver_linux64.zip -O /tmp/driver.zip && \
    unzip /tmp/driver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf /tmp/driver.zip /tmp/chromedriver-linux64

# Tell Selenium where Chrome is
ENV CHROME_BINARY=/opt/chromium/chrome
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

EXPOSE 10000

CMD ["bash", "start.sh"]
