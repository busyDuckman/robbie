# Robie-9000 Installation Guide 🚀  

Congratulations on your choice to replicate a Robie-9000, 
the finest personal mechanical overlord in the galaxy. This guide will help you
traverse the software installation with ease.


## Overview
The Robie-9000 works with a host computer for larger AI tasks,
and a raspberry pi for onboard compute. These two systems will 
communicate via ssh.

# Raspberry pi setup.

## Before we start:
At this point It is assumed you have obtained a pi-4 or later and
installed the latest ubuntu OS on it; and connected it to your
wifi network. You will have given it a static IP address via
your router, which you will save for future reference.


## Step 1: Preparing Your Raspberry Pi for remote access (SSH) 📡
Firstly, connect your Raspberry Pi to a display, keyboard, and mouse.
Power it on and when it has booted open the Terminal by pressing
Ctrl + Alt + T.

Run the following command to update your package list and 
install any available upgrades:

    sudo apt update && sudo apt upgrade -y

In order to enable SSH, execute the following command:

    sudo apt install openssh-server
    sudo systemctl enable ssh
    sudo systemctl start ssh

If that produced an error, do it this way:

    sudo apt purge openssh-client
    sudo apt install openssh-server
    sudo systemctl enable ssh
    sudo systemctl start ssh

### Configure ssh authentication 🔑

Configure ssh to store a public key so that passwords are not needed.

If your host machine does not have a ssh key, make one now:

    ssh-keygen -t rsa

Now copy the public key to robie:

    ssh-copy-id pi@your_pi_ip_address

Note: you may have used another user than pi, 
that's OK use that instead.

Now add robie to your PC's ssh config.

Edit nano ~/.ssh/config

Add the following configuration to the file, 
replacing pi and your_pi_ip_address with the actual 
username and  IP address of your Raspberry Pi:

    Host robie
        HostName your_pi_ip_address
        User pi

The PC machine can connect to robie via the command:

    ssh robie

Try it out to make sure it works. It should authenticate without
asking you for a password.

Once this is complete your Raspberry Pi is ready for remote 
management and connection with the host. You can unplug the 
keyboard and mouse.


## Step 2: Installing Docker 🐋
Step 2 is completed on the PC, via the SSH Terminal ("ssh robie").

Docker is used to simplify setting up the Robie-9000. It can be 
difficult to set up docker, but overall it makes everything
less painful.

In the remote terminal input the following commands to
install Docker:

    sudo apt-get install \
        ca-certificates \
        curl \
        gnupg


    sudo mkdir -m 0755 -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

     echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    sudo usermod -aG docker $(whoami)
    
Now Reboot your Raspberry Pi for the changes to take effect:

    sudo reboot now

Note: the process to install docker changes from time to time. This is 
written in 2023; You may need to consult newer doco on th subject.

To verify docker is running, try:

    docker run hello-world

# Step 3 Enabling SPI and SPI_1 Interfaces on Raspberry Pi 4 (Running Ubuntu)
To use the eye dispays, you need to enable the primary (spi0) and secondary (spi1) SPI interfaces:

Open the config.txt file, which is located in the /boot/firmware directory.

    sudo nano /boot/firmware/config.txt

The primary SPI interface is likely already enabled.   
Look for a line that reads dtparam=spi=on. If it's not present, add it to the file.

Enable the secondary SPI interface (spi1) by adding the following line after dtparam=spi=on:

    dtoverlay=spi1-1cs

Your config.txt file should now look a little like this:

    [pi4]
    max_framebuffers=2
    arm_boost=1
    
    [all]
    # Enable the audio output, I2C and SPI interfaces on the GPIO header. As these
    # parameters related to the base device-tree they must appear *before* any
    # other dtoverlay= specification
    dtparam=audio=on
    dtparam=i2c_arm=on
    dtparam=spi=on

    # Enable the additional SPI interface
    dtoverlay=spi1-1cs


Save, and reboot your Raspberry Pi for the changes to take effect.

    sudo reboot now

After the reboot, the new SPI device should appear as /dev/spidev1.0 in your system.
You can check this by running ls /dev/spi* in the terminal, you should see:

    robbie@robbie-9000:~$ ls /dev/spi*
    /dev/spidev0.0  /dev/spidev0.1  /dev/spidev1.0

## final steps

# install the robbie software

    sudo mkdir /robbie

    sudo chown $(whoami):$(whoami) /robbie

# Host PC setup.💻
You will need a host PC to run all the commands to 
computationally intensive for the onboard Pi.

This can be a cloud host, or a local machine. The 
requirements are quite steep (as of 2023). Your 
PC should have:

  - Nvidia RTC 3080 or higher with 8GB Graphics Memory
  - 4 GB spare RAM
  - 200GB free HDD space

Rejoice, for the Robie-9000 has been unleashed! Its vintage tinny voice shall serenade your ears.

Fellow traveler, your journey is complete. The Robie-9000 is now under your command. Go forth and explore the sonic cosmos! 🌌

