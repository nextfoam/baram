#! /usr/bin/env python
# $Id: demo.py 299 2007-03-30 12:52:17Z mhagger $

# Copyright (C) 1999-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""demo.py -- Demonstrate the Gnuplot python module.

Run this demo by typing 'python demo.py'.  For a more complete test of
the Gnuplot package, see test.py.

"""

from numpy import *

# If the package has been installed correctly, this should work:
from PyFoam.ThirdParty import Gnuplot
from PyFoam.ThirdParty.Gnuplot import funcutils

from PyFoam.ThirdParty.six.moves import input as rinput

def demo():
    """Demonstrate the Gnuplot package."""

    # A straightforward use of gnuplot.  The `debug=1' switch is used
    # in these examples so that the commands that are sent to gnuplot
    # are also output on stderr.
    g = Gnuplot.Gnuplot(debug=1)
    g.title('A simple example') # (optional)
    g('set style data linespoints') # give gnuplot an arbitrary command
    # Plot a list of (x, y) pairs (tuples or a numpy array would
    # also be OK):
    g.plot([[0,1.1], [1,5.8], [2,3.3], [3,4.2]])
    rinput('Please press return to continue...\n')

    g.reset()
    # Plot one dataset from an array and one via a gnuplot function;
    # also demonstrate the use of item-specific options:
    try:
        x = arange(10, dtype='float_')
    except TypeError:
        x = arange(10, typecode='d')

    y1 = x**2
    # Notice how this plotitem is created here but used later?  This
    # is convenient if the same dataset has to be plotted multiple
    # times.  It is also more efficient because the data need only be
    # written to a temporary file once.
    d = Gnuplot.Data(x, y1,
                     title='calculated by python',
                     with_='points pt 3 ps 3')
    g.title('Data can be computed by python or gnuplot')
    g.xlabel('x')
    g.ylabel('x squared')
    # Plot a function alongside the Data PlotItem defined above:
    g.plot(Gnuplot.Func('x**2', title='calculated by gnuplot'), d)
    rinput('Please press return to continue...\n')

    # Save what we just plotted as a color postscript file.

    # With the enhanced postscript option, it is possible to show `x
    # squared' with a superscript (plus much, much more; see `help set
    # term postscript' in the gnuplot docs).  If your gnuplot doesn't
    # support enhanced mode, set `enhanced=0' below.
    g.ylabel('x^2') # take advantage of enhanced postscript mode
    g.hardcopy('gp_test.ps', enhanced=1, color=1)
    print ('\n******** Saved plot to postscript file "gp_test.ps" ********\n')
    rinput('Please press return to continue...\n')

    g.reset()
    # Demonstrate a 3-d plot:
    # set up x and y values at which the function will be tabulated:
    x = arange(35)/2.0
    y = arange(30)/10.0 - 1.5
    # Make a 2-d array containing a function of x and y.  First create
    # xm and ym which contain the x and y values in a matrix form that
    # can be `broadcast' into a matrix of the appropriate shape:
    xm = x[:,newaxis]
    ym = y[newaxis,:]
    m = (sin(xm) + 0.1*xm) - ym**2
    g('set parametric')
    g('set style data lines')
    g('set hidden')
    g('set contour base')
    g.title('An example of a surface plot')
    g.xlabel('x')
    g.ylabel('y')
    # The `binary=1' option would cause communication with gnuplot to
    # be in binary format, which is considerably faster and uses less
    # disk space.  (This only works with the splot command due to
    # limitations of gnuplot.)  `binary=1' is the default, but here we
    # disable binary because older versions of gnuplot don't allow
    # binary data.  Change this to `binary=1' (or omit the binary
    # option) to get the advantage of binary format.
    g.splot(Gnuplot.GridData(m,x,y, binary=0))
    rinput('Please press return to continue...\n')

    # plot another function, but letting GridFunc tabulate its values
    # automatically.  f could also be a lambda or a global function:
    def f(x,y):
        return 1.0 / (1 + 0.01 * x**2 + 0.5 * y**2)

    g.splot(Gnuplot.funcutils.compute_GridData(x,y, f, binary=0))
    rinput('Please press return to continue...\n')

    # Explicit delete shouldn't be necessary, but if you are having
    # trouble with temporary files being left behind, try uncommenting
    # the following:
    #del g, d


# when executed, just run demo():
if __name__ == '__main__':
    demo()

# Should work with Python3 and Python2
