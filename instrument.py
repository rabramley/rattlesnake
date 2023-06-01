from audio import AudioSystem, EnvelopeFactory, AudioSystemListener
from audio_utils import Envelope, Sound
from samples import Sample, SampleFile
from pathlib import Path
from typing import Dict
from bisect import bisect_left
from collections import deque


class Instrument(AudioSystemListener):
    def __init__(self, audio_system: AudioSystem, sample_folder_path: Path, polyphony: int) -> None:
        self.audio_system: AudioSystem = audio_system
        self.sample_folder_path: Path = sample_folder_path
        self.sample_files: Dict[int, SampleFile] = self._load_sample_files()
        self.sounds: Dict[int, Sound] = {}
        self.poly_used = deque()
        self.envelope_factory = EnvelopeFactory(
            self.audio_system.samplerate * 0.01,
            self.audio_system.samplerate * 0.5,
            0.5,
            self.audio_system.samplerate * 2,
            self.audio_system,
        )
        self.audio_system.register_listener(self)
        self.polyphony = polyphony

    def _load_sample_files(self) -> Dict[int, SampleFile]:
        result: Dict[int, SampleFile] = {}

        for f in self.sample_folder_path.glob('*.wav'):
            try:
                note: int = int(f.stem)
            except ValueError:
                raise ValueError(f"Sample file name format '{f.name}' should be an integer")
        
            result[note] = SampleFile(str(f), note)
        return result
    
    def _get_sample_file(self, note: int) -> SampleFile:
        keys = sorted(list(self.sample_files.keys()))
        ind = bisect_left(keys, note)

        if ind == 0:
            sample_note = keys[ind]
        elif ind >= len(keys):
            sample_note = keys[ind-1]
        else:
            ind_diff = abs(keys[ind] - note)
            ind_1_diff = abs(keys[ind-1] - note)

            if ind_diff < ind_1_diff:
                sample_note = keys[ind]
            else:
                sample_note = keys[ind-1]
        
        return Sample(self.sample_files[sample_note], note)

    def note_on(self, note: int, velocity: int) -> None:
        if note in self.sounds:
            self.sounds[note].kill()

        while len(self.poly_used) >= self.polyphony:
            self.kill(self.poly_used.popleft().get_note())

        sample = self._get_sample_file(note)
        envelope = Envelope(
            int(self.audio_system.samplerate * 0.01),
            int(self.audio_system.samplerate * 0.5),
            0.2,
            int(self.audio_system.samplerate * 8),
        )

        sound = Sound(note, sample.left_data, envelope, velocity)

        self.kill(note)

        self.sounds[note] = sound
        self.poly_used.append(sound)
        self.audio_system.play(sound)

    def note_off(self, note: int) -> None:
        if note in self.sounds:
            self.sounds[note].note_off()

    def kill(self, note: int) -> None:
        if note in self.sounds:
            self.sounds[note].kill()
            s = self.sounds.pop(note)
            if s in self.poly_used:
                self.poly_used.remove(s)

    def completed(self, sound: Sound):
        if sound.get_note() in self.sounds:
            existing = self.sounds[sound.get_note()]
            if existing is sound:
                self.sounds.pop(sound.get_note())
