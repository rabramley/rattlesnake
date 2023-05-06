from config import *
import numpy as np
import sounddevice
from samples import Sample


class Envelope:
    # Refactor so that an envelope is only a view on the
    # a shared envelope for the instrument
    def __init__(self, velocity, attack, decay, sustain, release):
        self.velocity = velocity
        self.velocity_gain = self.velocity / 127
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.release_start_position = -1
        self.release_end_position = -1

        self._ad = self.attack + self.decay

    def set_release_start(self, position):
        self.release_start_position = position
        self.release_end_position = position + self.release

    def over_range(self, position, frame_count):
        end = position + frame_count

        if self.release_start_position < 0:
            return self._pre_release_over_range(position, end)
        else:
            return self._post_release_over_range(position, end)
    
    def _pre_release_over_range(self, start, end):
        return np.array(np.interp(
            range(start, end),
            [0, self.attack, self._ad],
            [0.0, self.velocity_gain, self.sustain * self.velocity_gain],
        ), np.float32)

    def _post_release_over_range(self, start, end):
        return np.array(np.interp(
            range(start, end),
            [self.release_start_position, self.release_end_position],
            [self.sustain * self.velocity_gain, 0.0],
        ), np.float32)

    def complete_at(self, position):
        return self.release_start_position >= 0 and position - self.release_start_position >= self.release


class Sound:
    def __init__(self, sample: Sample, envelope: Envelope):
        self.sample = sample
        self.envelope = envelope
        self.position = 0
    
    def complete(self):
        return self.envelope.complete_at(self.position)
    
    def over_range(self, frame_count) -> tuple[np.ndarray, np.ndarray]:
        abs_pos =  self.position % self.sample.nframes

        env_curve = self.envelope.over_range(self.position, frame_count)

        l = np.roll(self.sample.left_data, -abs_pos)[:frame_count]*env_curve
        r = np.roll(self.sample.right_data, -abs_pos)[:frame_count]*env_curve

        self.position += frame_count

        return l,r

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

        for s in list(self.playingsounds.values()):
            lw, rw = s.over_range(frame_count)
            l += lw
            r += rw

            if s.complete():
                self.playingsounds.pop(s.id)

        stereo = np.ravel(np.stack((l, r)), order='F')
        outdata[:] = stereo.reshape(outdata.shape)

    def play(self, sound: Sound):
        self.next_sound_id += 1
        sound.id = self.next_sound_id
        self.playingsounds[sound.id] = sound
