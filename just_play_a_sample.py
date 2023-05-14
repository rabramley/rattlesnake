from audio import AudioSystem
from instrument import Instrument
from pathlib import Path
import time


audio = AudioSystem(device=2, blocksize=512)
try:
    audio.start()
    print('Audio system started')
except:
    print('Failed to open audio system')
    exit(1)

saw_synth = Instrument(audio, Path('data/saw/'))

# for i in range(30, 80, 4):
#     saw_synth.note_on(i, 50)
#     time.sleep(1)
# time.sleep(4)

vel = 127

for i in range(4):
    saw_synth.note_on(38, vel)
    saw_synth.note_on(66, vel)
    saw_synth.note_on(57, vel)
    time.sleep(4)
    saw_synth.note_off(38)
    saw_synth.note_off(66)
    saw_synth.note_off(57)
    time.sleep(1)
    saw_synth.note_on(39, vel)
    saw_synth.note_on(70, vel)
    saw_synth.note_on(55, vel)
    time.sleep(4)
    saw_synth.note_off(39)
    saw_synth.note_off(70)
    saw_synth.note_off(55)
    time.sleep(1)
time.sleep(4)
