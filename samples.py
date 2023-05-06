from config import *
import wave
import numpy as np
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
