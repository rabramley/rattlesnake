from config import *
import numpy as np
import sounddevice
from samples import Sample
from audio_utils import mix_sounds


class EnvelopeFactory:
    # Refactor so that an envelope is only a view on the
    # a shared envelope for the instrument
    def __init__(self, attack, decay, sustain, release, audio_system):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.blocksize = audio_system.blocksize

        self._ad = int(self.attack + self.decay)

        self._prerelease = np.array(np.interp(
            range(0, self._ad + self.blocksize),
            [0, self.attack, self._ad],
            [0.0, 1.0, self.sustain],
        ), np.float32)
        self._sustain = np.array(np.interp(
            range(0, self.blocksize),
            [0],
            [self.sustain],
        ), np.float32)
        self.full_release_time = int(self.release / self.sustain)
        self._release = np.array(np.interp(
            range(0, self.full_release_time + self.blocksize),
            [0, self.full_release_time],
            [1.0, 0.0],
        ), np.float32)
        self._kill = np.array(np.interp(
            range(0, self.blocksize * 2),
            [0, self.blocksize],
            [1.0, 0.0],
        ), np.float32)

    def get_envelope(self):
        return Envelope(self)


class Envelope:
    def __init__(self, factory):
        self.factory = factory
        self.release_start_position = 0
        self.killed_position = 0
        self.is_released = False
        self.killed = False
        self.last_volume = 0

    def get_block(self, position: int, frame_count: int) -> np.ndarray:
        end = position + frame_count
        result = []

        if self.killed:
            result = self.factory._kill[position - self.killed_position:end - self.killed_position]
        elif self.is_released:
            result = self.factory._release[position - self.release_start_position:end - self.release_start_position]
        else:
            if position < self.factory._ad:
                result = self.factory._prerelease[position:end]
            else:
                result = self.factory._sustain
    
        if len(result) > 0:
            self.last_volume = result[-1]

        return result

    def set_release_start(self, position):
        self.is_released = True
        self.release_start_position = position - self.factory.full_release_time + int(self.last_volume * self.factory.full_release_time)

    def kill(self, position):
        self.killed = True
        self.killed_position = position - self.factory.blocksize + int(self.last_volume * self.factory.blocksize)

    def complete_at(self, position):
        return self.killed or (self.is_released and position - self.release_start_position >= self.factory.full_release_time)

class Sound:
    def __init__(self, note: int, sample: Sample, envelope: Envelope, velocity: int):
        self.note = note
        self.sample = sample
        self.envelope = envelope
        self.position = 0
        self.velocity = velocity
        self.velocity_gain = self.velocity / 127
    
    def complete(self):
        return self.envelope.complete_at(self.position)
    
    def next_block(self, frame_count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        abs_pos =  self.position % self.sample.nframes

        l_block = np.roll(self.sample.left_data, -abs_pos)[:frame_count]
        r_block = np.roll(self.sample.right_data, -abs_pos)[:frame_count]

        self.position += frame_count

        return l_block, r_block

    def note_off(self) -> None:
        self.envelope.set_release_start(self.position)

    def kill(self) -> None:
        print("Killing")
        self.envelope.kill(self.position)


class AudioSystemListener():
    def completed(self, sound: Sound):
        pass


class AudioSystem():
    def __init__(self, device, blocksize=512, samplerate=44100, channels=2, dtype='int16'):
        self.device = device
        self.blocksize = blocksize
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.playingsounds = {}
        self.next_sound_id = 0
        self.listeners = []

    def start(self):
        sd = sounddevice.OutputStream(
            device=self.device,
            blocksize=self.blocksize,
            samplerate=self.samplerate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self,
        )
        sd.start()

    def __call__(self, outdata, frame_count, time_info, status):
        if status:
            print(status)
        mix_sounds(list(self.playingsounds.values()), frame_count, outdata)

        completed = []

        for s in list(self.playingsounds.values()):
            if s.complete():
                self.playingsounds.pop(s)
                for l in self.listeners:
                    l.completed(s)
        
    def play(self, sound: Sound):
        self.playingsounds[sound] = sound

    def register_listener(self, listener: AudioSystemListener):
        self.listeners.append(listener)