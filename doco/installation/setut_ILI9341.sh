#!/bin/bash

# Update and upgrade the system
sudo apt-get update
sudo apt-get upgrade -y

# Configure SPI and ILI9341 in usercfg.txt
echo "dtparam=spi=on" | sudo tee -a /boot/firmware/usercfg.txt
echo "dtoverlay=ili9341:rotate=90" | sudo tee -a /boot/firmware/usercfg.txt

# Load fbtft_device module at boot
echo "fbtft_device" | sudo tee -a /etc/modules

# Create fbtft.conf file in /etc/modprobe.d/
echo "options fbtft_device name=ili9341 gpios=reset:25,dc:24,led:18 speed=16000000 rotate=90 bgr=1" | sudo tee /etc/modprobe.d/fbtft.conf

# Reboot the system
echo "The system will reboot now to apply the changes."
sudo reboot
