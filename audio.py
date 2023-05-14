from config import *
import numpy as np
import sounddevice
from samples import Sample


class EnvelopeFactory:
    # Refactor so that an envelope is only a view on the
    # a shared envelope for the instrument
    def __init__(self, attack, decay, sustain, release, audio_system):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release

        self._ad = int(self.attack + self.decay)

        self._prerelease = np.array(np.interp(
            range(0, self._ad + audio_system.blocksize),
            [0, self.attack, self._ad],
            [0.0, 1.0, self.sustain],
        ), np.float16)
        self._sustain = np.array(np.interp(
            range(0, audio_system.blocksize),
            [0],
            [self.sustain],
        ), np.float16)
        self._release = np.array(np.interp(
            range(0, self.release + audio_system.blocksize),
            [0, self.release],
            [self.sustain, 0.0],
        ), np.float16)

    def get_envelope(self, velocity):
        return Envelope(self, velocity)


class Envelope:
    def __init__(self, factory, velocity):
        self.factory = factory
        self.velocity = velocity
        self.velocity_gain = self.velocity / 127
        self.release_start_position = -1
        self.release_end_position = -1

    def get_block(self, position: int, frame_count: int) -> np.ndarray:
        end = position + frame_count

        if self.release_start_position < 0:
            if position < self.factory._ad:
                return self.factory._prerelease[position:end] * self.velocity_gain
            else:
                return self.factory._sustain * self.velocity_gain
        else:
            return self.factory._release[position - self.release_start_position:end - self.release_start_position] * self.velocity_gain
    
    def set_release_start(self, position):
        self.release_start_position = position
        self.release_end_position = position + self.factory.release

    def complete_at(self, position):
        return self.release_start_position >= 0 and position - self.release_start_position >= self.factory.release

class Sound:
    def __init__(self, sample: Sample, envelope: Envelope):
        self.sample = sample
        self.envelope = envelope
        self.position = 0
    
    def complete(self):
        return self.envelope.complete_at(self.position)
    
    def next_block(self, frame_count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        abs_pos =  self.position % self.sample.nframes

        env_block = self.envelope.get_block(self.position, frame_count)
        l_block = np.roll(self.sample.left_data, -abs_pos)[:frame_count]
        r_block = np.roll(self.sample.right_data, -abs_pos)[:frame_count]

        self.position += frame_count

        return l_block, r_block, env_block

    def note_off(self) -> None:
        self.envelope.set_release_start(self.position)


class AudioSystem():
    def __init__(self, device, blocksize=512, samplerate=44100, channels=2, dtype='int16'):
        self.device = device
        self.blocksize = blocksize
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.playingsounds = {}
        self.next_sound_id = 0

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
        l = np.zeros(frame_count, np.float32)
        r = np.zeros(frame_count, np.float32)
        completed = []

        for i, s in enumerate(list(self.playingsounds.values())):
            lw, rw, env = s.next_block(frame_count)
            l += lw * env
            r += rw * env

            if s.complete():
                completed.append(s)

        for c in completed:
            self.playingsounds.pop(c.id)

        stereo = np.ravel(np.stack((l, r)), order='F')
        outdata[:] = stereo.reshape(outdata.shape)

    def play(self, sound: Sound):
        self.next_sound_id += 1
        sound.id = self.next_sound_id
        self.playingsounds[sound.id] = sound
