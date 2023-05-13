FROM balenalib/raspberrypi4-64-debian-python:3.11-bullseye

# Lets install raspberry pi stuff, and common compile tools
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        libraspberrypi-dev \
        raspberrypi-kernel \
        raspberrypi-kernel-headers \
        gcc \
        git \
        build-essential \
        python3-opengl \
        libglfw3-dev \
        autoconf automake \
        libtool \
        wget \
        unzip

# -----------------------------------------------------------------------
RUN mkdir -p /robbie/third_party

# -----------------------------------------------------------------------
# Build OpenCV
#   - This will take a while, sof lets to it first.

RUN apt-get install -y \
    libjpeg-dev libtiff5-dev  libpng-dev \
    libatlas-base-dev gfortran \
    cmake gfortran \
    python3-dev python3-numpy \
    libjpeg-dev libtiff-dev libgif-dev \
    libgstreamer1.0-dev gstreamer1.0-gtk3 \
    libgstreamer-plugins-base1.0-dev gstreamer1.0-gl \
    libavcodec-dev libavformat-dev libswscale-dev \
    libgtk2.0-dev libcanberra-gtk* \
    libxvidcore-dev libx264-dev libgtk-3-dev \
    libtbb2 libtbb-dev libdc1394-22-dev libv4l-dev \
    libopenblas-dev libatlas-base-dev libblas-dev \
    liblapack-dev libhdf5-dev \
    protobuf-compiler

# Compile OpenCV
# looks like buster no longer supports libjasper-dev, so meh.
# As openCV only uses it for jpeg2000,
# will have to make with -D BUILD_JASPER=off

WORKDIR /robbie/third_party
RUN git clone https://github.com/opencv/opencv.git \
     && cd opencv \
     && mkdir build \
     && cd build \
     && cmake -D BUILD_JASPER=off -D CMAKE_BUILD_TYPE=Release -D CMAKE_INSTALL_PREFIX=/usr/local .. \
     && make -j$(nproc) \
     && make install


RUN apt-get install -y python3-opencv

# -----------------------------------------------------------------------
# all containers will have this user

# -----------------------------------------------------------------------
# Done
WORKDIR /robbie