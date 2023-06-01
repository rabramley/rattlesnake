from audio import AudioSystem
from instrument import Instrument
from pathlib import Path
import time


audio = AudioSystem(device=2, blocksize=32)
try:
    audio.start()
    print('Audio system started')
except:
    print('Failed to open audio system')
    exit(1)

saw_synth = Instrument(audio, Path('data/saw/'), 128)

# for i in range(30, 80, 4):
#     saw_synth.note_on(i, 50)
#     time.sleep(1)
# time.sleep(4)

vel = 50
pacing=1
note=50

for i in range(10):
    saw_synth.note_on(note, vel)
    saw_synth.note_on(note+4, vel)
    saw_synth.note_on(note+7, vel)
    time.sleep(pacing)
    saw_synth.note_off(note)
    saw_synth.note_off(note+4)
    saw_synth.note_off(note+7)
    time.sleep(pacing/4)
    note+=1
    # time.sleep(pacing/8)
    # saw_synth.note_on(39, vel)
    # saw_synth.note_on(70, vel)
    # saw_synth.note_on(55, vel)
    # time.sleep(pacing)
    # saw_synth.note_off(39)
    # saw_synth.note_off(70)
    # saw_synth.note_off(55)
    # time.sleep(pacing/8)
time.sleep(8)
