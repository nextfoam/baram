# $Id$

# Copyright (C) 2002-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""gp_java -- an interface to gnuplot used under Jython/Java.

This file implements a low-level interface to a gnuplot program run
via Jython/Java.  This file should be imported through gp.py, which in
turn should be imported via 'import Gnuplot' rather than these
low-level interfaces.

"""

# ############ Configuration variables: ################################

class GnuplotOpts:
    """The configuration options for gnuplot on generic platforms.

    Store the options in a class to make them easy to import and
    modify en masse.  If you want to modify the options from the
    command line or within a running program, do something like the
    following::

        import Gnuplot
        Gnuplot.GnuplotOpts.gnuplot_command = '/bin/mygnuplot'

    """

    gnuplot_command = 'gnuplot'
    recognizes_persist = 1
    prefer_persist = 0
    recognizes_binary_splot = 1
    prefer_inline_data = 0
    support_fifo = 0
    prefer_fifo_data = 0
    default_term = 'x11'
    default_lpr = '| lpr'
    prefer_enhanced_postscript = 1

# ############ End of configuration options ############################

import sys

from java.lang import Thread
from java.lang import Runtime


def test_persist():
    """Determine whether gnuplot recognizes the option '-persist'.

    """

    return GnuplotOpts.recognizes_persist


class OutputProcessor(Thread):
    """In a separate thread, read from one InputStream and output to a file.

    """

    def __init__(self, name, input, output):
        self.input = input
        self.output = output

        Thread.__init__(self, name)
        self.setDaemon(1)

    def run(self):
        while 1:
            self.output.write(chr(self.input.read()))


class GnuplotProcess:
    """Unsophisticated interface to a running gnuplot program.

    This represents a running gnuplot program and the means to
    communicate with it at a primitive level (i.e., pass it commands
    or data).  When the object is destroyed, the gnuplot program exits
    (unless the 'persist' option was set).  The communication is
    one-way; gnuplot's text output just goes to stdout with no attempt
    to check it for error messages.

    Members:


    Methods:

        '__init__' -- start up the program.

        '__call__' -- pass an arbitrary string to the gnuplot program,
            followed by a newline.

        'write' -- pass an arbitrary string to the gnuplot program.

        'flush' -- cause pending output to be written immediately.

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
        command = [GnuplotOpts.gnuplot_command]
        if persist:
            if not test_persist():
                raise Exception('-persist does not seem to be supported '
                                'by your version of gnuplot!')
            command.append('-persist')

        # This is a kludge: distutils wants to import everything it
        # sees when making a distribution, and if we just call exec()
        # normally that causes a SyntaxError in CPython because "exec"
        # is a keyword.  Therefore, we call the exec() method
        # indirectly.
        #self.process = Runtime.getRuntime().exec(command)
        exec_method = getattr(Runtime.getRuntime(), 'exec')
        self.process = exec_method(command)

        self.outprocessor = OutputProcessor(
            'gnuplot standard output processor',
            self.process.getInputStream(), sys.stdout
            )
        self.outprocessor.start()
        self.errprocessor = OutputProcessor(
            'gnuplot standard error processor',
            self.process.getErrorStream(), sys.stderr
            )
        self.errprocessor.start()

        self.gnuplot = self.process.getOutputStream()

    def close(self):
        # ### Does this close the gnuplot process under Java?
        if self.gnuplot is not None:
            self.gnuplot.close()
            self.gnuplot = None

    def __del__(self):
        self.close()

    def write(self, s):
        self.gnuplot.write(s)

    def flush(self):
        self.gnuplot.flush()

    def __call__(self, s):
        """Send a command string to gnuplot, followed by newline."""

        self.write(s + '\n')
        self.flush()

# Should work with Python3 and Python2
