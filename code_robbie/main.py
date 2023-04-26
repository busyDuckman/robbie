"""
Robbie-9000 Source base.
  - fastapi endpoints to interact with robbie
  - main loops to run hardware
  - setup and init robot
"""
import sys
from io import BytesIO

import numpy as np
import requests
import wave
import pyaudio
from fastapi import FastAPI
import threading
import time
import subprocess

from robbie9000_controller import Robbie9000Controller

app = FastAPI()
detected_objects = set(["cat", "dog"])

@app.get("/api/what_seen")
async def get_detected_objects():
    return {"objects": list(detected_objects)}

def yolo_detection_loop():
    while True:
        # Run YOLO detection here and update the detected_objects set
        # For example: detected_objects.add("detected_item")
        # print("Robbie-9000")
        time.sleep(1)  # Adjust the sleep time as needed

# Run YOLO detection loop in a separate thread
yolo_thread = threading.Thread(target=yolo_detection_loop, daemon=True)
yolo_thread.start()

@app.on_event("startup")
async def on_startup():

    def run_command(command):
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        return result.stdout + result.stderr

    aplay_output = run_command("aplay -l")
    arecord_output = run_command("arecord -l")

    print("Output devices:\n", aplay_output)
    print("Input devices:\n", arecord_output)

    Robbie9000Controller.startup()



