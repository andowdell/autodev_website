#!/bin/bash

# Set environment variables
export CONFIG_DSN="http://08aea5911922414ebaf0423d9ac32b18@azs.mojedane.net:9000/5"
export CONFIG_ENVIRONMENT="PRD#"
export CONFIG_HOSTNAME="autazeszwajcarii.pl"
export CONFIG_SENTRY_SAMPLE_RATE="1.0"
export CONFIG_LOG_LEVEL="INFO"
export CONFIG_GRAYLOG_HOST="azs.mojedane.net"

# Navigate to the application directory
cd /web_apps/app_download

# Run the Python application
python3 app_axa.py
