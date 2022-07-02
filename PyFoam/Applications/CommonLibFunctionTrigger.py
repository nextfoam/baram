"""Implements a trigger that removes the libs and/or function
entry from the controlDict"""

import sys

from os import path
from optparse import OptionGroup
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Error import warning

class CommonLibFunctionTrigger(object):
    """ The class that does the actual triggering
    """

    def addOptions(self):
        grp=OptionGroup(self.parser,
                        "Manipulating controlDict",
                        "Temporarily remove entries from the controlDict that are incompatible with some applications")

        grp.add_option("--remove-libs",
                       action="store_true",
                       dest="removeLibs",
                       default=False,
                       help="Remove the libs entry from the controlDict for the duration of the application run")
        grp.add_option("--remove-functions",
                       action="store_true",
                       dest="removeFunctions",
                       default=False,
                       help="Remove the functions entry from the controlDict for the duration of the application run")
        self.parser.add_option_group(grp)

    def addLibFunctionTrigger(self,run,sol):
        if self.opts.removeLibs or self.opts.removeFunctions:
            warning("Adding Trigger to reset lib/function at end")
            trig=LibFunctionTrigger(sol,self.opts.removeLibs,self.opts.removeFunctions)
            run.addEndTrigger(trig.resetIt)


class LibFunctionTrigger:
    def __init__(self,sol,libs,funs):
        self.control=ParsedParameterFile(path.join(sol.systemDir(),"controlDict"),
                                         backup=True,
                                         doMacroExpansion=True)

        self.fresh=False

        try:
            if libs and ("libs" in self.control):
                warning("Temporarily removing the libs-entry from the controlDict")
                del self.control["libs"]
                self.fresh=True
            if funs and ("functions" in self.control):
                warning("Temporarily removing the functions-entry from the controlDict")
                del self.control["functions"]
                self.fresh=True

            if self.fresh:
                self.control.writeFile()
            else:
                self.control.restore()

        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            warning("Restoring defaults")
            self.control.restore()
            raise e

    def resetIt(self):
        if self.fresh:
            warning("Trigger called: Resetting controlDict")
            self.control.restore()
            self.fresh=False

# Should work with Python3 and Python2
