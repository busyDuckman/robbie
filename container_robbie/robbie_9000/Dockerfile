# Use the official Python 3.11 image as the base
FROM python:3.11

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

