#! /usr/bin/env python

# $Id: test.py 302 2008-01-14 22:15:19Z bmcage $

# Copyright (C) 1999-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""test.py -- Exercise the Gnuplot.py module.

This module is not meant to be a flashy demonstration; rather it is a
thorough test of many combinations of Gnuplot.py features.

"""

import os, time, math, tempfile
try:
    import numpy
except ImportError:
    # assume this is pypy and retry
    import numpypy
    import numpy

from PyFoam.ThirdParty.six import print_
from PyFoam.ThirdParty.six.moves import input as rinput

try:
    from PyFoam.ThirdParty import Gnuplot
    from PyFoam.ThirdParty.Gnuplot import PlotItems
    from PyFoam.ThirdParty.Gnuplot import funcutils
    Gnuplot.funcutils = funcutils
except ImportError:
    # kludge in case Gnuplot hasn't been installed as a module yet:
    from . import __init__
    Gnuplot = __init__
    from . import PlotItems
    Gnuplot.PlotItems = PlotItems
    from . import funcutils
    Gnuplot.funcutils = funcutils


def wait(str=None, prompt='Press return to show results...\n'):
    if str is not None:
        print_(str)
        #    rinput(prompt)


def main():
    """Exercise the Gnuplot module."""

    print_ (
        'This program exercises many of the features of Gnuplot.py.  The\n'
        'commands that are actually sent to gnuplot are printed for your\n'
        'enjoyment.'
        )

    wait('Popping up a blank gnuplot window on your screen.')
    g = Gnuplot.Gnuplot(debug=1)
    g.clear()

    # Make two temporary files:
    if hasattr(tempfile, 'mkstemp'):
        (fd, filename1,) = tempfile.mkstemp(text=1)
        f = os.fdopen(fd, 'w')
        (fd, filename2,) = tempfile.mkstemp(text=1)
    else:
        filename1 = tempfile.mktemp()
        f = open(filename1, 'w')
        filename2 = tempfile.mktemp()
    try:
        for x in numpy.arange(100.)/5. - 10.:
            f.write('%s %s %s\n' % (x, math.cos(x), math.sin(x)))
        f.close()

        print_('############### test Func ###################################')
        wait('Plot a gnuplot-generated function')
        g.plot(Gnuplot.Func('sin(x)'))

        wait('Set title and axis labels and try replot()')
        g.title('Title')
        g.xlabel('x')
        g.ylabel('y')
        g.replot()

        wait('Style linespoints')
        g.plot(Gnuplot.Func('sin(x)', with_='linespoints'))
        wait('title=None')
        g.plot(Gnuplot.Func('sin(x)', title=None))
        wait('title="Sine of x"')
        g.plot(Gnuplot.Func('sin(x)', title='Sine of x'))
        wait('axes=x2y2')
        g.plot(Gnuplot.Func('sin(x)', axes='x2y2', title='Sine of x'))

        print_('Change Func attributes after construction:')
        f = Gnuplot.Func('sin(x)')
        wait('Original')
        g.plot(f)
        wait('Style linespoints')
        f.set_option(with_='linespoints')
        g.plot(f)
        wait('title=None')
        f.set_option(title=None)
        g.plot(f)
        wait('title="Sine of x"')
        f.set_option(title='Sine of x')
        g.plot(f)
        wait('axes=x2y2')
        f.set_option(axes='x2y2')
        g.plot(f)

        print_('############### test File ###################################')
        wait('Generate a File from a filename')
        g.plot(Gnuplot.File(filename1))

        wait('Style lines')
        g.plot(Gnuplot.File(filename1, with_='lines'))

        wait('using=1, using=(1,)')
        g.plot(Gnuplot.File(filename1, using=1, with_='lines'),
               Gnuplot.File(filename1, using=(1,), with_='points'))
        wait('using=(1,2), using="1:3"')
        g.plot(Gnuplot.File(filename1, using=(1,2)),
               Gnuplot.File(filename1, using='1:3'))

        wait('every=5, every=(5,)')
        g.plot(Gnuplot.File(filename1, every=5, with_='lines'),
               Gnuplot.File(filename1, every=(5,), with_='points'))
        wait('every=(10,None,0), every="10::5"')
        g.plot(Gnuplot.File(filename1, with_='lines'),
               Gnuplot.File(filename1, every=(10,None,0)),
               Gnuplot.File(filename1, every='10::5'))

        wait('title=None')
        g.plot(Gnuplot.File(filename1, title=None))
        wait('title="title"')
        g.plot(Gnuplot.File(filename1, title='title'))

        print_('Change File attributes after construction:')
        f = Gnuplot.File(filename1)
        wait('Original')
        g.plot(f)
        wait('Style linespoints')
        f.set_option(with_='linespoints')
        g.plot(f)
        wait('using=(1,3)')
        f.set_option(using=(1,3))
        g.plot(f)
        wait('title=None')
        f.set_option(title=None)
        g.plot(f)

        print_('############### test Data ###################################')
        x = numpy.arange(100)/5. - 10.
        y1 = numpy.cos(x)
        y2 = numpy.sin(x)
        d = numpy.transpose((x,y1,y2))

        wait('Plot Data against its index')
        g.plot(Gnuplot.Data(y2, inline=0))

        wait('Plot Data, specified column-by-column')
        g.plot(Gnuplot.Data(x,y2, inline=0))
        wait('Same thing, saved to a file')
        Gnuplot.Data(x,y2, inline=0, filename=filename1)
        g.plot(Gnuplot.File(filename1))
        wait('Same thing, inline data')
        g.plot(Gnuplot.Data(x,y2, inline=1))

        wait('Plot Data, specified by an array')
        g.plot(Gnuplot.Data(d, inline=0))
        wait('Same thing, saved to a file')
        Gnuplot.Data(d, inline=0, filename=filename1)
        g.plot(Gnuplot.File(filename1))
        wait('Same thing, inline data')
        g.plot(Gnuplot.Data(d, inline=1))
        wait('with_="lp lw 4 ps 4"')
        g.plot(Gnuplot.Data(d, with_='lp lw 4 ps 4'))
        wait('cols=0')
        g.plot(Gnuplot.Data(d, cols=0))
        wait('cols=(0,1), cols=(0,2)')
        g.plot(Gnuplot.Data(d, cols=(0,1), inline=0),
               Gnuplot.Data(d, cols=(0,2), inline=0))
        wait('Same thing, saved to files')
        Gnuplot.Data(d, cols=(0,1), inline=0, filename=filename1)
        Gnuplot.Data(d, cols=(0,2), inline=0, filename=filename2)
        g.plot(Gnuplot.File(filename1), Gnuplot.File(filename2))
        wait('Same thing, inline data')
        g.plot(Gnuplot.Data(d, cols=(0,1), inline=1),
               Gnuplot.Data(d, cols=(0,2), inline=1))
        wait('Change title and replot()')
        g.title('New title')
        g.replot()
        wait('title=None')
        g.plot(Gnuplot.Data(d, title=None))
        wait('title="Cosine of x"')
        g.plot(Gnuplot.Data(d, title='Cosine of x'))

        print_('############### test compute_Data ###########################')
        x = numpy.arange(100)/5. - 10.

        wait('Plot Data, computed by Gnuplot.py')
        g.plot(
            Gnuplot.funcutils.compute_Data(x, lambda x: math.cos(x), inline=0)
            )
        wait('Same thing, saved to a file')
        Gnuplot.funcutils.compute_Data(
            x, lambda x: math.cos(x), inline=0, filename=filename1
            )
        g.plot(Gnuplot.File(filename1))
        wait('Same thing, inline data')
        g.plot(Gnuplot.funcutils.compute_Data(x, math.cos, inline=1))
        wait('with_="lp 4 4"')
        g.plot(Gnuplot.funcutils.compute_Data(x, math.cos, with_='lp 4 4'))

        print_('############### test hardcopy ###############################')
        print_('******** Generating postscript file "gp_test.ps" ********')
        wait()
        g.plot(Gnuplot.Func('cos(0.5*x*x)', with_='linespoints lw 2 ps 2',
                       title='cos(0.5*x^2)'))
        g.hardcopy('gp_test.ps')

        wait('Testing hardcopy options: mode="eps"')
        g.hardcopy('gp_test.ps', mode='eps')
        wait('Testing hardcopy options: mode="landscape"')
        g.hardcopy('gp_test.ps', mode='landscape')
        wait('Testing hardcopy options: mode="portrait"')
        g.hardcopy('gp_test.ps', mode='portrait')
        wait('Testing hardcopy options: eps=1')
        g.hardcopy('gp_test.ps', eps=1)
        wait('Testing hardcopy options: mode="default"')
        g.hardcopy('gp_test.ps', mode='default')
        wait('Testing hardcopy options: enhanced=1')
        g.hardcopy('gp_test.ps', enhanced=1)
        wait('Testing hardcopy options: enhanced=0')
        g.hardcopy('gp_test.ps', enhanced=0)
        wait('Testing hardcopy options: color=1')
        g.hardcopy('gp_test.ps', color=1)
        # For some reason,
        #    g.hardcopy('gp_test.ps', color=0, solid=1)
        # doesn't work here (it doesn't activate the solid option), even
        # though the command sent to gnuplot looks correct.  I'll
        # tentatively conclude that it is a gnuplot bug. ###
        wait('Testing hardcopy options: color=0')
        g.hardcopy('gp_test.ps', color=0)
        wait('Testing hardcopy options: solid=1')
        g.hardcopy('gp_test.ps', solid=1)
        wait('Testing hardcopy options: duplexing="duplex"')
        g.hardcopy('gp_test.ps', solid=0, duplexing='duplex')
        wait('Testing hardcopy options: duplexing="defaultplex"')
        g.hardcopy('gp_test.ps', duplexing='defaultplex')
        wait('Testing hardcopy options: fontname="Times-Italic"')
        g.hardcopy('gp_test.ps', fontname='Times-Italic')
        wait('Testing hardcopy options: fontsize=20')
        g.hardcopy('gp_test.ps', fontsize=20)

        print_('******** Generating svg file "gp_test.svg" ********')
        wait()
        g.plot(Gnuplot.Func('cos(0.5*x*x)', with_='linespoints lw 2 ps 2',
                       title='cos(0.5*x^2)'))
        g.hardcopy('gp_test.svg', terminal='svg')

        wait('Testing hardcopy svg options: enhanced')
        g.hardcopy('gp_test.ps', terminal='svg', enhanced='1')


        print_('############### test shortcuts ##############################')
        wait('plot Func and Data using shortcuts')
        g.plot('sin(x)', d)

        print_('############### test splot ##################################')
        wait('a 3-d curve')
        g.splot(Gnuplot.Data(d, with_='linesp', inline=0))
        wait('Same thing, saved to a file')
        Gnuplot.Data(d, inline=0, filename=filename1)
        g.splot(Gnuplot.File(filename1, with_='linesp'))
        wait('Same thing, inline data')
        g.splot(Gnuplot.Data(d, with_='linesp', inline=1))

        print_('############### test GridData and compute_GridData ##########')
        # set up x and y values at which the function will be tabulated:
        x = numpy.arange(35)/2.0
        y = numpy.arange(30)/10.0 - 1.5
        # Make a 2-d array containing a function of x and y.  First create
        # xm and ym which contain the x and y values in a matrix form that
        # can be `broadcast' into a matrix of the appropriate shape:
        xm = x[:,numpy.newaxis]
        ym = y[numpy.newaxis,:]
        m = (numpy.sin(xm) + 0.1*xm) - ym**2
        wait('a function of two variables from a GridData file')
        g('set parametric')
        g('set style data lines')
        g('set hidden')
        g('set contour base')
        g.xlabel('x')
        g.ylabel('y')
        g.splot(Gnuplot.GridData(m,x,y, binary=0, inline=0))
        wait('Same thing, saved to a file')
        Gnuplot.GridData(m,x,y, binary=0, inline=0, filename=filename1)
        g.splot(Gnuplot.File(filename1, binary=0))
        wait('Same thing, inline data')
        g.splot(Gnuplot.GridData(m,x,y, binary=0, inline=1))

        wait('The same thing using binary mode')
        g.splot(Gnuplot.GridData(m,x,y, binary=1))
        wait('Same thing, using binary mode and an intermediate file')
        Gnuplot.GridData(m,x,y, binary=1, filename=filename1)
        g.splot(Gnuplot.File(filename1, binary=1))

        wait('The same thing using compute_GridData to tabulate function')
        g.splot(Gnuplot.funcutils.compute_GridData(
            x,y, lambda x,y: math.sin(x) + 0.1*x - y**2,
            ))
        wait('Same thing, with an intermediate file')
        Gnuplot.funcutils.compute_GridData(
            x,y, lambda x,y: math.sin(x) + 0.1*x - y**2,
            filename=filename1)
        g.splot(Gnuplot.File(filename1, binary=1))

        wait('Use compute_GridData in ufunc and binary mode')
        g.splot(Gnuplot.funcutils.compute_GridData(
            x,y, lambda x,y: numpy.sin(x) + 0.1*x - y**2,
            ufunc=1, binary=1,
            ))
        wait('Same thing, with an intermediate file')
        Gnuplot.funcutils.compute_GridData(
            x,y, lambda x,y: numpy.sin(x) + 0.1*x - y**2,
            ufunc=1, binary=1,
            filename=filename1)
        g.splot(Gnuplot.File(filename1, binary=1))

        wait('And now rotate it a bit')
        for view in range(35,70,5):
            g('set view 60, %d' % view)
            g.replot()
            time.sleep(1.0)

        wait(prompt='Press return to end the test.\n')
    finally:
        os.unlink(filename1)
        os.unlink(filename2)


# when executed, just run main():
if __name__ == '__main__':
    main()

# Should work with Python3 and Python2
