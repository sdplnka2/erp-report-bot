FROM python:3.10-slim

# Install tools
RUN apt-get update && apt-get install -y wget unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ============================
# INSTALL PORTABLE CHROMIUM
# ============================
RUN wget -q https://github.com/macchrome/winchrome/releases/download/v121.0.6167.184/chrome-linux.zip -O /tmp/chrome.zip && \
    unzip /tmp/chrome.zip -d /tmp/chrome && \
    mv /tmp/chrome/chrome-linux /opt/chromium && \
    rm -rf /tmp/chrome /tmp/chrome.zip

# ============================
# INSTALL MATCHING CHROMEDRIVER
# ============================
RUN wget -q https://chromedriver.storage.googleapis.com/121.0.6167.184/chromedriver_linux64.zip -O /tmp/driver.zip && \
    unzip /tmp/driver.zip -d /tmp/driver && \
    mv /tmp/driver/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf /tmp/driver /tmp/driver.zip

ENV CHROME_BINARY=/opt/chromium/chrome
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

EXPOSE 10000

CMD ["bash", "start.sh"]
