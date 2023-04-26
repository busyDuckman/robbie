import wave
from io import BytesIO
import pyaudio

from utils.robbie9000_settings import Robbie9000


def list_audio_output_devices():
    audio = Robbie9000.audio

    output_devices = []
    print("  - Listing audio output devices:")

    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        if device_info["maxOutputChannels"] > 0:
            output_devices.append((i, device_info["name"]))
            print("    - found:", device_info["name"])

    return output_devices


def play_wav(file_path):
    # Open the WAV file
    wav = wave.open(file_path, 'rb')

    audio = Robbie9000.audio

    # Set up the stream
    stream = audio.open(format=audio.get_format_from_width(wav.getsampwidth()),
                        channels=wav.getnchannels(),
                        rate=wav.getframerate(),
                        output=True)

    # Read and play the file in chunks
    chunk = 1024
    data = wav.readframes(chunk)
    while data:
        stream.write(data)
        data = wav.readframes(chunk)

    # Stop and close the stream
    stream.stop_stream()
    stream.close()

