import platform
if platform.system() == 'Darwin':
    import matplotlib
    matplotlib.use('TkAgg')
from .core import *
from .data import *
__version__ = '0.12.1'
