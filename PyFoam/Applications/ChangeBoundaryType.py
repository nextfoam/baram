#  ICE Revision: $Id$
"""
Application class that implements pyFoamChangeBoundaryType.py
"""

from .PyFoamApplication import PyFoamApplication

from os import path
from optparse import OptionGroup

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from .CommonChangeBoundary import CommonChangeBoundary

from PyFoam.ThirdParty.six import print_,string_types

class ChangeBoundaryType(PyFoamApplication,
                         CommonChangeBoundary):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Changes the type of a boundary in the boundary-file
        """
        CommonChangeBoundary.__init__(self)
        PyFoamApplication.__init__(self,args=args,
                                   description=description,
                                   usage="%prog <caseDirectory> <boundaryName> <new type>",
                                   changeVersion=False,
                                   nr=3,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        CommonChangeBoundary.addOptions(self)

        change=OptionGroup(self.parser,
                           "Change",
                           "Change specific options")
        self.parser.add_option_group(change)

        change.add_option("--additional-values",
                          action="store",
                          default=None,
                          dest="additionalValues",
                          help="Dictionary in Python-format with additional values to add to the boundary")

    def run(self):
        fName=self.parser.getArgs()[0]
        bName=self.parser.getArgs()[1]
        tName=self.parser.getArgs()[2]

        def changeType(bnd,target):
            found=False

            for val in bnd:
                if val==bName:
                    found=True
                elif found:
                    val["type"]=tName
                    if self.opts.additionalValues:
                        vals=self.opts.additionalValues
                        if isinstance(vals,string_types):
                            # we're called from the command line. Convert string to usable format
                            vals=eval(vals)
                        for k in vals:
                            val[k]=vals[k]
                    break

            if not found:
                self.warning("Boundary",bName,"not found in",bnd[::2])
                return None
            else:
                return bnd

        self.processBoundaryFiles(changeType,fName)

# Should work with Python3 and Python2
