# $Id$

# Copyright (C) 1998-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""_Gnuplot.py -- An object that represents a running gnuplot process.

This file implements the Gnuplot plotter object, which is an abstract
interface to a running gnuplot process.

"""

import sys, string, types

from . import gp, PlotItems, termdefs, Errors

from PyFoam.ThirdParty.six import string_types
from PyFoam.ThirdParty.six.moves import input as rinput

class _GnuplotFile:
    """A file to which gnuplot commands can be written.

    Sometimes it is convenient to write gnuplot commands to a command
    file for later evaluation.  In that case, one of these objects is
    used as a mock gnuplot process.  Note that temporary files may be
    deleted before you have time to execute the file!

    Members:

        'gnuplot' -- the file object gathering the commands.

    Methods:

        '__init__' -- open the file.

        '__call__' -- write a gnuplot command to the file, followed by a
            newline.

        'write' -- write an arbitrary string to the file.

        'flush' -- cause pending output to be written immediately.

    """

    def __init__(self, filename):
        """Open the file for writing."""

        self.gnuplot = open(filename, 'w')
        # forward write and flush methods:
        self.write = self.gnuplot.write
        self.flush = self.gnuplot.flush

    def __call__(self, s):
        """Write a command string to the file, followed by newline."""

        self.write(s + '\n')
        self.flush()


class Gnuplot:
    """Interface to a gnuplot program.

    A Gnuplot represents a higher-level interface to a gnuplot
    program.  It can plot 'PlotItem's, which represent each thing to
    be plotted on the current graph.  It keeps a reference to each of
    the 'PlotItems' used in the current plot, so that they (and their
    associated temporary files) are not deleted prematurely.

    Members:

        'itemlist' -- a list of the PlotItems that are associated with
            the current plot.  These are deleted whenever a new plot
            command is issued via the 'plot' method.

        'plotcmd' -- 'plot' or 'splot', depending on what was the last
            plot command.

    Methods:

        '__init__' -- if a filename argument is specified, the
            commands will be written to that file instead of being
            piped to gnuplot.

        'plot' -- clear the old plot and old 'PlotItems', then plot
            the arguments in a fresh plot command.  Arguments can be:
            a 'PlotItem', which is plotted along with its internal
            options; a string, which is plotted as a 'Func'; or
            anything else, which is plotted as a 'Data'.

        'splot' -- like 'plot', except for 3-d plots.

        'hardcopy' -- replot the plot to a postscript file (if
            filename argument is specified) or pipe it to the printer
            as postscript othewise.  If the option 'color' is set to
            true, then output color postscript.

        'replot' -- replot the old items, adding any arguments as
            additional items as in the plot method.

        'refresh' -- issue (or reissue) the plot command using the
            current 'PlotItems'.

        '__call__' -- pass an arbitrary string to the gnuplot process,
            followed by a newline.

        'xlabel', 'ylabel', 'zlabel', 'title' -- set corresponding plot
            attribute.

        'interact' -- read lines from stdin and send them, one by one,
            to the gnuplot interpreter.  Basically you can type
            commands directly to the gnuplot command processor.

        'load' -- load a file (using the gnuplot 'load' command).

        'save' -- save gnuplot commands to a file (using gnuplot
            'save' command) If any of the 'PlotItem's is a temporary
            file, it will be deleted at the usual time and the save
            file will be pretty useless :-).

        'clear' -- clear the plot window (but not the itemlist).

        'reset' -- reset all gnuplot settings to their defaults and
            clear the current itemlist.

        'set_string' -- set or unset a gnuplot option whose value is a
            string.

        '_clear_queue' -- clear the current 'PlotItem' list.

        '_add_to_queue' -- add the specified items to the current
            'PlotItem' list.

    """

    # optiontypes tells how to set parameters.  Specifically, the
    # parameter will be set using self.set_<type>(option, value),
    # where <type> is a string looked up in the following table.
    optiontypes = {
        'title' : 'string',
        'xlabel' : 'string',
        'ylabel' : 'string',
        'zlabel' : 'string',
        'xrange' : 'range',
        'yrange' : 'range',
        'zrange' : 'range',
        'trange' : 'range',
        'urange' : 'range',
        'vrange' : 'range',
        'parametric' : 'boolean',
        'polar' : 'boolean',
        'output' : 'string',
        }

    def __init__(self, filename=None, persist=None, debug=0, quiet=False):
        """Create a Gnuplot object.

        Create a 'Gnuplot' object.  By default, this starts a gnuplot
        process and prepares to write commands to it.

        Keyword arguments:

          'filename=<string>' -- if a filename is specified, the
              commands are instead written to that file (e.g., for
              later use using 'load').

          'persist=1' -- start gnuplot with the '-persist' option
              (which creates a new plot window for each plot command).
              (This option is not available on older versions of
              gnuplot.)

          'debug=1' -- echo the gnuplot commands to stderr as well as
              sending them to gnuplot.

        """

        if filename is None:
            self.gnuplot = gp.GnuplotProcess(persist=persist, quiet=quiet)
        else:
            if persist is not None:
                raise Errors.OptionError(
                    'Gnuplot with output to file does not allow '
                    'persist option.')
            self.gnuplot = _GnuplotFile(filename)
        self._clear_queue()
        self.debug = debug
        self.plotcmd = 'plot'
        self('set terminal %s' % (gp.GnuplotOpts.default_term,))

    def close(self):
        # This may cause a wait for the gnuplot process to finish
        # working, which is generally a good thing because it delays
        # the deletion of temporary files.
        if self.gnuplot is not None:
            self.gnuplot.close()
            self.gnuplot = None

    def __del__(self):
        self.close()
        self._clear_queue()

    def __call__(self, s):
        """Send a command string to gnuplot.

        Send the string s as a command to gnuplot, followed by a
        newline.  All communication with the gnuplot process (except
        for inline data) is through this method.

        """

        self.gnuplot(s)
        if self.debug:
            # also echo to stderr for user to see:
            sys.stderr.write('gnuplot> %s\n' % (s,))

    def refresh(self):
        """Refresh the plot, using the current 'PlotItem's.

        Refresh the current plot by reissuing the gnuplot plot command
        corresponding to the current itemlist.

        """

        plotcmds = []
        for item in self.itemlist:
            plotcmds.append(item.command())
        self(self.plotcmd + ' ' + ", ".join(plotcmds))
        for item in self.itemlist:
            # Uses self.gnuplot.write():
            item.pipein(self.gnuplot)
        self.gnuplot.flush()

    def _clear_queue(self):
        """Clear the 'PlotItems' from the queue."""

        self.itemlist = []

    def _add_to_queue(self, items):
        """Add a list of items to the itemlist (but don't plot them).

        'items' is a sequence of items, each of which should be a
        'PlotItem' of some kind, a string (interpreted as a function
        string for gnuplot to evaluate), or a numpy array (or
        something that can be converted to a numpy array).

        """

        for item in items:
            if isinstance(item, PlotItems.PlotItem):
                self.itemlist.append(item)
            elif isinstance(item,string_types):
                self.itemlist.append(PlotItems.Func(item))
            else:
                # assume data is an array:
                self.itemlist.append(PlotItems.Data(item))

    def plot(self, *items, **keyw):
        """Draw a new plot.

        Clear the current plot and create a new 2-d plot containing
        the specified items.  Each arguments should be of the
        following types:

        'PlotItem' (e.g., 'Data', 'File', 'Func') -- This is the most
            flexible way to call plot because the PlotItems can
            contain suboptions.  Moreover, PlotItems can be saved to
            variables so that their lifetime is longer than one plot
            command; thus they can be replotted with minimal overhead.

        'string' (e.g., 'sin(x)') -- The string is interpreted as
            'Func(string)' (a function that is computed by gnuplot).

        Anything else -- The object, which should be convertible to an
            array, is passed to the 'Data' constructor, and thus
            plotted as data.  If the conversion fails, an exception is
            raised.

        """

        if keyw:
            self.set(**keyw)

        self.plotcmd = 'plot'
        self._clear_queue()
        self._add_to_queue(items)
        self.refresh()

    def splot(self, *items, **keyw):
        """Draw a new three-dimensional plot.

        Clear the current plot and create a new 3-d plot containing
        the specified items.  Arguments can be of the following types:

        'PlotItem' (e.g., 'Data', 'File', 'Func', 'GridData' ) -- This
            is the most flexible way to call plot because the
            PlotItems can contain suboptions.  Moreover, PlotItems can
            be saved to variables so that their lifetime is longer
            than one plot command--thus they can be replotted with
            minimal overhead.

        'string' (e.g., 'sin(x*y)') -- The string is interpreted as a
            'Func()' (a function that is computed by gnuplot).

        Anything else -- The object is converted to a Data() item, and
            thus plotted as data.  Note that each data point should
            normally have at least three values associated with it
            (i.e., x, y, and z).  If the conversion fails, an
            exception is raised.

        """

        if keyw:
            self.set(**keyw)

        self.plotcmd = 'splot'
        self._clear_queue()
        self._add_to_queue(items)
        self.refresh()

    def replot(self, *items, **keyw):
        """Replot the data, possibly adding new 'PlotItem's.

        Replot the existing graph, using the items in the current
        itemlist.  If arguments are specified, they are interpreted as
        additional items to be plotted alongside the existing items on
        the same graph.  See 'plot' for details.

        """

        if keyw:
            self.set(**keyw)

        self._add_to_queue(items)
        self.refresh()

    def interact(self):
        """Allow user to type arbitrary commands to gnuplot.

        Read stdin, line by line, and send each line as a command to
        gnuplot.  End by typing C-d.

        """

        import time
        if sys.platform == 'win32':
            sys.stderr.write('Press Ctrl-z twice to end interactive input\n')
        else:
            # What should this be for the Macintosh?
            sys.stderr.write('Press C-d to end interactive input\n')
        while 1:
            try:
                line = rinput('gnuplot>>> ')
            except EOFError:
                break
            self(line)
            time.sleep(0.2) # give a little time for errors to be written
        sys.stderr.write('\n')

    def clear(self):
        """Clear the plot window (without affecting the current itemlist)."""

        self('clear')

    def reset(self):
        """Reset all gnuplot settings to their defaults and clear itemlist."""

        self('reset')
        self.itemlist = []

    def load(self, filename):
        """Load a file using gnuplot's 'load' command."""

        self("load '%s'" % (filename,))

    def save(self, filename):
        """Save the current plot commands using gnuplot's 'save' command."""

        self("save '%s'" % (filename,))

    def set_string(self, option, s=None):
        """Set a string option, or if s is omitted, unset the option."""

        if s is None:
            self('set %s' % (option,))
        else:
            self('set %s "%s"' % (option, s))

    def set_label(self, option, s=None, offset=None, font=None):
        """Set or clear a label option, which can include an offset or font.

        If offset is specified, it should be a tuple of two integers
        or floats.

        If font is specified, it is appended to the command as a
        string in double quotes.  Its interpretation is
        terminal-dependent; for example, for postscript it might be
        'Helvetica,14' for 14 point Helvetica.

        """

        cmd = ['set', option]
        if s is not None:
            cmd.append('"%s"' % (s,))

            if offset is not None:
                cmd.append('%s,%s' % offset)

            if font is not None:
                cmd.append('"%s"' % (font,))

        self(" ".join(cmd))

    def set_boolean(self, option, value):
        """Set an on/off option.  It is assumed that the way to turn
        the option on is to type `set <option>' and to turn it off,
        `set no<option>'."""

        if value:
            self('set %s' % option)
        else:
            self('set no%s' % option)

    def set_range(self, option, value):
        """Set a range option (xrange, yrange, trange, urange, etc.).
        The value can be a string (which is passed as-is, without
        quotes) or a tuple (minrange,maxrange) of numbers or string
        expressions recognized by gnuplot.  If either range is None
        then that range is passed as `*' (which means to
        autoscale)."""

        if value is None:
            self('set %s [*:*]' % (option,))
        elif isinstance(value,string_types):
            self('set %s %s' % (option, value,))
        else:
            # Must be a tuple:
            (minrange,maxrange) = value
            if minrange is None:
                minrange = '*'
            if maxrange is None:
                maxrange = '*'
            self('set %s [%s:%s]' % (option, minrange, maxrange,))

    def set(self, **keyw):
        """Set one or more settings at once from keyword arguments.
        The allowed settings and their treatments are determined from
        the optiontypes mapping."""

        for (k,v) in list(keyw.items()):
            try:
                type = self.optiontypes[k]
            except KeyError:
                raise 'option %s is not supported' % (k,)
            getattr(self, 'set_%s' % type)(k, v)

    def xlabel(self, s=None, offset=None, font=None):
        """Set the plot's xlabel."""

        self.set_label('xlabel', s, offset=offset, font=font)

    def ylabel(self, s=None, offset=None, font=None):
        """Set the plot's ylabel."""

        self.set_label('ylabel', s, offset=offset, font=font)

    def zlabel(self, s=None, offset=None, font=None):
        """Set the plot's zlabel."""

        self.set_label('zlabel', s, offset=offset, font=font)

    def title(self, s=None, offset=None, font=None):
        """Set the plot's title."""

        self.set_label('title', s, offset=offset, font=font)

    def hardcopy(self, filename=None, terminal='postscript', **keyw):
        """Create a hardcopy of the current plot.

        Output the current plot to the default printer (if configured)
        or to the specified filename.

        Note that gnuplot remembers the printer suboptions across
        terminal changes (at least for postscript).  Therefore if you
        set, for example, color=1 for one hardcopy then the next
        hardcopy will also be color unless you explicitly choose
        color=0.  Alternately you can force all of the options to
        their defaults by setting mode='default'.  I consider this to
        be a bug in gnuplot.

        Keyword arguments:

          'filename=<string>' -- if a filename is specified, save the
              output in that file; otherwise print it immediately
              using the 'default_lpr' configuration option.

          'terminal=<string>' -- the type of gnuplot 'terminal' to use
              for the output (e.g., 'postscript', 'png', 'latex',
              etc).  Look in termdefs.py to see what terminal types
              are defined, or check termdefs.terminal_opts.keys().

        The rest of the keyword arguments depend on the terminal type.

        Keyword arguments for 'postscript' terminal:

          'mode=<string>' -- set the postscript submode ('landscape',
              'portrait', 'eps', or 'default').  The default is
              to leave this option unspecified.

          'eps=<bool>' -- shorthand for 'mode="eps"'; asks gnuplot to
              generate encapsulated postscript.

          'enhanced=<bool>' -- if set (the default), then generate
              enhanced postscript, which allows extra features like
              font-switching, superscripts, and subscripts in axis
              labels.  (Some old gnuplot versions do not support
              enhanced postscript; if this is the case set
              gp.GnuplotOpts.prefer_enhanced_postscript=None.)

          'color=<bool>' -- if set, create a plot with color.  Default
              is to leave this option unchanged.

          'solid=<bool>' -- if set, force lines to be solid (i.e., not
              dashed).

          'duplexing=<string>' -- set duplexing option ('defaultplex',
              'simplex', or 'duplex').  Only request double-sided
              printing if your printer can handle it.  Actually this
              option is probably meaningless since hardcopy() can only
              print a single plot at a time.

          'fontname=<string>' -- set the default font to <string>,
              which must be a valid postscript font.  The default is
              to leave this option unspecified.

          'fontsize=<double>' -- set the default font size, in
              postscript points.

        Note that this command will return immediately even though it
        might take gnuplot a while to actually finish working.  Be
        sure to pause briefly before issuing another command that
        might cause the temporary files to be deleted.

        """

        if filename is None:
            if gp.GnuplotOpts.default_lpr is None:
                raise Errors.OptionError(
                    'default_lpr is not set, so you can only print to a file.')
            filename = gp.GnuplotOpts.default_lpr

        # Be careful processing the options.  If the user didn't
        # request an option explicitly, do not specify it on the 'set
        # terminal' line (don't even specify the default value for the
        # option).  This is to avoid confusing older versions of
        # gnuplot that do not support all of these options.  The
        # exception is postscript's 'enhanced' option, which is just
        # too useful to have to specify each time!

        # Build up the 'set terminal' command here:
        setterm = ['set', 'terminal', terminal]
        try:
            opts = termdefs.terminal_opts[terminal]
        except KeyError:
            raise Errors.OptionError(
                'Terminal "%s" is not configured in Gnuplot.py.' % (terminal,))

        for opt in opts:
            cmd = opt(keyw)
            if cmd is not None:
                setterm.extend(cmd)
        if keyw:
            # Not all options were consumed.
            raise Errors.OptionError(
                'The following options are unrecognized: %s'
                % (", ".join(list(keyw.keys())),)
                )

        self.set_string('output', filename)
        self(" ".join(setterm))
        # replot the current figure (to the printer):
        self.refresh()
        # reset the terminal to its `default' setting:
        self('set terminal %s' % gp.GnuplotOpts.default_term)
        self.set_string('output')

# Should work with Python3 and Python2
