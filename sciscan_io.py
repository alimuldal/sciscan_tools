import os
import numpy as np
import sys
import warnings

# frames stored as big-endian uint16
DTYPE = np.dtype('>u2')


class SciScanStack(object):

    def __init__(self, dirpath, mode='r'):
        """
        Wraps a Scientifica SciScan raw image stack as a memory-mapped numpy
        array

        Parameters
        --------------
        dirpath: str
            path to the directory containing the '.ini' and '.raw' files

        mode: str
            mode for opening the memmap array, see docs for np.memmap

        Attributes
        --------------
        frames: np.memmap
            array containing the raw pixel values (big-endian uint16)

        metadata: Bunch
            dict-like object containing the metadata fields

        shape: tuple of ints
            dimensions of the stack

        dim_names: tuple of strings
            corresponding names of the dimensions

        raw_path, ini_path: str
            full paths to '.raw' and '.ini' files

        """

        ini_path, raw_path = None, None

        for ff in os.listdir(dirpath):
            base, ext = os.path.splitext(ff)
            if ext == '.raw':
                raw_path = os.path.join(dirpath, ff)
            elif ext == '.ini':
                ini_path = os.path.join(dirpath, ff)

        if None in (ini_path, raw_path):
            raise ValueError(
                'directory must contain both a ".raw" and a ".ini" file'
            )

        self.raw_path = raw_path
        self.ini_path = ini_path

        metadata = Bunch()
        with open(self.ini_path, 'r') as f:
            for line in f:
                try:
                    key, val = (vv.strip() for vv in line.split('='))
                    if val not in ("", '""'):
                        key = key.replace('.', '_')
                        key = key.replace('__', '_')
                        metadata.update(
                            {key: str2num(replace_problem_chars(val))}
                        )
                except ValueError:
                    # skip any lines that aren't 'key = value' pairs
                    continue
        self.metadata = metadata

        if self.metadata.experiment_type != 'XYT':
            warnings.warn('currently only single-channel XYT is supported')

        nx = int(metadata.x_pixels)
        ny = int(metadata.y_pixels)
        nc = int(metadata.no_of_channels)
        nframes = int(metadata.no_of_frames_to_acquire)

        if nc > 1:
            shape = (nframes, nc, ny, nx)
            dim_names = 'T', 'C', 'Y', 'X'
        else:
            shape = (nframes, ny, nx)
            dim_names = 'T', 'Y', 'X'

        # check file size (bytes)
        nbytes = os.stat(self.raw_path).st_size
        expected_nbytes = np.prod(shape) * DTYPE.itemsize
        if nbytes > expected_nbytes:
            # this can be OK as long as either expected < actual, or the file
            # is writeable (and can therefore be padded to the expected size)
            warnings.warn('mismatch between actual (%i B) and expected (%i B) '
                          'file sizes - the ".ini" metadata may be inaccurate.'
                          % (nbytes, expected_nbytes))

        self.shape = shape
        self.dim_names = dim_names

        # an mmap'ed array of frames (this could even be writeable...)
        self.frames = np.memmap(self.raw_path, dtype=DTYPE, offset=0,
                                mode=mode, shape=self.shape)


def replace_problem_chars(s):
    rules = [
        ('"', ''),
        ('..', '.'),
        ('(', ''),
        (')', ''),
        ('-', ''),
    ]
    for old, new in rules:
        s = s.replace(old, new)
    return s


class Bunch(dict):

    """
    a dict-like container whose elements can be accessed as class attributes
    """

    def __init__(self, **kw):
        dict.__init__(self, kw)
        self.__dict__ = self

    def __getstate__(self):
        return self

    def __setstate__(self, state):
        self.update(state)
        self.__dict__ = self


def str2num(s):
    """
    safely cast a string input to a numeric type (if possible). will try
    casting to the following types, in order of priority:

    bool > int > float > string
    """

    s = str(s)

    if s.lower() == 'true':
        return True
    elif s.lower() == 'false':
        return False
    else:
        for tt in (int, float):
            try:
                return tt(s)
            except ValueError:
                continue

    # if all else fails, return the string
    return s
