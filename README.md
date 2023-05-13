# Rattlesnake

```
sudo python3 setup.py build_ext --inplace
```

## To Do List
### Instruments
- [ ] Load samples with different file names
 - [x] Midinote suffix
 - [ ] Note name suffix, eg 'C#3'
 - [ ] Velocity suffix
- [ ] Instrument file
 - [ ] Decide format: YAML, JSON, TOML?
 - [ ] Sample - note and velocity
 - [ ] Envelope
 - [ ] Loop - start, end
- [ ] Panning

### Kits
- [ ] Sample per note
- [ ] Gunshot mitigation
 - [ ] Sample start randomization
 - [ ] Round robin samples
- [ ] Choke groups

### Samples
- [ ] Bitdepths
 - [ ] 8 bit
 - [x] 16 bit
 - [ ] 24 bit

### Envelopes
- [ ] Types
 - [x] ADSR
 - [ ] AD
 - [ ] ADSHR
- [ ] Slopes
 - [x] Linear
 - [ ] Exponential

### MIDI
- [ ] Plays notes on midi note down
- [ ] Channels per instrument

### Channels
- [ ] Instrument to channel
- [ ] Panning
- [ ] Multiple interfaces

### Optimization
- [ ] Envelopes
 - [ ] Cythonize
- [ ] Playback
 - [ ] Cythonize
- [ ] Multicore OpenMP: https://cython.readthedocs.io/en/latest/src/userguide/parallelism.html
