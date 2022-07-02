#! /usr/bin/env python

# Copyright (C) 2001-2003 Michael Haggerty <mhagger@alum.mit.edu>
#
# This file is licensed under the GNU Lesser General Public License
# (LGPL).  See LICENSE.txt for details.

"""Setup script for the Gnuplot module distribution.

"""

from distutils.core import setup

# Get the version number from the __init__ file:
from .__init__ import __version__

long_description = """\
Gnuplot.py is a Python package that allows you to create graphs from
within Python using the gnuplot plotting program.
"""

setup (
    # Distribution meta-data
    name='gnuplot-py',
    version=__version__,
    description='A Python interface to the gnuplot plotting program.',
    long_description=long_description,
    author='Michael Haggerty',
    author_email='mhagger@alum.mit.edu',
    url='http://gnuplot-py.sourceforge.net',
    license='LGPL',
    # This line is a workaround for a spelling error in earlier
    # versions of distutils.  The error has been fixed as of
    # python2.3, but we leave this line here for compatibility with
    # older python versions.
    licence='LGPL',

    # Description of the package in the distribution
    package_dir={'Gnuplot' : '.'},
    packages=['Gnuplot'],
    )

# Should work with Python3 and Python2
