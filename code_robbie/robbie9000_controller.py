import sys

import pyaudio

from audio.listen import find_mic_array
from audio.playit import list_audio_output_devices
from audio.sayit import wait_for_tts_init, sayit
from utils.robbie9000_settings import Robbie9000


class _Robbie9000ControllerMeta(type):
    """
    Metaclass for the Robbie9000 controller.

    Holds global settings and resources for the Robbie9000 system.
    Assumes that all set calls are made during the startup phase, so no need for a lock.
    """
    initialised: bool = False

    def startup(self):
        sys.stdout.reconfigure(line_buffering=True)
        print("Robbie-9000")
        print("System Start")

        print("  - audio init")
        Robbie9000.audio_instance = pyaudio.PyAudio()
        Robbie9000.audio_in_device_num = find_mic_array()
        devices = list_audio_output_devices()

        print("  - tts service init")
        Robbie9000.tts_host = "marytts"
        Robbie9000.tts_port = 59125
        wait_for_tts_init()

        print("  - done.")
        self.do_stuff("hello world")
        # play_wav("/robbie/code_robbie/data/audio/startup.wav", audio)

        self.initialised = True

    def do_stuff(self, what):
        sayit(what)



class Robbie9000Controller(metaclass=_Robbie9000ControllerMeta):
    """
    Singleton class for conrolling the  Robbie9000
    """
    pass