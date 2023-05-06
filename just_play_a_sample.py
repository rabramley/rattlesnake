from audio import AudioSystem
from samples import Sound
import time

audio = AudioSystem(device=2, blocksize=512)
try:
    audio.start()
    print('Audio system started')
except:
    print('Failed to open audio system')
    exit(1)

for i in range(60, 73):
    sample = Sound('data/saw.wav', 36, i)
    audio.play(sample, i, 50)
    time.sleep(1)
time.sleep(4)
