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
 - [ ] One shot
- [ ] Panning
- [ ] polyphonic output compression - https://www.youtube.com/watch?v=2yzUDWDJYNs

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

### Config
- [ ] MIDI input port
- [ ] Audio interface

### MIDI
- [x] Plays notes on midi note on
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
- [x] Multicore OpenMP: https://cython.readthedocs.io/en/latest/src/userguide/parallelism.html
