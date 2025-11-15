FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome paths
ENV CHROME_BINARY=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Working directory
WORKDIR /app

# Copy project
COPY . /app

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (required for Render)
EXPOSE 10000

# Start server using gunicorn
CMD ["bash", "start.sh"]
