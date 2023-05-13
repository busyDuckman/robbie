# Use the official Python 3.11 image as the base
#FROM python:3.11
#FROM balenalib/raspberrypi4-64-debian-python:3.11-bullseye
FROM pi4_base:latest

# Expose /dev and /sys directories to the container
#VOLUME [ "/dev", "/sys" ]

# lets patch in raspberry pi stuff
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        libraspberrypi-dev \
        raspberrypi-kernel \
        raspberrypi-kernel-headers \
        gcc \
        git \
        build-essential


# -----------------------------------------------------------------------
# 1) setup sound

# Update packages and install necessary dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y pulseaudio pulseeffects openjdk-11-jre wget

#RUN apt-get update && apt-get install -y \
#    libasound2 \
#    bluez \
#    bluez-tools \
#    pulseaudio \
#    pulseaudio-module-bluetooth \
#    alsa-utils \
#    --no-install-recommends \
#    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y alsa-utils

# -----------------------------------------------------------------------
# 2) setup the display
RUN mkdir -p /robbie/third_party
WORKDIR /robbie/third_party

RUN apt-get update && \
    apt-get install -y build-essential autoconf automake libtool git wget unzip

# Download the BCM2835 libraries
RUN wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.68.tar.gz && \
    tar zxvf bcm2835-1.68.tar.gz

# Configure and build the BCM2835 libraries
WORKDIR /robbie/third_party/bcm2835-1.68
RUN ./configure && \
     make
# If this check fails, it's because at this stage we dont have access to the PI's hardware.
# RUN make check
RUN make install
WORKDIR /robbie/third_party

# Install WiringPi
# Add the package repository and GPG key
#RUN echo "deb http://archive.raspberrypi.org/debian/ buster main" > /etc/apt/sources.list.d/wiringpi.list
#RUN wget -qO - https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | apt-key add -

# Update the package list and install wiringPi
RUN #apt-get update && \
#    apt-get install -y wiringpi


#RUN wget https://project-downloads.drogon.net/wiringpi-latest.deb
#RUN dpkg -i wiringpi-latest.deb
#    gpio -v

# RUN apt-get install -y wiringpi

#ENV CFLAGS="-I/usr/local/include -L/usr/local/lib"
#RUN git clone https://github.com/WiringPi/WiringPi
#WORKDIR /robbie/third_party/WiringPi
#RUN sed -i 's/sudo //g' build  # Remove sudo from the build script

## Create dummy uninstall and install scripts
#RUN echo '#!/bin/sh' > /usr/local/bin/uninstall && \
#    chmod +x /usr/local/bin/uninstall && \
#    echo '#!/bin/sh' > /usr/local/bin/install && \
#    chmod +x /usr/local/bin/install
#
## Remove sudo from build script
## RUN sed -i 's/sudo //g' build
#RUN ./build


RUN echo "deb http://archive.raspberrypi.org/debian/ bullseye main" >> /etc/apt/sources.list.d/raspi.list && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0x82B129927FA3303E && \
    apt-get update && \
    apt-get install -y wiringpi && \
    rm /etc/apt/sources.list.d/raspi.list && \
    apt-get clean

WORKDIR /robbie/third_party


RUN apt-get update
RUN pip3 install --upgrade pip
# RUN apt-get install -y python3-pip python3-pil python3-numpy

RUN pip3 install RPi.GPIO
RUN pip3 install spidev


# download the example code so we can test as nessesary
RUN wget https://www.waveshare.com/w/upload/8/8d/LCD_Module_RPI_code.zip && \
    unzip ./LCD_Module_RPI_code.zip

# -----------------------------------------------------------------------
# 3) SETUP THE ROBBIE-9000 SYSTEM

# Set the working directory to the 'robot' directory
WORKDIR /robbie/code_robbie

# extra hoops to get libportaudio2
RUN echo "deb http://deb.debian.org/debian/ buster main" > /etc/apt/sources.list.d/debian.list
RUN apt-get update

# stuff needed for pyaudio
RUN apt-get install -y libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0

# Create a non-root user
RUN useradd -m -s /bin/bash robbie  && \
    chown -R robbie:robbie /robbie/code_robbie && \
    mkdir -p /run/user/1000 && \
    chown -R robbie:robbie /run/user/1000 && \
    mkdir -p /home/robbie/.config/pulse && \
    chown -R robbie:robbie /home/robbie/.config/pulse

# Some hoops so that gpio acess does not require sudo
#COPY container_robbie/robbie_9000/99-gpio.rules /etc/udev/rules.d/
#COPY container_robbie/robbie_9000/spi.rules /etc/udev/rules.d/
#
RUN groupadd gpio && \
    usermod -a -G gpio robbie && \
    groupadd -f spi && \
    usermod -a -G spi robbie
#
## reload (IDK whatever at this point)
RUN apt-get update && \
    apt-get install -y udev && \
    systemctl enable udev
#    udevadm control --reload-rules && \
#    udevadm trigger

#RUN groupadd -f gpio && \
#    usermod -a -G gpio robbie \

# Switch to the non-root user
USER robbie

# Set the PULSE_SERVER environment variable for the robbie user
ENV PULSE_SERVER=unix:/run/user/1000/pulse/native


# Install any necessary Python packages
RUN echo "2"
COPY code_robbie/requirements.txt /tmp
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set the Python path to include the user's local package directory
ENV PYTHONPATH="${PYTHONPATH}:~/.local/lib/python3.11/site-packages"

EXPOSE 8000
#pulseaudio --start && \

CMD python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info

