from Cython.Build import cythonize
from setuptools import Extension, setup
import numpy

ext_modules = [
    Extension(
        "audio_utils",
        ["audio_utils.pyx"],
        extra_compile_args=['-fopenmp'],
        extra_link_args=['-fopenmp'],
    )
]

setup(
    name='audio_utils',
    ext_modules=cythonize(ext_modules, language_level = "3"),
    include_dirs=[numpy.get_include()],
)
