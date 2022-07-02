# $Id$

# Copyright (C) 1999-2003 Michael Haggerty <mhagger@alum.mit.edu>
# Thanks to Tony Ingraldi and Noboru Yamamoto for their contributions.
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""gp_mac -- an interface to gnuplot for the Macintosh.

"""

import os, string

from . import Errors


# ############ Configuration variables: ################################

class GnuplotOpts:
    """The configuration options for gnuplot on the Macintosh.

    See gp.py for details about the meaning of these options.  Please
    let me know if you know better choices for these settings."""

    # The '-persist' option is not supported on the Mac:
    recognizes_persist = 0

    # Apparently the Mac can use binary data:
    recognizes_binary_splot = 1

    # Apparently the Mac can not use inline data:
    prefer_inline_data = 0

    # os.mkfifo is not supported on the Mac.
    support_fifo = 0
    prefer_fifo_data = 0

    # The default choice for the 'set term' command (to display on screen).
    # Terminal types are different in Gnuplot 3.7.1c.
    # For earlier versions, this was default_term = 'macintosh'
    default_term = 'pict'

    # I don't know how to print directly to a printer on the Mac:
    default_lpr = '| lpr'

    # Used the 'enhanced' option of postscript by default?  Set to
    # None (*not* 0!) if your version of gnuplot doesn't support
    # enhanced postscript.
    prefer_enhanced_postscript = 1

# ############ End of configuration options ############################


# The Macintosh doesn't support pipes so communication is via
# AppleEvents.

from . import gnuplot_Suites
import Required_Suite
import aetools


# Mac doesn't recognize persist.
def test_persist():
    return 0


class _GNUPLOT(aetools.TalkTo,
               Required_Suite.Required_Suite,
               gnuplot_Suites.gnuplot_Suite,
               gnuplot_Suites.odds_and_ends,
               gnuplot_Suites.Standard_Suite,
               gnuplot_Suites.Miscellaneous_Events):
    """Start a gnuplot program and emulate a pipe to it."""

    def __init__(self):
        aetools.TalkTo.__init__(self, '{GP}', start=1)


class GnuplotProcess:
    """Unsophisticated interface to a running gnuplot program.

    See gp_unix.GnuplotProcess for usage information.

    """

    def __init__(self, persist=0, quiet=False):
        """Start a gnuplot process.

        Create a 'GnuplotProcess' object.  This starts a gnuplot
        program and prepares to write commands to it.

        Keyword arguments:

          'persist' -- the '-persist' option is not supported on the
                       Macintosh so this argument must be zero.

        """

        if persist:
            raise Errors.OptionError(
                '-persist is not supported on the Macintosh!')

        self.gnuplot = _GNUPLOT()

    def close(self):
        if self.gnuplot is not None:
            self.gnuplot.quit()
            self.gnuplot = None

    def __del__(self):
        self.close()

    def write(self, s):
        """Mac gnuplot apparently requires '\r' to end statements."""

        self.gnuplot.gnuexec(string.replace(s, '\n', os.linesep))

    def flush(self):
        pass

    def __call__(self, s):
        """Send a command string to gnuplot, for immediate execution."""

        # Apple Script doesn't seem to need the trailing '\n'.
        self.write(s)
        self.flush()

# Should work with Python3 and Python2
