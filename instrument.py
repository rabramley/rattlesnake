from audio import AudioSystem
from samples import Sample, SampleFile

class Instrument:
    def __init__(self, audio_system: AudioSystem, filename: str, sample_note: int) -> None:
        self.audio_system: AudioSystem = audio_system
        self.filename: str = filename
        self.sample_note: int = sample_note

    def note_on(self, note: int, velocity: int):
        sample = Sample('data/saw.wav', 36, note)
        self.audio_system.play(sample, note, 50)

    def note_off(self, note):
        pass
