import os
import numpy as np
import sys
import warnings


class SciScanStack(object):

    def __init__(self, dirpath, mode='r'):
        """
        Read in a SciScan raw image stack as a memory-mapped numpy array

        Parameters
        --------------
        dirpath: str
            path to the directory containing the '.ini' and '.raw' files

        mode: str
            mode for opening the memmap array, see np.memmap

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
                        metadata.update(
                            {key:str2num(replace_problem_chars(val))}
                            )
                except ValueError:
                    continue
        self.metadata = metadata

        if self.metadata.experiment_type != 'XYT':
            warnings.warn('currently only single-channel XYT is supported')

        nx = int(metadata.x_pixels)
        ny = int(metadata.y_pixels)
        nframes = int(metadata.frame_count)

        self.shape = (nframes, nx, ny)
        self.dim_names = 'T', 'Y', 'X'

        # an mmap'ed array of frames (this could even be writeable...)
        self.frames = np.memmap(self.raw_path, dtype='>u2',
                                offset=0, mode=mode, shape=self.shape)


def replace_problem_chars(s):
    rules = [
        ('"', ''),
        ('..', '.'),
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

    if s.lower() in ('true', 'false'):
        return bool(s)
    else:
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s
