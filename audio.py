from config import *
import wave
import numpy as np
import sounddevice
from chunk import Chunk
import struct


class waveread(wave.Wave_read):
    def initfp(self, file):
        self._convert = None
        self._soundpos = 0
        self._cue = []
        self._loops = []
        self._ieee = False
        self._file = Chunk(file, bigendian=0)
        if self._file.getname() != b'RIFF':
            raise IOError('file does not start with RIFF id')
        if self._file.read(4) != b'WAVE':
            raise IOError('not a WAVE file')
        self._fmt_chunk_read = 0
        self._data_chunk = None
        while 1:
            self._data_seek_needed = 1
            try:
                chunk = Chunk(self._file, bigendian=0)
            except EOFError:
                break
            chunkname = chunk.getname()
            if chunkname == b'fmt ':
                self._read_fmt_chunk(chunk)
                self._fmt_chunk_read = 1
            elif chunkname == b'data':
                if not self._fmt_chunk_read:
                    raise IOError('data chunk before fmt chunk')
                self._data_chunk = chunk
                self._nframes = chunk.chunksize // self._framesize
                self._data_seek_needed = 0
            elif chunkname == b'cue ':
                numcue = struct.unpack('<i', chunk.read(4))[0]
                for i in range(numcue):
                    id, position, datachunkid, chunkstart, blockstart, sampleoffset = struct.unpack('<iiiiii', chunk.read(24))
                    self._cue.append(sampleoffset)
            elif chunkname == b'smpl':
                manuf, prod, sampleperiod, midiunitynote, midipitchfraction, smptefmt, smpteoffs, numsampleloops, samplerdata = struct.unpack(
                    '<iiiiiiiii', chunk.read(36))
                for i in range(numsampleloops):
                    cuepointid, type, start, end, fraction, playcount = struct.unpack('<iiiiii', chunk.read(24))
                    self._loops.append([start, end])
            chunk.skip()
        if not self._fmt_chunk_read or not self._data_chunk:
            raise IOError('fmt chunk and/or data chunk missing')

    def getmarkers(self):
        return self._cue

    def getloops(self):
        return self._loops

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


class Sound:
    def __init__(self, filename, samplenote, midinote):
        wf = waveread(filename)
        self.fname = filename
        self.midinote = midinote
        self.samplenote = samplenote
        self.channels = wf.getnchannels()
        self.sample_width = wf.getsampwidth()

        if wf.getloops():
            self.loop = wf.getloops()[0][0]
            self.nframes = wf.getloops()[0][1] + 2
        else:
            self.loop = -1
            self.nframes = wf.getnframes()
        
        self.set_data(wf.readframes(self.nframes))
        
        wf.close()

        if self.samplenote != self.midinote:
            factor = pow(2, ((self.midinote - self.samplenote)/12))
            self.left_data = np.array(np.interp(
                [i*factor for i in range(1, int(self.nframes/factor))],
                range(1, self.nframes),
                self.left_data,
            ), np.float32)
            self.right_data = np.array(np.interp(
                [i*factor for i in range(1, int(self.nframes/factor))],
                range(1, self.nframes),
                self.right_data,
            ), np.float32)
            self.nframes = len(self.right_data)

    def set_data(self, data):
        if self.sample_width != 2:
            # For sample width of 3
            raise Exception(f"Only support 16 bit samples at the minute.  This file has a sample with of {self.sample_width}")

        data = np.frombuffer(data, dtype=np.int16)

        if self.channels == 2:
            self.left_data = np.array(data[::2], np.float32)
            self.right_data = np.array(data[1::2], np.float32)
        elif self.channels == 1:
            self.left_data = np.array(data, np.float32)
            self.right_data = np.array(data, np.float32)
        else:
            raise Exception(f"Only support 1 or 2 channel audio samples, not {self.channels}")


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
