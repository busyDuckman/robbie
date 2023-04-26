"""
This module contains the play_sound function for playing simple beep sequences
using PyAudio. It supports sine, square, triangle, and sawtooth waveforms,
with the ability to control playback speed and apply a decay factor to simulate
the fall-off of a piano-like sound.

Example usage:

import yaml

# Load music library from YAML file
with open("music_library.yaml", "r") as f:
    music_library = yaml.safe_load(f)

# Play a sequence of notes with a square wave and a decay factor of 2.0
play_sound(music_library["happy"], wave_type='square', decay_factor=2.0)

# Play a sequence of notes with a triangle wave, no decay, and a speed factor
  of 0.5 (slower)
play_sound(music_library["thinking"], wave_type='triangle', decay_factor=0.0, speed_factor=0.5)

Music Library Format:
  - The music library is a dictionary with keys corresponding to beep types
    (e.g., "happy", "thinking", etc.)
  - Each value is a string containing a semicolon-separated list of notes and
    durations in the format "NOTE,DURATION"
    (e.g., "C4,0.1; E4,0.1; G4,0.1; C5,0.1")
  - NOTES are specified as letter (A-G), optional sharp (#), and octave (0-8)
  - DURATIONS are specified as decimal values in seconds (e.g., 0.1 for 100ms)
"""

from os.path import join
import yaml
import numpy as np
import pyaudio

from utils.robbie9000_settings import Robbie9000


def note_to_frequency(note: str) -> float:
    """
    Turns a note, with octave, eg "C#8" into a frequency.
    Notes are specified as letter (A-G), optional sharp (#).
    """
    A4 = 440
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    if '#' in note:
        key = note[0:2].upper()
        octave = int(note[2]) + 1
    else:
        key = note[0].upper()
        octave = int(note[1]) + 1

    key_number = keys.index(key)
    return A4 * pow(2, (octave * 12 + key_number - 49) / 12)


def play_sound(sound_string,
               sample_rate=44100,
               wave_type='sine',
               decay_factor=0.0,
               speed_factor=1.0):
    """
    Plays a sound string (simple music).
    :param sound_string: eg: "C4,0.25; E4,0.25; G4,0.25; C5,0.25; G4,0.25; E4,0.25; C4,0.25; G3,0.25"
    :param audio: PyAudio object to play to,
    :param sample_rate: waveform resolution.
    :param wave_type: 'sine', 'square', 'triangle', 'sawtooth'
    :param decay_factor: > 0 adds a piano like amplitude falloff to each note.
    :param speed_factor: Playback speed multiplier.
    """

    audio = Robbie9000.audio

    if isinstance(sound_string, dict):
        sound_string = sound_string['melody']

    sequence = [(note_duration.split(',')[0], float(note_duration.split(',')[1])) for note_duration in sound_string.split('; ')]

    stream = audio.open(format=pyaudio.paFloat32, channels=1, rate=sample_rate, output=True)

    for note, duration in sequence:
        freq = note_to_frequency(note)
        wave = generate_wave(freq, duration / speed_factor, sample_rate, wave_type, decay_factor)
        stream.write(wave.tobytes())

    stream.stop_stream()
    stream.close()


def generate_wave(freq, duration, sample_rate=44100, wave_type='sine', decay_factor=0.0):
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    if wave_type == 'sine':
        wave = np.sin(2 * np.pi * freq * t)
    elif wave_type == 'square':
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave_type == 'triangle':
        wave = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    elif wave_type == 'sawtooth':
        wave = 2 * (t * freq % 1) - 1
    else:
        raise ValueError(f"Invalid wave_type: {wave_type}")

    if decay_factor > 0:
        decay = np.exp(-decay_factor * t)
        wave *= decay

    return wave.astype(np.float32)
    # return (wave / np.max(np.abs(wave))) * 0.5

# def generate_sine_wave(freq, duration, sample_rate=44100):
#     t = np.linspace(0, duration, int(sample_rate * duration), False)
#     sine_wave = 0.5 * np.sin(2 * np.pi * freq * t)
#     return sine_wave.astype(np.float32)


# def generate_square_wave(freq, duration, sample_rate=44100):
#     t = np.linspace(0, duration, int(duration * sample_rate), False)
#     square_wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5
#     return square_wave

def parse_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    data_path = "../data"
    yaml_data = parse_yaml(join(data_path, 'dialogue/beep_library.yaml'))
    beeps = yaml_data['beeps']

    # play_sound("B4,0.5; D5,0.25; G5,0.5; F#5,0.25; E5,0.25; D5,0.25; C#5,0.25; B4,0.25")

    # for wave_type in ["sine", "square", "triangle", "sawtooth"]:
    # play_sound(beeps['imperial_march'], speed_factor=0.25)

    audio = pyaudio.PyAudio()

    wave_type = "square"
    for name, info in beeps.items():
        print("wave type: ", wave_type)
        print("name: ", name)
        sound = info['melody']
        play_sound(sound, audio, wave_type=wave_type, decay_factor=0.0)
        print()

    print("Done.")

if __name__ == "__main__":
    main()