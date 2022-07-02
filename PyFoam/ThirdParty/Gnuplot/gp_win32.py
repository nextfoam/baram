# $Id$

# Copyright (C) 1999-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""gp_win32 -- an interface to gnuplot for Windows.

"""

from . import Errors

# ############ Configuration variables: ################################

class GnuplotOpts:
    """The configuration options for gnuplot under windows.

    See gp_unix.py for details about the meaning of these options.
    Please let me know if you know better choices for these settings.

    """

    # Command to start up the gnuplot program.  Note that on windows
    # the main gnuplot program cannot be used directly because it can
    # not read commands from standard input.  See README for more
    # information.
    #
    # If pgnuplot is in a subdirectory with spaces in its name, extra
    # quoting is required for windows for it to launch gnuplot.
    # Moreover, it is suggested to use a raw string to avoid having to
    # quote backslashes in the filename.  Example:
    #
    #     gnuplot_command = r'"C:\Program Files\gp371w32\pgnuplot.exe"'
    gnuplot_command = r'pgnuplot.exe'

    # The '-persist' option is not supported on windows:
    recognizes_persist = 0

    # As far as I know, gnuplot under windows can use binary data:
    recognizes_binary_splot = 1

    # Apparently gnuplot on windows can use inline data, but we use
    # non-inline data (i.e., temporary files) by default for no
    # special reason:
    prefer_inline_data = 0

    # os.mkfifo is apparently not supported under Windows.
    support_fifo = 0
    prefer_fifo_data = 0

    # The default choice for the 'set term' command (to display on
    # screen):
    default_term = 'windows'

    # According to the gnuplot help manual, the following can be used
    # to print directly to a printer under windows.  (Of course it
    # won't help if your printer can't handle postscript!)
    default_lpr = 'PRN'

    # Used the 'enhanced' option of postscript by default?  Set to
    # None (*not* 0!) if your version of gnuplot doesn't support
    # enhanced postscript.
    prefer_enhanced_postscript = 1

# ############ End of configuration options ############################


try:
    from sys import hexversion
except ImportError:
    hexversion = 0

if hexversion >= 0x02000000:
    # Apparently at least as of Python 2.0b1, popen support for
    # windows is adequate.  Give that a try:
    from os import popen
else:
    # For earlier versions, you have to have the win32 extensions
    # installed and we use the popen that it provides.
    from win32pipe import popen


# Mac doesn't recognize persist.
def test_persist():
    return 0


class GnuplotProcess:
    """Unsophisticated interface to a running gnuplot program.

    See gp_unix.py for usage information.

    """

    def __init__(self, persist=0, quiet=False):
        """Start a gnuplot process.

        Create a 'GnuplotProcess' object.  This starts a gnuplot
        program and prepares to write commands to it.

        Keyword arguments:

            'persist' -- the '-persist' option is not supported under
                Windows so this argument must be zero.

        """

        if persist:
            raise Errors.OptionError(
                '-persist is not supported under Windows!')

        self.gnuplot = popen(GnuplotOpts.gnuplot_command, 'w')

        # forward write and flush methods:
        self.write = self.gnuplot.write
        self.flush = self.gnuplot.flush

    def close(self):
        if self.gnuplot is not None:
            self.gnuplot.close()
            self.gnuplot = None

    def __del__(self):
        self.close()

    def __call__(self, s):
        """Send a command string to gnuplot, followed by newline."""

        self.write(s + '\n')
        self.flush()

# Should work with Python3 and Python2
