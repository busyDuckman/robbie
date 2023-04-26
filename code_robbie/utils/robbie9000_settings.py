import pyaudio


class _Robbie9000Meta(type):
    """
    Metaclass for the Robbie9000 singleton.

    Holds global settings and resources for the Robbie9000 system.
    Assumes that all set calls are made during the startup phase, so no need for a lock.
    """

    audio: pyaudio.PyAudio = pyaudio.PyAudio()
    audio_out_device_num: int = None
    audio_in_device_num: int = None
    tts_host: str = None
    tts_port: int = None


class Robbie9000(metaclass=_Robbie9000Meta):
    """
    Singleton class for accessing global Robbie9000 settings and resources.

    Example usage:
        Robbie9000.audio_instance = pyaudio.PyAudio()
        out_dev_num = Robbie9000.output_device_num

    """
    pass
