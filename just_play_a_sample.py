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

for i in range(30, 80, 4):
    saw_synth.note_on(i, 50)
    time.sleep(1)
time.sleep(4)
