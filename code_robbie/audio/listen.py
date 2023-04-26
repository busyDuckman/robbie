import pyaudio
import numpy as np
import time

from utils.robbie9000_settings import Robbie9000


# Find the ReSpeaker device
def find_mic_array():
    audio = Robbie9000.audio

    device_index = None
    print("  - Finding mic array:")
    print("    - available devices:")
    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        name = device_info["name"].lower()
        print(f"      - {i}: {name}")

    for i in range(audio.get_device_count()):
        device_info = audio.get_device_info_by_index(i)
        name = device_info["name"].lower()
        if "arrayuac10" in name or "respeaker" in name:
            device_index = i
            print(f"    - found mic array: {device_info['name']}")
            break
    else:
        print(f"    - mic array not found.")
    print()
    return device_index

# Record audio from the ReSpeaker device
def record_audio(device_index, record_seconds=5, threshold=500):
    chunk_size = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 16000

    p = pyaudio.PyAudio()
    stream = p.open(format=format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=chunk_size)

    print("Recording...")

    audio_data = []

    for _ in range(int(rate / chunk_size * record_seconds)):
        data = stream.read(chunk_size)
        audio_data.append(data)
        amplitude = np.frombuffer(data, dtype=np.int16)
        if np.abs(amplitude).mean() > threshold:
            audio_data = [data]  # Reset the buffer

    print("Recording complete.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    return b"".join(audio_data)

if __name__ == '__main__':
    device_index = find_mic_array(audio)

    if device_index is not None:
        print(f"ReSpeaker device found at index {device_index}.")
        recorded_audio = record_audio(device_index)
    else:
        print("ReSpeaker device not found.")
