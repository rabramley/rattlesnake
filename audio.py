from config import *
import numpy as np
import sounddevice


class Envelope:
    # Refactor so that an envelope is only a view on the
    # a shared envelope for the instrument
    def __init__(self, velocity, attack, decay, sustain, hold, release):
        self.velocity = velocity
        self.velocity_gain = self.velocity / 127
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.hold = hold
        self.release = release
        self.position = 0

        self._ad = self.attack + self.decay
        self._adh = self._ad + self.hold
        self._adhr = self._adh + self.release

    def subpath(self, frames):
        start = self.position
        self.position += frames
        return np.array(np.interp(
            range(start, self.position),
            [0, self.attack, self._ad, self._adh, self._adhr],
            [0.0, self.velocity_gain, self.sustain * self.velocity_gain, self.sustain * self.velocity_gain, 0.0],
        ), np.float32)
    
    def complete(self):
        return self.position >= self._adhr


class PlayingSound:
    def __init__(self, note, sound, envelope):
        self.sound = sound
        self.envelope = envelope
        self.note = note
        self.pos = 0
    
    def absolute_position(self):
        return self.pos % self.sound.nframes
    
    def complete(self):
        return self.envelope.complete()


class AudioSystem():
    def __init__(self, device, blocksize=512, samplerate=44100, channels=2, dtype='int16'):
        self.device = device
        self.blocksize = blocksize
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.playingsounds = {}

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

        for s in list(self.playingsounds.values()):
            env = s.envelope.subpath(frame_count)
            l += np.roll(s.sound.left_data, -s.absolute_position())[:frame_count]*env
            r += np.roll(s.sound.right_data, -s.absolute_position())[:frame_count]*env
            s.pos += frame_count

            if s.complete():
                self.playingsounds.pop(s.note)

        stereo = np.ravel(np.stack((l, r)), order='F')
        outdata[:] = stereo.reshape(outdata.shape)

    def unplay(self, note):
        self.playingsounds.pop(note)

    def play(self, sound, note, velocity):
        self.playingsounds[note] = PlayingSound(note, sound, Envelope(velocity, self.samplerate * 0.01, self.samplerate * 0.05, 0.5, self.samplerate * 0.5, self.samplerate * 4))
