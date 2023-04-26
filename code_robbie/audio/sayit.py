"""
The sayit(...) function is core to the robbie-9000's speach and emotive
display capability.

"""
import wave
from io import BytesIO
import pyaudio

import requests

from utils.network import wait_for_port, wait_for_port_pb
from utils.robbie9000_settings import Robbie9000


def wait_for_tts_init():
    host = Robbie9000.tts_host
    port = Robbie9000.tts_port

    t = wait_for_port(host, port, timeout=30)
    t = round(t, 2)
    print(f"    - reached {host}:{port} after {t} seconds.")

def sayit(text):
    """
    Plays TTS audio output of the given text, in a robotic voice.
    """
    audio = Robbie9000.audio
    audio_out_device_num = Robbie9000.audio_out_device_num

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
    resp = requests.post(f'http://marytts:59125/process', tts_params)

    wav = wave.open(BytesIO(resp.content))
    stream = audio.open(format = audio.get_format_from_width(wav.getsampwidth()),
                    channels = 1,
                    rate = wav.getframerate(),
                    output = True,
                    output_device_index=audio_out_device_num)
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