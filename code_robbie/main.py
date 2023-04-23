from io import BytesIO

import numpy as np
import requests
import wave
import pyaudio
from fastapi import FastAPI
import threading
import time


audio = pyaudio.PyAudio()
HOST_NAME = "robot_tts"

app = FastAPI()
detected_objects = set(["cat", "dog"])

def sayit(text):
    global HOST_NAME

    if text is None or len(text.strip()) == 0:
        return
    # <option>cmu-bdl-hsmm en_US male hmm</option>

    tts_params = {
        "INPUT_TYPE"    :   "TEXT",
        "AUDIO"         :   "WAVE_FILE",
        "OUTPUT_TYPE"   :   "AUDIO",
        "LOCALE"        :   "en_US",
        "INPUT_TEXT"    :   text,
        "effect_robot_selected"     : "on",
        "effect_robot_parameters"   : "amount:95.0"
    }

    print("TTS: " + text)
    resp = requests.post(f'http://{HOST_NAME}:59125/process', tts_params)

    wav = wave.open(BytesIO(resp.content))
    stream = audio.open(format = audio.get_format_from_width(wav.getsampwidth()),
                    channels = 1,
                    rate = wav.getframerate(),
                    output = True)
    #read data
    chunk = 1024
    data = wav.readframes(chunk)

    #play stream
    while data:
        stream.write(data)
        data = wav.readframes(chunk)

    #stop stream
    stream.stop_stream()
    stream.close()


@app.get("/api/what_seen")
async def get_detected_objects():
    return {"objects": list(detected_objects)}

def yolo_detection_loop():
    while True:
        # Run YOLO detection here and update the detected_objects set
        # For example: detected_objects.add("detected_item")
        print("Robbie-9000")
        time.sleep(1)  # Adjust the sleep time as needed

# Run YOLO detection loop in a separate thread
yolo_thread = threading.Thread(target=yolo_detection_loop, daemon=True)
yolo_thread.start()


# def main():
#     print("Robbie-9000")
#     print("System Start")
#     sayit("hello world")
#
#
#
#
# if __name__ == '__main__':
#     main()