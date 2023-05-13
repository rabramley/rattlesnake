from rtmidi.midiutil import open_midiinput
import time
from audio import AudioSystem
from instrument import Instrument
from pathlib import Path
from rtmidi.midiconstants import (
    NOTE_OFF,
    NOTE_ON, 
)

PORT_NAME = 'UX16 MIDI 1'

audio = AudioSystem(device=2, blocksize=512)
try:
    audio.start()
    print('Audio system started')
except:
    print('Failed to open audio system')
    exit(1)

saw_synth = Instrument(audio, Path('data/saw/'))

def midi_callback(event, *args):
    event, delta = event
    status = event[0] & 0xF0
    ch = event[0] & 0xF

    if status == NOTE_ON:
        note = event[1]
        velocity = event[2]
        saw_synth.note_on(note, velocity)
    elif status == NOTE_OFF:
        note = event[1]
        saw_synth.note_off(note)

try:
    midiin, _ = open_midiinput(PORT_NAME)
    midiin.set_callback(midi_callback)
except Exception as e:
    print(f"An error occurred opening MIDI Port '{PORT_NAME}'")
    print(e)

try:
    with midiin:
        while True:
            time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    midiin.close_port()
    del midiin