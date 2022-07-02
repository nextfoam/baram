# $Id$

# Copyright (C) 1998-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""gp_macosx -- an interface to the command line version of gnuplot
used under Mac OS X.

The only difference between this interface and gp_unix is that
default_term is 'aqua'.

This file implements a low-level interface to gnuplot.  This file
should be imported through gp.py, which in turn should be imported via
'import Gnuplot' rather than using these low-level interfaces
directly.

"""

# ############ Configuration variables: ################################

class GnuplotOpts:
    """The configuration options for gnuplot on Mac OS X.

    See the gp_unix.py for documentation on all of the parameters.

    """

    gnuplot_command = 'gnuplot'
    recognizes_persist = None # test automatically on first use
    prefer_persist = 0
    recognizes_binary_splot = 1
    prefer_inline_data = 0

    # os.mkfifo should be supported on Mac OS X.  Let me know if I'm
    # wrong.
    support_fifo = 1
    prefer_fifo_data = 1

    default_term = 'aqua'
    default_lpr = '| lpr'
    prefer_enhanced_postscript = 1

# ############ End of configuration options ############################

from os import popen


def test_persist():
    """Determine whether gnuplot recognizes the option '-persist'.

    If the configuration variable 'recognizes_persist' is set (i.e.,
    to something other than 'None'), return that value.  Otherwise,
    try to determine whether the installed version of gnuplot
    recognizes the -persist option.  (If it doesn't, it should emit an
    error message with '-persist' in the first line.)  Then set
    'recognizes_persist' accordingly for future reference.

    """

    if GnuplotOpts.recognizes_persist is None:
        import string
        g = popen('echo | %s -persist 2>&1' % GnuplotOpts.gnuplot_command, 'r')
        response = g.readlines()
        g.close()
        GnuplotOpts.recognizes_persist = (
            (not response) or (string.find(response[0], '-persist') == -1))
    return GnuplotOpts.recognizes_persist


class GnuplotProcess:
    """Unsophisticated interface to a running gnuplot program.

    This represents a running gnuplot program and the means to
    communicate with it at a primitive level (i.e., pass it commands
    or data).  When the object is destroyed, the gnuplot program exits
    (unless the 'persist' option was set).  The communication is
    one-way; gnuplot's text output just goes to stdout with no attempt
    to check it for error messages.

    Members:

        'gnuplot' -- the pipe to the gnuplot command.

    Methods:

        '__init__' -- start up the program.

        '__call__' -- pass an arbitrary string to the gnuplot program,
            followed by a newline.

        'write' -- pass an arbitrary string to the gnuplot program.

        'flush' -- cause pending output to be written immediately.

        'close' -- close the connection to gnuplot.

    """

    def __init__(self, persist=None, quiet=False):
        """Start a gnuplot process.

        Create a 'GnuplotProcess' object.  This starts a gnuplot
        program and prepares to write commands to it.

        Keyword arguments:

          'persist=1' -- start gnuplot with the '-persist' option,
              (which leaves the plot window on the screen even after
              the gnuplot program ends, and creates a new plot window
              each time the terminal type is set to 'x11').  This
              option is not available on older versions of gnuplot.

        """

        if persist is None:
            persist = GnuplotOpts.prefer_persist
        if persist:
            if not test_persist():
                raise Exception('-persist does not seem to be supported '
                                'by your version of gnuplot!')
            self.gnuplot = popen('%s -persist' % GnuplotOpts.gnuplot_command,
                                 'w')
        else:
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
