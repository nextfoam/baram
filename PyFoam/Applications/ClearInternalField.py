#  ICE Revision: $Id$
"""
Application class that implements pyFoamClearInternalField.py
"""

from os import path

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from PyFoam.ThirdParty.six import print_

import sys

class ClearInternalField(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Takes a field-file and makes the whole internal field uniform. Either
taking the value from a patch or using a user-specified value
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <fieldfile>",
                                   changeVersion=False,
                                   nr=1,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("--patch",
                               action="store",
                               default=None,
                               dest="patch",
                               help="The name of the patch that should provide the value")
        self.parser.add_option("--value",
                               action="store",
                               default=None,
                               dest="value",
                               help="The value that should be used for the internal field")
        self.parser.add_option("--test",
                               action="store_true",
                               default=None,
                               dest="test",
                               help="Does not write the file but only prints it to the screen")
        self.parser.add_option("--source-key",
                               action="store",
                               default="value",
                               dest="srckey",
                               help="The key that should be read from the source patch: %default")


    def run(self):
        fName=self.parser.getArgs()[0]

        if self.opts.patch==None and self.opts.value==None:
            self.error("Either a patch or a value must be specified")
        if self.opts.patch!=None and self.opts.value!=None:
            self.error("Only a patch or a value can be specified")

        try:
            fieldFile=ParsedParameterFile(fName,backup=False)
        except IOError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.error("Problem with file",fName,":",e)

        value=""
        if self.opts.patch:
            value=fieldFile["boundaryField"][self.opts.patch][self.opts.srckey]
        else:
            value="uniform "+self.opts.value

        fieldFile["internalField"]=value

        if self.opts.test:
            print_(str(fieldFile))
        else:
            fieldFile.writeFile()
            self.addToCaseLog(path.dirname(path.dirname(path.abspath(fName))))

# Should work with Python3 and Python2
