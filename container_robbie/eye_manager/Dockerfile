FROM pi4_base_gpio:latest

# -----------------------------------------------------------------------
# 2) setup the display
RUN mkdir -p /robbie/third_party
WORKDIR /robbie/third_party

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
#RUN apt-get update && \
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


#RUN echo "deb http://archive.raspberrypi.org/debian/ bullseye main" >> /etc/apt/sources.list.d/raspi.list && \
#    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0x82B129927FA3303E && \
#    apt-get update && \
#    apt-get install -y wiringpi && \
#    rm /etc/apt/sources.list.d/raspi.list && \
#    apt-get clean

WORKDIR /robbie/third_party


RUN apt-get update
# RUN pip3 install --upgrade pip
# RUN apt-get install -y python3-pip python3-pil python3-numpy

RUN pip3 install RPi.GPIO
RUN pip3 install spidev


# download the example code so we can test as nessesary
RUN wget https://www.waveshare.com/w/upload/8/8d/LCD_Module_RPI_code.zip && \
    unzip ./LCD_Module_RPI_code.zip




# -----------------------------------------------------------------------
# 3) SETUP THE ROBBIE-9000 EYE MANAGER SERVICE

# Set the working directory to the 'robot' directory
WORKDIR /robbie/code_robbie

# Install any necessary Python packages
RUN echo "2"
COPY code_robbie/eye_manager/requirements.txt /tmp
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set the Python path to include the user's local package directory
ENV PYTHONPATH="${PYTHONPATH}:~/.local/lib/python3.11/site-packages"

EXPOSE 8000
#pulseaudio --start && \

WORKDIR /robbie/code_robbie/eye_manager
CMD python3 eye_service.py

