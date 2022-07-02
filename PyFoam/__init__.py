#  ICE Revision: $Id$
""" Utility-classes for OpenFOAM

Module for the Execution of OpenFOAM-commands and processing their output
"""

from PyFoam.Infrastructure.Configuration import Configuration


def version():
    """:return: Version number as a tuple"""
    return (2021, 6)
    # return (2021, 6, "development")  # Change in bin/pyFoamVersion.py as well !!!!


def versionString():
    """:return: Version number of PyFoam"""
    v = version()

    vStr = "%d" % v[0]
    for d in v[1:]:
        if type(d) == int:
            vStr += (".%d" % d)
        else:
            vStr += ("-%s" % str(d))
    return vStr


def foamVersionString():
    from PyFoam.FoamInformation import foamVersionString
    return foamVersionString()


_configuration = Configuration()


def configuration():
    """:return: The Configuration information of PyFoam"""
    return _configuration

# Should work with Python3 and Python2
