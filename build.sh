#!/bin/bash

# Update the package list and upgrade all packages
apt-get update && apt-get upgrade -y

# Install apt-utils first
apt-get install -y apt-utils

# Install other system dependencies
apt-get install -y --no-install-recommends \
    ca-certificates \
    autoconf \
    gcc \
    g++ \
    imagemagick \
    libtool \
    make \
    libxslt-dev \
    python3-dev \
    wget \
    unzip \
    tzdata \
    libxss1 \
    libappindicator3-1 \
    fonts-liberation \
    libasound2 \
    libnss3 \
    libgtk-3-0 \
    xdg-utils \
    libdrm2 \
    libgbm1 \
    libu2f-udev \
    libvulkan1

# Set the timezone
export TZ=Europe/Warsaw
ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

# Install Google Chrome
wget http://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.198-1_amd64.deb
dpkg -i google-chrome-stable_114.0.5735.198-1_amd64.deb; apt-get -fy install

# Set up the application directory
#mkdir -p /web_apps/app_download/
cd /web_apps/app_download/

# Install Python dependencies
# You should replace this path with the actual path of your requirements.txt
pip3 install -r /web_apps/app_download/requirements.txt

# Clean up
#apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
