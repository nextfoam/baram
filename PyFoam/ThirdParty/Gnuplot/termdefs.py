# $Id: termdefs.py 302 2008-01-14 22:15:19Z bmcage $

# Copyright (C) 2001-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""Terminal definition file.

This module describes the options available to gnuplot's various
terminals.  For the moment, it only supports a few terminals, but the
infrastructure is here to add others as they are needed.

Part of the trick is that the 'set terminal' command takes myriad
suboptions with various argument types, and order is sometimes
significant.  The other part of the trick is that there are over 50
terminal types, and each terminal has its own set of options.

The strategy here is to define a general mechanism for turning Python
keyword parameters into fragments of gnuplot command strings.  There
are a number of classes derived from Arg that do this.  Some take
string args, some boolean, etc.  Then the list of options that each
terminal accepts is stored in the terminal_opts dictionary.
Gnuplot.hardcopy(), in turn, uses this dictionary to interpret its
keyword arguments and build the 'set terminal' command.

"""


import types

from . import gp, Errors

from PyFoam.ThirdParty.six import string_types

class Arg:
    """Process terminal subargs and return a command fragment.

    Pull one or more arguments from keyw and output a list of strings
    that will be appended to the 'set terminal' (separated by spaces).
    Delete any used args from keyw.  If no relevant options are found,
    return None.

    This is a base class for the actual argument-processing classes.
    Derived classes must define a __call__(self, keyw) method
    returning a list of strings or None.

    """

    pass


class ArgOneParam(Arg):
    """Arg abstract base class specialized for exactly one parameter.

    Members:

        'argname' -- The name of the keyword argument used to pass
            this argument to Python.

        'default' -- The default value of the argument, used if no
            keyword parameter is found.  If this is None, then no
            default is assumed.

    """

    def __init__(self, argname, default):
        self.argname = argname
        self.default = default

    def get_option(self, keyw):
        """Get the keyword argument corresponding to this Arg.

        Look in keyw for the keyword argument needed by this Arg.  If
        it is found, delete it from keyw and return it.  If it is not
        found, return self.default.

        """

        try:
            k = keyw[self.argname]
        except KeyError:
            return self.default
        else:
            del keyw[self.argname]
        return k


class KeywordArg(ArgOneParam):
    """Represent an argument that must be passed as a keyword to gnuplot.

    Some gnuplot options take the form of single unquoted keywords
    (possibly preceded by a fixed keyword).  We allow those to be
    passed as strings 'option="keyword"'.  Check that the option
    supplied is in the list of allowed options.

    Members:

        'fixedword' -- the fixed keyword that must precede the
            variable keyword in the gnuplot command, or None if none
            is required.

        'options' -- a list of strings containing the legal
            alternatives for this argument.

    """

    def __init__(self, argname, options, fixedword=None, default=None):
        ArgOneParam.__init__(self, argname, default)
        self.fixedword = fixedword
        self.options = options

    def __call__(self, keyw):
        k = self.get_option(keyw)

        if k is None:
            return None
        elif k in self.options:
            if self.fixedword is None:
                return [k]
            else:
                return [self.fixedword, k]
        else:
            raise Errors.OptionError(
                'Illegal option %s="%s"' % (self.argname, k,))


class StringArg(ArgOneParam):
    """An option taking a quoted string argument."""

    def __init__(self, argname, fixedword=None, default=None):
        ArgOneParam.__init__(self, argname, default)
        self.fixedword = fixedword

    def __call__(self, keyw):
        k = self.get_option(keyw)

        if k is None:
            return None
        elif not isinstance(k,string_types):
            raise Errors.OptionError(
                'Option %s must be a string' % (self.argname,))
        else:
            retval = []
            if self.fixedword is not None:
                retval.append(self.fixedword)
            retval.append('"%s"' % k)
            return retval


class BareStringArg(ArgOneParam):
    """An arbitrary argument output without quotes.

    The argument can be a string or anything with a str()
    representation, or a tuple of such things.  Thus this can be used
    for strings (which will be output without quotation marks),
    integers, floating point arguments, or multiple arguments of the
    above types (which will be output separated by spaces).  No
    checking is done that the argument is sensible.

    """

    def __init__(self, argname, fixedword=None, default=None):
        ArgOneParam.__init__(self, argname, default)
        self.fixedword = fixedword

    def __call__(self, keyw):
        k = self.get_option(keyw)

        if k is None:
            return None
        else:
            retval = []
            if self.fixedword is not None:
                retval.append(self.fixedword)
            if type(k) in (tuple,list):
                for i in k:
                    retval.append(str(i))
            else:
                retval.append(str(k))
            return retval


class BooleanArg(ArgOneParam):
    """An argument that takes a true/false value.

    The argument should be 0 or 1.  The option is output to gnuplot as
    'trueval' if the argument is true or 'falseval' if the argument is
    false.  Either one can be 'None', in which case nothing is output.
    'default' should also be 0 or 1.

    """

    def __init__(self, argname, trueval, falseval,
                 fixedword=None, default=None):
        ArgOneParam.__init__(self, argname, default)
        self.trueval = trueval
        self.falseval = falseval
        self.fixedword = fixedword

    def __call__(self, keyw):
        k = self.get_option(keyw)
        if k is None:
            return None
        else:
            retval = []
            if self.fixedword is not None:
                retval.append(self.fixedword)
            if k:
                val = self.trueval
            else:
                val = self.falseval
            if val is not None:
                retval.append(val)
            return retval


class MutuallyExclusiveArgs(Arg):
    """A group of args, of which either zero or one may be set, but not more.

    Members:

        subargs -- a list [('argname', arg), ...] of Arg instances.
            'argname' is used to identify the corresponding arg in
            error messages.  (The name of the corresponding keyword
            args is determined internally by each arg.)

    """

    def __init__(self, *subargs):
        self.subargs = list(subargs)

    def __call__(self, keyw):
        foundargname = None
        retval = None
        for (argname, arg,) in self.subargs:
            cmd = arg(keyw)
            if cmd is not None:
                if foundargname is not None:
                    raise Errors.OptionError(
                        'Arguments %s and %s cannot both be specified'
                        % (foundargname, argname,)
                        )
                else:
                    foundargname = argname
                    retval = cmd
        return retval # might be None


class KeywordOrBooleanArg(Arg):
    """Allow a keyword arg to be specified either as a keyword or a boolean.

    This arg type is the most flexible way to allow keyword parameters
    to be specified.  Say there is an option like 'fontsize' that can
    take the values 'small' or 'large'.  This could be represented as

        'KeywordOrBooleanArg(options=["small", "large"], argname="fontsize")'

    In that case, the fontsize could be specified in any of the
    following ways:

        'g.hardcopy(..., fontsize="small", ...)'
        'g.hardcopy(..., fontsize="large", ...)'
        'g.hardcopy(..., small=1, ...)'
        'g.hardcopy(..., large=1, ...)'

    If 'argname' is set to be 'None', then the first two possibilities
    are omitted.

    In the special case that there are exactly two alternatives, one
    can also use:

        'g.hardcopy(..., small=0, ...) # implies fontsize="large"'
        'g.hardcopy(..., large=0, ...) # implies fontsize="small"'

    Obviously care must be taken to ensure that none of the implied
    keyword parameter names conflict with one another or with any of
    the other Args allowed by a function.

    Members:

        'options' -- a list of strings representing allowed keyword
            values.  These options can be used as boolean values in
            the style 'option=1'.

        'argname' -- the name of the argname for the 'arg=value' style
            of setting the argument.  If 'None', then this style is
            not allowed.

        'fixedword' -- a fixed keyword that must precede the option,
            or 'None'.

        'default' -- the default option to set if nothing is set
            explicitly, or None to leave nothing set in that case.

    """

    def __init__(self, options, argname=None, fixedword=None, default=None):
        self.options = options
        self.argname = argname
        self.fixedword = fixedword
        self.default = default
        assert self.default is None or self.default in self.options, \
               'default must be a valid option'

    def __call__(self, keyw):
        if self.argname is not None and self.argname in keyw:
            k = keyw[self.argname]
            del keyw[self.argname]
            if k is None:
                pass
            elif k in self.options:
                # Make sure it isn't contradicted by the corresponding boolean:
                if k in keyw and not keyw[k]:
                    raise Errors.OptionError(
                        'Arguments %s and %s are contradictory'
                        % (self.argname, k,)
                        )
                else:
                    # Store the option into the boolean to be processed below:
                    keyw[k] = 1
            else:
                raise Errors.OptionError(
                    'Illegal option %s=%s' % (self.argname, k,))

        # Now scan the booleans and make sure that at most one is set:
        option = None
        for i in range(len(self.options)):
            k = self.options[i]
            if k in keyw:
                newval = keyw[k]
                del keyw[k]
                if newval:
                    if option is not None:
                        raise Errors.OptionError(
                            'Arguments %s and %s cannot both be specified'
                            % (option, k,)
                            )
                    else:
                        option = k
                else:
                    # newval was false.  This is only legal if this
                    # option only has two possible values:
                    if len(self.options) == 2:
                        option = self.options[1 - i]
                    else:
                        pass

        if option is None:
            if self.default is None:
                return None
            else:
                option = self.default
        retval = []
        if self.fixedword is not None:
            retval.append(self.fixedword)
        retval.append(option)
        return retval


# Now we define the allowed options for a few terminal types.  This
# table is used by Gnuplot.hardcopy() to construct the necessary 'set
# terminal' command.

terminal_opts = {}

terminal_opts['postscript'] = [
    KeywordOrBooleanArg(
        options=['landscape', 'portrait', 'eps', 'default'],
        argname='mode',
        ),
    KeywordOrBooleanArg(
        options=['enhanced', 'noenhanced'],
        # This default should probably be computed from the *current*
        # value of GnuplotOpts, not at import time. ###
        default=(gp.GnuplotOpts.prefer_enhanced_postscript
                 and 'enhanced'
                 or 'noenhanced'),
        ),
    KeywordOrBooleanArg(options=['color', 'monochrome']),
    KeywordOrBooleanArg(options=['solid', 'dashed']),
    KeywordOrBooleanArg(
        options=['defaultplex', 'simplex', 'duplex'],
        argname='duplexing',
        ),
    StringArg(argname='fontname'),
    BareStringArg(argname='fontsize'),
    ]

terminal_opts['pdf'] = [
    KeywordOrBooleanArg(
        options=['landscape', 'portrait', 'eps', 'default'],
        argname='mode',
        ),
    KeywordOrBooleanArg(options=['color', 'monochrome']),
    KeywordOrBooleanArg(options=['solid', 'dashed']),
    KeywordOrBooleanArg(
        options=['defaultplex', 'simplex', 'duplex'],
        argname='duplexing',
        ),
    StringArg(argname='fontname'),
    BareStringArg(argname='fontsize'),
    ]

terminal_opts['png'] = [
    KeywordOrBooleanArg(
        options=['small', 'medium', 'large'],
        argname='fontsize',
        ),
    KeywordOrBooleanArg(options=['monochrome', 'gray', 'color']),
    ]

terminal_opts['fig'] = [
    KeywordOrBooleanArg(options=['monochrome', 'color']),
    KeywordOrBooleanArg(options=['small', 'big']),
    BareStringArg(argname='pointsmax', fixedword='pointsmax'),
    KeywordOrBooleanArg(options=['landscape', 'portrait']),
    KeywordOrBooleanArg(options=['metric', 'inches']),
    BareStringArg(argname='fontsize'),
    BareStringArg(argname='size'), # needs a tuple of two doubles
    BareStringArg(argname='thickness'),
    BareStringArg(argname='depth'),
    ]

terminal_opts['cgm'] = [
    KeywordOrBooleanArg(
        options=['landscape', 'portrait', 'default'],
        argname='mode',
        ),
    KeywordOrBooleanArg(options=['color', 'monochrome']),
    KeywordOrBooleanArg(options=['rotate', 'norotate']),
    BareStringArg(argname='width', fixedword='width'),
    BareStringArg(argname='linewidth', fixedword='linewidth'),
    StringArg(argname='font'),
    BareStringArg(argname='fontsize'),
    ]

terminal_opts['pict'] = [
    KeywordOrBooleanArg(
        options=['landscape', 'portrait', 'default'],
        argname='mode',
        ),
    KeywordOrBooleanArg(options=['color', 'monochrome']),
    KeywordOrBooleanArg(options=['dashes', 'nodashes']),

    # default font, which must be a valid pict font:
    StringArg(argname='fontname'),

    # default font size, in points:
    BareStringArg(argname='fontsize'),

    # width of plot in pixels:
    BareStringArg(argname='width'),

    # height of plot in pixels:
    BareStringArg(argname='height'),

    ]

terminal_opts['mp'] = [
    KeywordOrBooleanArg(options=['color', 'colour', 'monochrome']),
    KeywordOrBooleanArg(options=['solid', 'dashed']),
    KeywordOrBooleanArg(options=['notex', 'tex', 'latex']),
    BareStringArg(argname='magnification'),
    KeywordOrBooleanArg(options=['psnfss', 'psnfss-version7', 'nopsnfss']),
    BareStringArg(argname='prologues'),
    KeywordOrBooleanArg(options=['a4paper']),
    KeywordOrBooleanArg(options=['amstex']),
    StringArg(argname='fontname'),
    BareStringArg(argname='fontsize'),
    ]

terminal_opts['svg'] = [
    BareStringArg(argname='size', fixedword='size'),  # tuple of two doubles
    KeywordOrBooleanArg(options=['fixed', 'dynamic']),
    StringArg(argname='fname', fixedword='fname'),
    BareStringArg(argname='fsize', fixedword='fsize'),
    KeywordOrBooleanArg(options=['enhanced', 'noenhanced']),
    StringArg(argname='fontfile', fixedword='fontfile'),
    ]

# Should work with Python3 and Python2
