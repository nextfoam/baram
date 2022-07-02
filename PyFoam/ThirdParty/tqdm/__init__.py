# import everything from the real library

from .tqdm._tqdm import tqdm
from .tqdm._tqdm import trange
from .tqdm._tqdm_gui import tqdm_gui
from .tqdm._tqdm_gui import tgrange
from .tqdm._tqdm_pandas import tqdm_pandas
# from ._main import main
from .tqdm._version import __version__  # NOQA

__all__ = ['tqdm', 'tqdm_gui', 'trange', 'tgrange', 'tqdm_pandas',
           '__version__']
