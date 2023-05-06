from audio import AudioSystem, Envelope, Sound
from samples import Sample, SampleFile
from pathlib import Path
from typing import Dict
from bisect import bisect_left


class Instrument:
    def __init__(self, audio_system: AudioSystem, sample_folder_path: Path) -> None:
        self.audio_system: AudioSystem = audio_system
        self.sample_folder_path: Path = sample_folder_path
        self.sample_files: Dict[int, SampleFile] = self._load_sample_files()
        self.sounds: Dict[int, Sound] = {}

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
        sample = self._get_sample_file(note)
        envelope = Envelope(velocity, self.audio_system.samplerate * 0.5, self.audio_system.samplerate * 0.5, 0.5, self.audio_system.samplerate * 2)

        sound = Sound(sample, envelope)

        self.sounds[note] = sound
        self.audio_system.play(sound)

    def note_off(self, note: int) -> None:
        sound = self.sounds[note]

        if sound:
            sound.note_off()

        self.sounds.pop(note)
