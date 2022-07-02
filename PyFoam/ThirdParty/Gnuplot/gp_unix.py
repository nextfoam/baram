# $Id: gp_unix.py,v 2d3659384189 2020-02-27 10:48:04Z bgschaid $

# Copyright (C) 1998-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""gp_unix -- an interface to gnuplot used for unix platforms.

This file implements a low-level interface to a gnuplot program for a
unix platform (actually it is used for any non-Windows, non-Mac
system).  This file should be imported through gp.py, which in turn
should be imported via 'import Gnuplot' rather than these low-level
interfaces.

"""

from PyFoam.ThirdParty.six import PY3

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

    # Command to start up the gnuplot program.  If your version of
    # gnuplot is run otherwise, specify the correct command here.  You
    # could also specify a full path or append command-line options
    # here if you wish.
    gnuplot_command = 'gnuplot'

    # Recent versions of gnuplot (at least for Xwindows) allow a
    # `-persist' command-line option when starting up gnuplot.  When
    # this option is specified, graph windows remain on the screen
    # even after you quit gnuplot (type `q' in the window to close
    # it).  This can be handy but unfortunately it is not supported by
    # older versions of gnuplot.  The following configuration variable
    # specifies whether the user's version of gnuplot recognizes this
    # option or not.  You can set this variable to 1 (supports
    # -persist) or 0 (doesn't support) yourself; if you leave it with
    # the value None then the first time you create a Gnuplot object
    # it will try to detect automatically whether your version accepts
    # this option.
    recognizes_persist = None # test automatically on first use

    # What should be the default if the persist option is not
    # specified explicitly?
    prefer_persist = 0

    # Recent versions of gnuplot allow you to specify a `binary'
    # option to the splot command for grid data, which means that the
    # data file is to be read in binary format.  This option saves
    # substantial time writing and reading the file, and can also save
    # substantial disk space and therefore it is the default for that
    # type of plot.  But if you have an older version of gnuplot (or
    # you prefer text format) you can disable the binary option in
    # either of two ways: (a) set the following variable to 0; or (b)
    # pass `binary=0' to the GridData constructor.  (Note that the
    # demo uses binary=0 to maximize portability.)
    recognizes_binary_splot = 1

    # Data can be passed to gnuplot through a temporary file or as
    # inline data (i.e., the filename is set to '-' and the data is
    # entered into the gnuplot interpreter followed by 'e').  If
    # prefer_inline_data is true, then use the inline method as
    # default whenever it is supported.  This should be fast but will
    # use more memory since currently the inline data is put into a
    # big string when the PlotItem is created.
    prefer_inline_data = 0

    # Does Python implement the threading module and os.mkfifo on this
    # operating system?  If so, the _FIFOFileItem class will be
    # defined in PlotItem.py.
    support_fifo = 1

    # Should FIFOs be used to send data to gnuplot by default?
    prefer_fifo_data = 1

    # After a hardcopy is produced, we have to set the terminal type
    # back to `on screen' using gnuplot's `set terminal' command.  The
    # following is the usual setting for Xwindows.  If it is wrong,
    # change the following line to select the terminal type you prefer
    # to use for on-screen work.
    default_term = 'x11'

    # Gnuplot can plot to a printer by using "set output '| ...'"
    # where ... is the name of a program that sends its stdin to a
    # printer, or by "set output 'printer_device', where
    # 'printer_device is the name of a file-like interface to the
    # printer.  On my machine the appropriate program is `lpr', as set
    # below.  On your computer it may be something different (like
    # `lp'); you can set that by changing the variable below.  You can
    # also add options to the print command if needed.
    default_lpr = '| lpr'

    # Enhanced postscript is an option to the postscript terminal
    # driver that requests enhanced treatment of strings (for example,
    # font changes, superscripts, and subscripts).  Set to 1 to enable
    # or 0 to disable.  If you have a version of gnuplot earlier than
    # 3.7, you should set this to None (*not* 0!) so that the option
    # is not used at all.
    prefer_enhanced_postscript = 1

# ############ End of configuration options ############################

from os import popen
import subprocess

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

        self.out = None
        if persist is None:
            persist = GnuplotOpts.prefer_persist
        if persist:
            if not test_persist():
                raise Exception('-persist does not seem to be supported '
                                'by your version of gnuplot!')
            cmd = '%s -persist' % GnuplotOpts.gnuplot_command
        else:
            cmd = GnuplotOpts.gnuplot_command

        if quiet:
            p = subprocess.Popen(cmd, shell=True, bufsize=-1,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, close_fds=True)
            self.gnuplot, self.out = (p.stdin, p.stdout)
        else:
            self.gnuplot, self.out = popen(cmd, "w"), None

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

        s += "\n"

        if PY3:
            s = s.encode()

        try:
            self.write(s)
        except TypeError:
            self.write(s.decode())

        self.flush()

# Should work with Python3 and Python2
