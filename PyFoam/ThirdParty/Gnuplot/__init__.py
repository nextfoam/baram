#! /usr/bin/env python
# $Id: __init__.py 306 2008-05-02 01:09:02Z alford $

# Copyright (C) 1998-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""Gnuplot -- A pipe-based interface to the gnuplot plotting program.

This is the main module of the Gnuplot package.

Written by "Michael Haggerty", mailto:mhagger@alum.mit.edu.  Inspired
by and partly derived from an earlier version by "Konrad Hinsen",
mailto:hinsen@ibs.ibs.fr.  If you find a problem or have a suggestion,
please "let me know", mailto:mhagger@alum.mit.edu.  Other feedback
would also be appreciated.

The Gnuplot.py home page is at

"Gnuplot.py", http://gnuplot-py.sourceforge.net


For information about how to use this module:

1. Check the README file.

2. Look at the example code in demo.py and try running it by typing
   'python demo.py' or 'python __init__.py'.

3. For more details see the extensive documentation strings
   throughout the python source files, especially this file,
   _Gnuplot.py, PlotItems.py, and gp_unix.py.

4. The docstrings have also been turned into html which can be read
   "here", http://gnuplot-py.sourceforge.net/doc.  However, the
   formatting is not perfect; when in doubt, double-check the
   docstrings.

You should import this file with 'import Gnuplot', not with 'from
Gnuplot import *', because the module and the main class have the same
name, `Gnuplot'.

To obtain the gnuplot plotting program itself, see "the gnuplot FAQ",
ftp://ftp.gnuplot.vt.edu/pub/gnuplot/faq/index.html.  Obviously you
need to have gnuplot installed if you want to use Gnuplot.py.

The old command-based interface to gnuplot (previously supported as
'oldplot.py') has been removed from the package.

Features:

 o  Allows the creation of two or three dimensional plots from
    python.

 o  A gnuplot session is an instance of class 'Gnuplot'.  Multiple
    sessions can be open at once.  For example::

        g1 = Gnuplot.Gnuplot()
        g2 = Gnuplot.Gnuplot()

    Note that due to limitations on those platforms, opening multiple
    simultaneous sessions on Windows or Macintosh may not work
    correctly.  (Feedback?)

 o  The implicitly-generated gnuplot commands can be stored to a file
    instead of executed immediately::

        g = Gnuplot.Gnuplot('commands.txt')

    The 'commands.txt' file can then be run later with gnuplot's
    'load' command.  Beware, however: the plot commands may depend on
    the existence of temporary files, which will probably be deleted
    before you use the command file.

 o  Can pass arbitrary commands to the gnuplot command interpreter::

        g('set pointsize 2')

    (If this is all you want to do, you might consider using the
    lightweight GnuplotProcess class defined in gp.py.)

 o  A Gnuplot object knows how to plot objects of type 'PlotItem'.
    Any PlotItem can have optional 'title' and/or 'with' suboptions.
    Builtin PlotItem types:

    * 'Data(array1)' -- data from a Python list or NumPy array
                        (permits additional option 'cols' )

    * 'File('filename')' -- data from an existing data file (permits
                            additional option 'using' )

    * 'Func('exp(4.0 * sin(x))')' -- functions (passed as a string,
                                     evaluated by gnuplot)

    * 'GridData(m, x, y)' -- data tabulated on a grid of (x,y) values
                             (usually to be plotted in 3-D)

    See the documentation strings for those classes for more details.

 o  PlotItems are implemented as objects that can be assigned to
    variables and plotted repeatedly.  Most of their plot options can
    also be changed with the new 'set_option()' member functions then
    they can be replotted with their new options.

 o  Communication of commands to gnuplot is via a one-way pipe.
    Communication of data from python to gnuplot is via inline data
    (through the command pipe) or via temporary files.  Temp files are
    deleted automatically when their associated 'PlotItem' is deleted.
    The PlotItems in use by a Gnuplot object at any given time are
    stored in an internal list so that they won't be deleted
    prematurely.

 o  Can use 'replot' method to add datasets to an existing plot.

 o  Can make persistent gnuplot windows by using the constructor option
    'persist=1'.  Such windows stay around even after the gnuplot
    program is exited.  Note that only newer version of gnuplot support
    this option.

 o  Can plot either directly to a postscript printer or to a
    postscript file via the 'hardcopy' method.

 o  Grid data for the splot command can be sent to gnuplot in binary
    format, saving time and disk space.

 o  Should work under Unix, Macintosh, and Windows.

Restrictions:

 -  Relies on the numpy Python extension.  This can be obtained from
    the Scipy group at <http://www.scipy.org/Download>.  If you're
    interested in gnuplot, you would probably also want numpy anyway.

 -  Only a small fraction of gnuplot functionality is implemented as
    explicit method functions.  However, you can give arbitrary
    commands to gnuplot manually::

        g = Gnuplot.Gnuplot()
        g('set stype data linespoints')
        g('set pointsize 5')

 -  There is no provision for missing data points in array data (which
    gnuplot allows via the 'set missing' command).

Bugs:

 -  No attempt is made to check for errors reported by gnuplot.  On
    unix any gnuplot error messages simply appear on stderr.  (I don't
    know what happens under Windows.)

 -  All of these classes perform their resource deallocation when
    '__del__' is called.  Normally this works fine, but there are
    well-known cases when Python's automatic resource deallocation
    fails, which can leave temporary files around.

"""

__version__ = '1.8'

# Other modules that should be loaded for 'from Gnuplot import *':
__all__ = ['utils', 'funcutils', ]

from .gp import GnuplotOpts, GnuplotProcess, test_persist
from .Errors import Error, OptionError, DataError
from .PlotItems import PlotItem, Func, File, Data, GridData
from ._Gnuplot import Gnuplot


if __name__ == '__main__':
    from . import demo
    demo.demo()

# Should work with Python3 and Python2
