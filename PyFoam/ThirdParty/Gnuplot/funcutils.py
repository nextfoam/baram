#! /usr/bin/env python

# $Id: funcutils.py 297 2007-03-30 11:25:28Z mhagger $

# Copyright (C) 1998-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""funcutils.py -- Subroutines that tabulate a function's values.

Convenience functions that evaluate a python function on a grid of
points and tabulate the output to be used with Gnuplot.

"""

try:
    import numpy
except ImportError:
    # assume this is pypy and retry
    import numpypy
    import numpy

from . import Gnuplot, utils, PlotItems


def tabulate_function(f, xvals, yvals=None, dtype=None, ufunc=0):
    """Evaluate and tabulate a function on a 1- or 2-D grid of points.

    f should be a function taking one or two floating-point
    parameters.

    If f takes one parameter, then xvals should be a 1-D array and
    yvals should be None.  The return value is a numpy array
    '[f(x[0]), f(x[1]), ..., f(x[-1])]'.

    If f takes two parameters, then 'xvals' and 'yvals' should each be
    1-D arrays listing the values of x and y at which 'f' should be
    tabulated.  The return value is a matrix M where 'M[i,j] =
    f(xvals[i],yvals[j])', which can for example be used in the
    'GridData' constructor.

    If 'ufunc=0', then 'f' is evaluated at each point using a Python
    loop.  This can be slow if the number of points is large.  If
    speed is an issue, you should write 'f' in terms of numpy ufuncs
    and use the 'ufunc=1' feature described next.

    If called with 'ufunc=1', then 'f' should be a function that is
    composed entirely of ufuncs (i.e., a function that can operate
    element-by-element on whole matrices).  It will be passed the
    xvals and yvals as rectangular matrices.

    """

    if yvals is None:
        # f is a function of only one variable:
        xvals = numpy.asarray(xvals, dtype)

        if ufunc:
            return f(xvals)
        else:
            if dtype is None:
                try:
                    dtype = xvals.dtype.char
                except AttributeError:
                    dtype = xvals.typecode()

            m = numpy.zeros((len(xvals),), dtype)
            for xi in range(len(xvals)):
                x = xvals[xi]
                m[xi] = f(x)
            return m
    else:
        # f is a function of two variables:
        xvals = numpy.asarray(xvals, dtype)
        yvals = numpy.asarray(yvals, dtype)

        if ufunc:
            return f(xvals[:,numpy.newaxis], yvals[numpy.newaxis,:])
        else:
            if dtype is None:
                # choose a result dtype based on what '+' would return
                # (yecch!):

                try:
                    dtype = (numpy.zeros((1,), xvals.dtype.char) +
                             numpy.zeros((1,), yvals.dtype.char)).dtype.char
                except AttributeError:
                    dtype = (numpy.zeros((1,), xvals.typecode()) +
                             numpy.zeros((1,), xvals.typecode())).typecode()

            m = numpy.zeros((len(xvals), len(yvals)), dtype)
            for xi in range(len(xvals)):
                x = xvals[xi]
                for yi in range(len(yvals)):
                    y = yvals[yi]
                    m[xi,yi] = f(x,y)
            return m


# For backwards compatibility:
grid_function = tabulate_function


def compute_Data(xvals, f, ufunc=0, **keyw):
    """Evaluate a function of 1 variable and store the results in a Data.

    Computes a function f of one variable on a set of specified points
    using 'tabulate_function', then store the results into a 'Data' so
    that it can be plotted.  After calculation, the data are written
    to a file; no copy is kept in memory.  Note that this is quite
    different than 'Func' (which tells gnuplot to evaluate the
    function).

    Arguments:

        'xvals' -- a 1-d array with dimension 'numx'

        'f' -- the function to plot--a callable object for which
            f(x) returns a number.

        'ufunc=<bool>' -- evaluate 'f' as a ufunc?

    Other keyword arguments are passed through to the Data
    constructor.

    'f' should be a callable object taking one argument.  'f(x)' will
    be computed at all values in xvals.

    If called with 'ufunc=1', then 'f' should be a function that is
    composed entirely of ufuncs, and it will be passed the 'xvals' and
    'yvals' as rectangular matrices.

    Thus if you have a function 'f', a vector 'xvals', and a Gnuplot
    instance called 'g', you can plot the function by typing
    'g.splot(compute_Data(xvals, f))'.

    """

    xvals = utils.float_array(xvals)

    # evaluate function:
    data = tabulate_function(f, xvals, ufunc=ufunc)

    return PlotItems.Data(xvals, data, **keyw)


def compute_GridData(xvals, yvals, f, ufunc=0, **keyw):
    """Evaluate a function of 2 variables and store the results in a GridData.

    Computes a function 'f' of two variables on a rectangular grid
    using 'tabulate_function', then store the results into a
    'GridData' so that it can be plotted.  After calculation the data
    are written to a file; no copy is kept in memory.  Note that this
    is quite different than 'Func' (which tells gnuplot to evaluate
    the function).

    Arguments:

        'xvals' -- a 1-d array with dimension 'numx'

        'yvals' -- a 1-d array with dimension 'numy'

        'f' -- the function to plot--a callable object for which
            'f(x,y)' returns a number.

        'ufunc=<bool>' -- evaluate 'f' as a ufunc?

     Other keyword arguments are passed to the 'GridData' constructor.

    'f' should be a callable object taking two arguments.
    'f(x,y)' will be computed at all grid points obtained by
    combining elements from 'xvals' and 'yvals'.

    If called with 'ufunc=1', then 'f' should be a function that is
    composed entirely of ufuncs, and it will be passed the 'xvals' and
    'yvals' as rectangular matrices.

    Thus if you have a function 'f' and two vectors 'xvals' and
    'yvals' and a Gnuplot instance called 'g', you can plot the
    function by typing 'g.splot(compute_GridData(f, xvals, yvals))'.

    """

    xvals = utils.float_array(xvals)
    yvals = utils.float_array(yvals)

    # evaluate function:
    data = tabulate_function(f, xvals, yvals, ufunc=ufunc)

    return PlotItems.GridData(data, xvals, yvals, **keyw)


# For backwards compatibility:
def GridFunc(f, xvals, yvals, **keyw):
    return compute_GridData(xvals, yvals, f, **keyw)

# Should work with Python3 and Python2
