#  ICE Revision: $Id$
""" Site-specific Packages

This Package is a stand-in for the actual Package. Imports will be redirected
to $PYFOAM_SITE_DIR/lib if this is present. Othherwise this directory is useless
"""

from PyFoam.Infrastructure.Hardcoded import pyFoamSiteVar
import sys
from os import path,environ
from PyFoam.ThirdParty.six import print_

if pyFoamSiteVar in environ:
    libDir=path.join(environ[pyFoamSiteVar],"lib")
    if not path.isdir(libDir):
        print_(libDir,"is not a directory")
    else:
        # this makes sure that Python-files found in PYFOAM_SITE_DIR/lib are used
        __path__.insert(0,libDir)
else:
    print_("No environment variable",pyFoamSiteVar,"set. Importing PyFoam.Site is pointless")
