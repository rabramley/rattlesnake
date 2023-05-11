import cython
import numpy
cimport numpy


def repitch_sample(numpy.ndarray input, int original_note, int required_note):
    cdef float factor = pow(2, (<float> (original_note - required_note))/12)
    cdef float inv_factor = 1/factor
    cdef int values_in_output = int(len(input)*factor)
    cdef float* input_data = <float *> (input.data)
    cdef numpy.ndarray output = numpy.zeros(values_in_output, numpy.float32)
    cdef float* output_data = <float *> (output.data)

    cdef Py_ssize_t i
    cdef int before, after
    cdef float exact_point, before_value, after_value

    for i in range(values_in_output):
        exact_point = i * inv_factor
        before = <int> exact_point
        after = before + 1

        before_value = input_data[before]
        after_value = input_data[after]

        t = exact_point - before

        output_data[i] = before_value + t * (after_value - before_value)
    
    return output


def split_stereo_to_mono(numpy.ndarray input):
    cdef float* input_data = <float *> (input.data)
    cdef int ninput = len(input)/2
    cdef numpy.ndarray left = numpy.zeros(ninput, numpy.float32)
    cdef float* left_data = <float *> (left.data)
    cdef numpy.ndarray right = numpy.zeros(ninput, numpy.float32)
    cdef float* right_data = <float *> (left.data)

    cdef Py_ssize_t i

    for i in range(ninput):
        left_data[i] = input[i*2]
        right_data[i] = input[i*2+1]

    return left, right
