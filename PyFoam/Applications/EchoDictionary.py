#  ICE Revision: $Id$
"""
Application class that implements pyFoamEchoDictionary
"""

import sys

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from .CommonParserOptions import CommonParserOptions

from PyFoam.ThirdParty.six import print_

class EchoDictionary(PyFoamApplication,
                     CommonParserOptions):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Reads a Foam-Dictionary and prints it to the screen. Mainly for
reformatting unformated dictionaries and debugging the parser
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <dictfile>",
                                   nr=1,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        CommonParserOptions.addOptions(self)

    def run(self):
        fName=self.parser.getArgs()[0]
        try:
            dictFile=ParsedParameterFile(fName,
                                         backup=False,
                                         debug=self.opts.debugParser,
                                         noHeader=self.opts.noHeader,
                                         noBody=self.opts.noBody,
                                         preserveComments=self.opts.preserveComments,
                                         boundaryDict=self.opts.boundaryDict,
                                         listDict=self.opts.listDict,
                                         listDictWithHeader=self.opts.listDictWithHeader,
                                         listLengthUnparsed=self.opts.listLengthUnparsed,
                                         treatBinaryAsASCII=self.opts.treatBinaryAsASCII,
                                         doMacroExpansion=self.opts.doMacros)
        except IOError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.error("Problem with file",fName,":",e)

        self.setData({"dictFile":dictFile})

        print_(dictFile)

# Should work with Python3 and Python2
