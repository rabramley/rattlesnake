import cython
import numpy
cimport numpy
from cython.parallel import prange
from libc.math cimport atan, pi
from libc.stdlib cimport malloc, free
from libc.string cimport memset


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True)
def repitch_sample(numpy.ndarray input, int original_note, int required_note):
    cdef float factor = pow(2, (<float> (original_note - required_note))/12)
    cdef float inv_factor = 1/factor
    cdef int values_in_output = int(len(input)*factor)
    cdef float* input_data = <float *> (input.data)
    cdef numpy.ndarray output = numpy.zeros(values_in_output, numpy.float32)
    cdef float* output_data = <float *> (output.data)

    cdef Py_ssize_t i
    cdef int before, after
    cdef float exact_point, before_value, after_value, diff,t

    for i in prange(values_in_output, nogil=True):
        exact_point = i * inv_factor
        before = <int> exact_point
        after = before + 1

        before_value = input_data[before]
        after_value = input_data[after]

        t = exact_point - before
        diff = after_value - before_value
        diff = diff * t

        output_data[i] = before_value + diff

    return output


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True)
def split_stereo_to_mono(numpy.ndarray input):
    cdef float* input_data = <float *> (input.data)
    cdef int ninput = len(input)/2
    cdef numpy.ndarray left = numpy.zeros(ninput, numpy.float32)
    cdef float* left_data = <float *> (left.data)
    cdef numpy.ndarray right = numpy.zeros(ninput, numpy.float32)
    cdef float* right_data = <float *> (left.data)

    cdef Py_ssize_t i


    for i in prange(ninput, nogil=True):
        left_data[i] = input_data[i*2]
        right_data[i] = input_data[i*2+1]

    return left, right


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True)
def mix_sounds(list playingsounds, int frame_count, numpy.ndarray output):
    cdef short* output_data = <short *> (output.data)
    cdef numpy.ndarray l, r, env
    cdef float* l_data
    cdef float* r_data
    cdef float* env_data
    cdef double *buffer = <double *> malloc(frame_count * 2 * sizeof(double))
    cdef float *frame = <float *> malloc(frame_count * sizeof(float))

    if not buffer:
        raise MemoryError()

    memset(buffer, 0, frame_count * 2 * sizeof(double));

    cdef double FACTORA = 16383
    cdef double FACTORB = 65535/pi
    cdef float velocity_gain
    cdef int position
    cdef Py_ssize_t i
    cdef Sound s

    try:
        for s in playingsounds:
            s.set_frame(frame_count, frame)

            for i in range(frame_count):
                buffer[i*2] += frame[i]
                buffer[i*2+1] += frame[i]

        for i in range(frame_count * 2):
            output_data[i] = <short> (atan(buffer[i]/FACTORA) * FACTORB)
    finally:
        free(buffer)
        free(frame)


cdef class Envelope:
    cdef int attack_end
    cdef float attack_gradient
    cdef int decay_end
    cdef float decay_gradient
    cdef float sustain_level
    cdef int release_time
    cdef int release_time_full
    cdef int release_start_position
    cdef int release_end
    cdef float release_gradient
    cdef bint is_released
    cdef bint killed
    cdef float killed_position
    cdef float last_volume

    def __cinit__(self, int attack_time, int decay_time, float sustain_level, int release_time):
        self.attack_end = attack_time
        self.attack_gradient = 1.0 / attack_time
        self.decay_end = attack_time + decay_time
        self.decay_gradient = (1.0 - sustain_level) / decay_time
        self.sustain_level = sustain_level
        self.release_time = release_time
        self.release_gradient = sustain_level / release_time
        self.release_time_full = int(1 / self.release_gradient)

        self.is_released = False
        self.killed = False
        self.last_volume = 0.0


    cdef apply_envelope(self, int position, int frame_count, float* frame):
        cdef float volume = 0
        cdef Py_ssize_t i
        cdef int i_pos

        for i in range(frame_count):
            i_pos = i + position

            if i_pos < self.attack_end:
                volume = i_pos * self.attack_gradient
            elif i_pos < self.decay_end:
                volume = 1 - ((i_pos - self.attack_end) * self.decay_gradient)
            elif not self.is_released:
                volume = self.sustain_level
            elif i_pos < self.release_end:
                volume = 1 - ((i_pos - self.release_start_position) * self.release_gradient)
            else:
                volume = 0.0
            
            frame[i] *= volume

        self.last_volume = volume


    def set_release_start(self, position):
        self.is_released = True
        self.release_start_position = position - self.release_time_full + int(self.last_volume * self.release_time_full)
        self.release_end = self.release_start_position + self.release_time_full

    def kill(self, position):
        self.killed = True
        self.killed_position = position - 100 + int(self.last_volume * 100)

    def complete_at(self, position):
        return self.killed or (self.is_released and position - self.release_start_position >= self.release_time_full)


cdef class Sound:
    cdef int note
    cdef numpy.ndarray sample
    cdef int sample_length
    cdef Envelope envelope
    cdef int velocity
    cdef int position
    cdef int sample_position
    cdef float velocity_gain
    cdef int first

    def __cinit__(self, int note, numpy.ndarray sample, Envelope envelope, int velocity):
        self.note = note
        self.sample = sample
        self.sample_length = len(sample)

        self.envelope = envelope
        self.position = 0
        self.sample_position = 0
        self.first = 1
        self.velocity = velocity
        self.velocity_gain = self.velocity / 127
    
    def complete(self):
        return self.envelope.complete_at(self.position)
    
    def get_note(self):
        return self.note
    
    cdef set_frame(self, int frame_count, float* frame):
        cdef Py_ssize_t i
        cdef float* sample_data = <float *> (self.sample.data)

        for i in range(frame_count):
            if self.sample_position >= self.sample_length:
                self.sample_position = 0 

            frame[i] = sample_data[self.sample_position] * self.velocity_gain

            self.sample_position += 1

        self.envelope.apply_envelope(self.position, frame_count, frame)

        self.position += frame_count

    def note_off(self) -> None:
        self.envelope.set_release_start(self.position)

    def kill(self) -> None:
        self.envelope.kill(self.position)
