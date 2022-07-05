# $Id: PlotItems.py 299 2007-03-30 12:52:17Z mhagger $

# Copyright (C) 1998-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""PlotItems.py -- Objects that can be plotted by Gnuplot.

This module contains several types of PlotItems.  PlotItems can be
plotted by passing them to a Gnuplot.Gnuplot object.  You can derive
your own classes from the PlotItem hierarchy to customize their
behavior.

"""

import os, string, tempfile, types

from PyFoam.ThirdParty.six.moves import StringIO
from PyFoam.ThirdParty.six import string_types,integer_types

#try:
#    from cStringIO import StringIO
#except ImportError:
#    from StringIO import StringIO

try:
    import numpy
except ImportError:
    # assume this is pypy and retry
    import numpypy
    import numpy

from . import gp, utils, Errors


class _unset:
    """Used to represent unset keyword arguments."""

    pass


class PlotItem:
    """Plotitem represents an item that can be plotted by gnuplot.

    For the finest control over the output, you can create 'PlotItems'
    yourself with additional keyword options, or derive new classes
    from 'PlotItem'.

    The handling of options is complicated by the attempt to allow
    options and their setting mechanism to be inherited conveniently.
    Note first that there are some options that can only be set in the
    constructor then never modified, and others that can be set in the
    constructor and/or modified using the 'set_option()' member
    function.  The former are always processed within '__init__'.  The
    latter are always processed within 'set_option', which is called
    by the constructor.

    'set_option' is driven by a class-wide dictionary called
    '_option_list', which is a mapping '{ <option> : <setter> }' from
    option name to the function object used to set or change the
    option.  <setter> is a function object that takes two parameters:
    'self' (the 'PlotItem' instance) and the new value requested for
    the option.  If <setter> is 'None', then the option is not allowed
    to be changed after construction and an exception is raised.

    Any 'PlotItem' that needs to add options can add to this
    dictionary within its class definition.  Follow one of the
    examples in this file.  Alternatively it could override the
    'set_option' member function if it needs to do wilder things.

    Members:

      '_basecommand' -- a string holding the elementary argument that
          must be passed to gnuplot's `plot' command for this item;
          e.g., 'sin(x)' or '"filename.dat"'.

      '_options' -- a dictionary of (<option>,<string>) tuples
          corresponding to the plot options that have been set for
          this instance of the PlotItem.  <option> is the option as
          specified by the user; <string> is the string that needs to
          be set in the command line to set that option (or None if no
          string is needed).  Example::

              {'title' : ('Data', 'title "Data"'),
               'with' : ('linespoints', 'with linespoints')}

    """

    # For _option_list explanation, see docstring for PlotItem.
    _option_list = {
        'axes' : lambda self, axes: self.set_string_option(
            'axes', axes, None, 'axes %s'),
        'with' : lambda self, with_: self.set_string_option(
            'with', with_, None, 'with %s'),
        'title' : lambda self, title: self.set_string_option(
            'title', title, 'notitle', 'title "%s"'),
        }
    _option_list['with_'] = _option_list['with']

    # order in which options need to be passed to gnuplot:
    _option_sequence = [
        'binary',
        'index', 'every', 'thru', 'using', 'smooth',
        'axes', 'title', 'with'
        ]

    def __init__(self, **keyw):
        """Construct a 'PlotItem'.

        Keyword options:

          'with_=<string>' -- choose how item will be plotted, e.g.,
              with_='points 3 3'.

          'title=<string>' -- set the title to be associated with the item
              in the plot legend.

          'title=None' -- choose 'notitle' option (omit item from legend).

        Note that omitting the title option is different than setting
        'title=None'; the former chooses gnuplot's default whereas the
        latter chooses 'notitle'.

        """

        self._options = {}
        self.set_option(**keyw)

    def get_option(self, name):
        """Return the setting of an option.  May be overridden."""

        try:
            return self._options[name][0]
        except:
            raise KeyError('option %s is not set!' % name)

    def set_option(self, **keyw):
        """Set or change a plot option for this PlotItem.

        See documentation for '__init__' for information about allowed
        options.  This function can be overridden by derived classes
        to allow additional options, in which case those options will
        also be allowed by '__init__' for the derived class.  However,
        it is easier to define a new '_option_list' variable for the
        derived class.

        """

        for (option, value) in list(keyw.items()):
            try:
                setter = self._option_list[option]
            except KeyError:
                raise Errors.OptionError('%s=%s' % (option,value))
            if setter is None:
                raise Errors.OptionError(
                    'Cannot modify %s option after construction!', option)
            else:
                setter(self, value)

    def set_string_option(self, option, value, default, fmt):
        """Set an option that takes a string value."""

        if value is None:
            self._options[option] = (value, default)
        elif isinstance(value,string_types):
            self._options[option] = (value, fmt % value)
        else:
            Errors.OptionError('%s=%s' % (option, value,))

    def clear_option(self, name):
        """Clear (unset) a plot option.  No error if option was not set."""

        try:
            del self._options[name]
        except KeyError:
            pass

    def get_base_command_string(self):
        raise NotImplementedError()

    def get_command_option_string(self):
        cmd = []
        for opt in self._option_sequence:
            (val,str) = self._options.get(opt, (None,None))
            if str is not None:
                cmd.append(str)
        return " ".join(cmd)

    def command(self):
        """Build the plot command to be sent to gnuplot.

        Build and return the plot command, with options, necessary to
        display this item.  If anything else needs to be done once per
        plot, it can be done here too.

        """

        return " ".join([
            self.get_base_command_string(),
            self.get_command_option_string(),
            ])

    def pipein(self, f):
        """Pipe necessary inline data to gnuplot.

        If the plot command requires data to be put on stdin (i.e.,
        'plot "-"'), this method should put that data there.  Can be
        overridden in derived classes.

        """

        pass


class Func(PlotItem):
    """Represents a mathematical expression to plot.

    Func represents a mathematical expression that is to be computed by
    gnuplot itself, as if you would type for example::

        gnuplot> plot sin(x)

    into gnuplot itself.  The argument to the contructor is a string
    that should be a mathematical expression.  Example::

        g.plot(Func('sin(x)', with_='line 3'))

    As shorthand, a string passed to the plot method of a Gnuplot
    object is also treated as a Func::

        g.plot('sin(x)')

    """

    def __init__(self, function, **keyw):
        PlotItem.__init__(self, **keyw)
        self.function = function

    def get_base_command_string(self):
        return self.function


class _FileItem(PlotItem):
    """A PlotItem representing a file that contains gnuplot data.

    This class is not meant for users but rather as a base class for
    other types of FileItem.

    """

    _option_list = PlotItem._option_list.copy()
    _option_list.update({
        'binary' : lambda self, binary: self.set_option_binary(binary),
        'index' : lambda self, value: self.set_option_colonsep('index', value),
        'every' : lambda self, value: self.set_option_colonsep('every', value),
        'using' : lambda self, value: self.set_option_colonsep('using', value),
        'smooth' : lambda self, smooth: self.set_string_option(
            'smooth', smooth, None, 'smooth %s'
            ),
        })

    def __init__(self, filename, **keyw):
        """Represent a PlotItem that gnuplot treates as a file.

        This class holds the information that is needed to construct
        the plot command line, including options that are specific to
        file-like gnuplot input.

        <filename> is a string representing the filename to be passed
        to gnuplot within quotes.  It may be the name of an existing
        file, '-' for inline data, or the name of a named pipe.

        Keyword arguments:

            'using=<int>' -- plot that column against line number

            'using=<tuple>' -- plot using a:b:c:d etc.  Elements in
                the tuple that are None are output as the empty
                string.

            'using=<string>' -- plot `using <string>' (allows gnuplot's
                arbitrary column arithmetic)

            'every=<value>' -- plot 'every <value>'.  <value> is
                formatted as for 'using' option.

            'index=<value>' -- plot 'index <value>'.  <value> is
                formatted as for 'using' option.

            'binary=<boolean>' -- data in the file is in binary format
                (this option is only allowed for grid data for splot).

            'smooth=<string>' -- smooth the data.  Option should be
                'unique', 'csplines', 'acsplines', 'bezier', or
                'sbezier'.

        The keyword arguments recognized by 'PlotItem' can also be
        used here.

        Note that the 'using' option is interpreted by gnuplot, so
        columns must be numbered starting with 1.

        By default, gnuplot uses the name of the file plus any 'using'
        option as the dataset title.  If you want another title, set
        it explicitly using the 'title' option.

        """

        self.filename = filename

        PlotItem.__init__(self, **keyw)

    def get_base_command_string(self):
        return gp.double_quote_string(self.filename)

    def set_option_colonsep(self, name, value):
        if value is None:
            self.clear_option(name)
        elif isinstance(value,(string_types+integer_types)):
            self._options[name] = (value, '%s %s' % (name, value,))
        elif type(value) is tuple:
            subopts = []
            for subopt in value:
                if subopt is None:
                    subopts.append('')
                else:
                    subopts.append(str(subopt))
            self._options[name] = (
                value,
                '%s %s' % (name, ":".join(subopts),),
                )
        else:
            raise Errors.OptionError('%s=%s' % (name, value,))

    def set_option_binary(self, binary):
        if binary:
            if not gp.GnuplotOpts.recognizes_binary_splot:
                raise Errors.OptionError(
                    'Gnuplot.py is currently configured to reject binary data')
            self._options['binary'] = (1, 'binary')
        else:
            self._options['binary'] = (0, None)


class _NewFileItem(_FileItem):
    def __init__(self, content, filename=None, **keyw):

        binary = keyw.get('binary', 0)
        if binary:
            mode = 'wb'
        else:
            mode = 'w'

        if filename:
            # This is a permanent file
            self.temp = False
            f = open(filename, mode)
        else:
            self.temp = True
            if hasattr(tempfile, 'mkstemp'):
                # Use the new secure method of creating temporary files:
                (fd, filename,) = tempfile.mkstemp(
                    suffix='.gnuplot', text=(not binary)
                    )
                f = os.fdopen(fd, mode)
            else:
                # for backwards compatibility to pre-2.3:
                filename = tempfile.mktemp()
                f = open(filename, mode)

        f.write(content)
        f.close()

        # If the user hasn't specified a title, set it to None so
        # that the name of the temporary file is not used:
        if self.temp and 'title' not in keyw:
            keyw['title'] = None

        _FileItem.__init__(self, filename, **keyw)

    def __del__(self):
        if self.temp:
            os.unlink(self.filename)


class _InlineFileItem(_FileItem):
    """A _FileItem that actually indicates inline data.

    """

    def __init__(self, content, **keyw):
        # If the user hasn't specified a title, set it to None so that
        # '-' is not used:
        if 'title' not in keyw:
            keyw['title'] = None

        if keyw.get('binary', 0):
            raise Errors.OptionError('binary inline data is not supported')

        _FileItem.__init__(self, '-', **keyw)

        if content[-1] == '\n':
            self.content = content
        else:
            self.content = content + '\n'

    def pipein(self, f):
        f.write(self.content + 'e\n')


if gp.GnuplotOpts.support_fifo:
    import threading

    class _FIFOWriter(threading.Thread):
        """Create a FIFO (named pipe), write to it, then delete it.

        The writing takes place in a separate thread so that the main
        thread is not blocked.  The idea is that once the writing is
        finished we know that gnuplot is done with the data that were in
        the file so we can delete the file.  This technique removes the
        ambiguity about when the temporary files should be deleted.

        Since the tempfile module does not provide an easy, secure way
        to create a FIFO without race conditions, we instead create a
        temporary directory using mkdtemp() then create the FIFO
        within that directory.  When the writer thread has written the
        full information to the FIFO, it deletes both the FIFO and the
        temporary directory that contained it.

        """

        def __init__(self, content, mode='w'):
            self.content = content
            self.mode = mode
            if hasattr(tempfile, 'mkdtemp'):
                # Make the file within a temporary directory that is
                # created securely:
                self.dirname = tempfile.mkdtemp(suffix='.gnuplot')
                self.filename = os.path.join(self.dirname, 'fifo')
            else:
                # For backwards compatibility pre-2.3, just use
                # mktemp() to create filename:
                self.dirname = None
                self.filename = tempfile.mktemp()
            threading.Thread.__init__(
                self,
                name=('FIFO Writer for %s' % (self.filename,)),
                )
            os.mkfifo(self.filename)
            self.start()

        def run(self):
            f = open(self.filename, self.mode)
            f.write(self.content)
            f.close()
            os.unlink(self.filename)
            if self.dirname is not None:
                os.rmdir(self.dirname)


    class _FIFOFileItem(_FileItem):
        """A _FileItem based on a FIFO (named pipe).

        This class depends on the availablity of os.mkfifo(), which only
        exists under Unix.

        """

        def __init__(self, content, **keyw):
            # If the user hasn't specified a title, set it to None so that
            # the name of the temporary FIFO is not used:
            if 'title' not in keyw:
                keyw['title'] = None

            _FileItem.__init__(self, '', **keyw)
            self.content = content
            if keyw.get('binary', 0):
                self.mode = 'wb'
            else:
                self.mode = 'w'

        def get_base_command_string(self):
            """Create the gnuplot command for plotting this item.

            The basecommand is different each time because each FIFOWriter
            creates a new FIFO.

            """

            # Create a new FIFO and a thread to write to it.  Retrieve the
            # filename of the FIFO to be used in the basecommand.
            fifo = _FIFOWriter(self.content, self.mode)
            return gp.double_quote_string(fifo.filename)


def File(filename, **keyw):
    """Construct a _FileItem object referring to an existing file.

    This is a convenience function that just returns a _FileItem that
    wraps the filename.

    <filename> is a string holding the filename of an existing file.
    The keyword arguments are the same as those of the _FileItem
    constructor.

    """

    if not isinstance(filename,string_types):
        raise Errors.OptionError(
            'Argument (%s) must be a filename' % (filename,)
            )
    return _FileItem(filename, **keyw)


def Data(*data, **keyw):
    """Create and return a _FileItem representing the data from *data.

    Create a '_FileItem' object (which is a type of 'PlotItem') out of
    one or more Float Python numpy arrays (or objects that can be
    converted to a float numpy array).  If the routine is passed a
    single with multiple dimensions, then the last index ranges over
    the values comprising a single data point (e.g., [<x>, <y>,
    <sigma>]) and the rest of the indices select the data point.  If
    passed a single array with 1 dimension, then each point is
    considered to have only one value (i.e., by default the values
    will be plotted against their indices).  If the routine is passed
    more than one array, they must have identical shapes, and then
    each data point is composed of one point from each array.  E.g.,
    'Data(x,x**2)' is a 'PlotItem' that represents x squared as a
    function of x.  For the output format, see the comments for
    'write_array()'.

    How the data are written to gnuplot depends on the 'inline'
    argument and preference settings for the platform in use.

    Keyword arguments:

        'cols=<tuple>' -- write only the specified columns from each
            data point to the file.  Since cols is used by python, the
            columns should be numbered in the python style (starting
            from 0), not the gnuplot style (starting from 1).

        'inline=<bool>' -- transmit the data to gnuplot 'inline'
            rather than through a temporary file.  The default is the
            value of gp.GnuplotOpts.prefer_inline_data.

        'filename=<string>' -- save data to a permanent file.

    The keyword arguments recognized by '_FileItem' can also be used
    here.

    """

    if len(data) == 1:
        # data was passed as a single structure
        data = utils.float_array(data[0])

        # As a special case, if passed a single 1-D array, then it is
        # treated as one value per point (by default, plotted against
        # its index):
        if len(data.shape) == 1:
            data = data[:,numpy.newaxis]
    else:
        # data was passed column by column (for example,
        # Data(x,y)); pack it into one big array (this will test
        # that sizes are all the same):
        data = utils.float_array(data)
        dims = len(data.shape)
        # transpose so that the last index selects x vs. y:
        data = numpy.transpose(data, (dims-1,) + tuple(range(dims-1)))
    if 'cols' in keyw:
        cols = keyw['cols']
        del keyw['cols']
        if isinstance(cols, integer_types):
            cols = (cols,)
        data = numpy.take(data, cols, -1)

    if 'filename' in keyw:
        filename = keyw['filename'] or None
        del keyw['filename']
    else:
        filename = None

    if 'inline' in keyw:
        inline = keyw['inline']
        del keyw['inline']
        if inline and filename:
            raise Errors.OptionError(
                'cannot pass data both inline and via a file'
                )
    else:
        inline = (not filename) and gp.GnuplotOpts.prefer_inline_data

    # Output the content into a string:
    f = StringIO()
    utils.write_array(f, data)
    content = f.getvalue()
    if inline:
        return _InlineFileItem(content, **keyw)
    elif filename:
        return _NewFileItem(content, filename=filename, **keyw)
    elif gp.GnuplotOpts.prefer_fifo_data:
        return _FIFOFileItem(content, **keyw)
    else:
        return _NewFileItem(content, **keyw)


def GridData(
    data, xvals=None, yvals=None, inline=_unset, filename=None, **keyw
    ):
    """Return a _FileItem representing a function of two variables.

    'GridData' represents a function that has been tabulated on a
    rectangular grid.  The data are written to a file; no copy is kept
    in memory.

    Arguments:

        'data' -- the data to plot: a 2-d array with dimensions
            (numx,numy).

        'xvals' -- a 1-d array with dimension 'numx'

        'yvals' -- a 1-d array with dimension 'numy'

        'binary=<bool>' -- send data to gnuplot in binary format?

        'inline=<bool>' -- send data to gnuplot "inline"?

        'filename=<string>' -- save data to a permanent file.

    Note the unusual argument order!  The data are specified *before*
    the x and y values.  (This inconsistency was probably a mistake;
    after all, the default xvals and yvals are not very useful.)

    'data' must be a data array holding the values of a function
    f(x,y) tabulated on a grid of points, such that 'data[i,j] ==
    f(xvals[i], yvals[j])'.  If 'xvals' and/or 'yvals' are omitted,
    integers (starting with 0) are used for that coordinate.  The data
    are written to a temporary file; no copy of the data is kept in
    memory.

    If 'binary=0' then the data are written to a datafile as 'x y
    f(x,y)' triplets (y changes most rapidly) that can be used by
    gnuplot's 'splot' command.  Blank lines are included each time the
    value of x changes so that gnuplot knows to plot a surface through
    the data.

    If 'binary=1' then the data are written to a file in a binary
    format that 'splot' can understand.  Binary format is faster and
    usually saves disk space but is not human-readable.  If your
    version of gnuplot doesn't support binary format (it is a
    recently-added feature), this behavior can be disabled by setting
    the configuration variable
    'gp.GnuplotOpts.recognizes_binary_splot=0' in the appropriate
    gp*.py file.

    Thus if you have three arrays in the above format and a Gnuplot
    instance called g, you can plot your data by typing
    'g.splot(Gnuplot.GridData(data,xvals,yvals))'.

    """

    # Try to interpret data as an array:
    data = utils.float_array(data)
    try:
        (numx, numy) = data.shape
    except ValueError:
        raise Errors.DataError('data array must be two-dimensional')

    if xvals is None:
        xvals = numpy.arange(numx)
    else:
        xvals = utils.float_array(xvals)
        if xvals.shape != (numx,):
            raise Errors.DataError(
                'The size of xvals must be the same as the size of '
                'the first dimension of the data array')

    if yvals is None:
        yvals = numpy.arange(numy)
    else:
        yvals = utils.float_array(yvals)
        if yvals.shape != (numy,):
            raise Errors.DataError(
                'The size of yvals must be the same as the size of '
                'the second dimension of the data array')

    # Binary defaults to true if recognizes_binary_plot is set;
    # otherwise it is forced to false.
    binary = keyw.get('binary', 1) and gp.GnuplotOpts.recognizes_binary_splot
    keyw['binary'] = binary

    if inline is _unset:
        inline = (
            (not binary) and (not filename)
            and gp.GnuplotOpts.prefer_inline_data
            )
    elif inline and filename:
        raise Errors.OptionError(
            'cannot pass data both inline and via a file'
            )

    # xvals, yvals, and data are now all filled with arrays of data.
    if binary:
        if inline:
            raise Errors.OptionError('binary inline data not supported')

        # write file in binary format

        # It seems that the gnuplot documentation for binary mode
        # disagrees with its actual behavior (as of v. 3.7).  The
        # documentation has the roles of x and y exchanged.  We ignore
        # the documentation and go with the code.

        mout = numpy.zeros((numy + 1, numx + 1), numpy.float32)
        mout[0,0] = numx
        mout[0,1:] = xvals.astype(numpy.float32)
        mout[1:,0] = yvals.astype(numpy.float32)
        try:
            # try copying without the additional copy implied by astype():
            mout[1:,1:] = numpy.transpose(data)
        except:
            # if that didn't work then downcasting from double
            # must be necessary:
            mout[1:,1:] = numpy.transpose(data.astype(numpy.float32))

        content = mout.tostring()
        if (not filename) and gp.GnuplotOpts.prefer_fifo_data:
            return _FIFOFileItem(content, **keyw)
        else:
            return _NewFileItem(content, filename=filename, **keyw)
    else:
        # output data to file as "x y f(x)" triplets.  This
        # requires numy copies of each x value and numx copies of
        # each y value.  First reformat the data:
        set = numpy.transpose(
            numpy.array(
                (numpy.transpose(numpy.resize(xvals, (numy, numx))),
                 numpy.resize(yvals, (numx, numy)),
                 data)), (1,2,0))

        # Now output the data with the usual routine.  This will
        # produce data properly formatted in blocks separated by blank
        # lines so that gnuplot can connect the points into a grid.
        f = StringIO()
        utils.write_array(f, set)
        content = f.getvalue()

        if inline:
            return _InlineFileItem(content, **keyw)
        elif filename:
            return _NewFileItem(content, filename=filename, **keyw)
        elif gp.GnuplotOpts.prefer_fifo_data:
            return _FIFOFileItem(content, **keyw)
        else:
            return _NewFileItem(content, **keyw)

# Should work with Python3 and Python2
