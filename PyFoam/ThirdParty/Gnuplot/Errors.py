# $Id: Errors.py 244 2003-04-21 09:44:09Z mhagger $

# Copyright (C) 2001-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""Exception types that can be raised by Gnuplot.py."""


class Error(Exception):
    """All our exceptions are derived from this one."""
    pass


class OptionError(Error):
    """Raised for unrecognized option(s)"""
    pass


class DataError(Error):
    """Raised for data in the wrong format"""
    pass

# Should work with Python3 and Python2
