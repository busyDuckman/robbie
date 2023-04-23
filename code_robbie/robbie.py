import os
import urllib.parse
import requests
import random
# import pygame
import pyaudio
from os import path
import wave
from io import BytesIO
import wave
import pickle
# from picklecache import cache
from datetime import datetime
# from bullshit import horoscope
# from .bullshit import horoscope
# import bullshit

from sentance_generator import SentanceGenerator


darebot_folder = "/home/pi/darebot"
resource_folder = path.join(darebot_folder, "data")
text_resource_folder = path.join(resource_folder, "text")

# @cache()
def init_dare_gen(markovLength = 1):
    print("----- CREATING NEW DARE GENERATOR ----")
    dare_files = ["darelist6.txt", "robotdares.txt", "formuladares.txt"]
    dare_files = [path.join(text_resource_folder, d) for d in dare_files]
    dare_generator = SentanceGenerator(dare_files, markovLength)
    return dare_generator

# @cache()
def init_lpt_gen(markovLength = 2):
    print("----- CREATING NEW LPT GENERATOR ----")
    files = ["top_lpt.txt"]
    files = [path.join(text_resource_folder, d) for d in files]
    generator = SentanceGenerator(files, markovLength)
    return generator


def current_time_readable():
    now = datetime.now()
    return now.strftime("%I:%M %p %A the ? of %B").replace("?", str(now.day) +
                                                    ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
                                                    [now.day % 10])\
        .replace("AM", "A.M.")\
        .replace("PM", "P.M.")


def sayit(text):
    if text is None or len(text.strip()) == 0:
        return

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
    resp = requests.post('http://localhost:59125/process', tts_params)

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


# ----------------------------------------------------------------------------------------------------------------------
# Darebot
# ----------------------------------------------------------------------------------------------------------------------

print("darebot init")

# There script (init.sh) to initialise the robot.
# It sets DAREBOT_INIT to true when run.
# if "DAREBOT_INIT" not in os.environ:
#     init_file = path.join(darebot_folder, "init.sh")
#     if path.exists(init_file):
#         print("Calling init.sh")
#         os.system(init_file)
#     else:
#         print("Could not find: " + init_file)
#
# dare_generator = init_dare_gen(1)
# lpt_gen = init_lpt_gen(3)

# hardware
# pygame.init()
audio = pyaudio.PyAudio()

# dares

print("darebot ready")

sayit("Hello world")

# sayit("Peter piper picked a peck of pickled peppers.")
# sayit('The doctor told me to get in a bathtub full of milk, to soothe my sunburn. I asked him "pasteurized?" he said...'
#       '"No, just up to your neck"')

# for i in range(20):
#     sayit(dare_generator.genSentence(1))

# sayit(bullshit.horoscope.generate(dirty=True))

# sayit(current_time_readable())
# sayit(random.choice(["Thankyou, I like it when u flick my switch!", "You are good at turning me on."]))


# sayit(lpt_gen.genSentence(2))

# for i in range(100):
#     print(lpt_gen.genSentence(3, 32, 128))

# while True:
#     text = input(">").lower().strip()
#     if text is "stop":
#         break;
#     elif "dare" in text:
#         sayit(dare_generator.genSentence(1))
#     elif "advice" in text:
#         sayit(lpt_gen.genSentence(3, 32, 128))
#     elif "time" in text:
#         now = datetime.datetime.now().strftime("")
#         sayit(dare_generator.genSentence(1))


# print(genSentence(markovLength))

audio.terminate()








