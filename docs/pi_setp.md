# Pi setup

## Audio for the listener

The listener (services/listener) plays through ALSA with kira. On the Pi the container is given
the sound card directly, with no PulseAudio:

    devices:
      - /dev/snd

Leave PULSE_SERVER unset there; the service only routes ALSA to PulseAudio when it is set.

Set the Pi up so kira can play outside a container too: install alsa-utils (aplay -l lists the
cards), make the speaker the default ALSA card, and add the user to the audio group.
