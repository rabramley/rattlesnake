from audio import AudioSystem
from instrument import Instrument
import time


audio = AudioSystem(device=2, blocksize=512)
try:
    audio.start()
    print('Audio system started')
except:
    print('Failed to open audio system')
    exit(1)

saw_synth = Instrument(audio, 'data/saw.wav', 36)

for i in range(60, 64):
    saw_synth.note_on(i, 50)
    time.sleep(1)
time.sleep(4)
