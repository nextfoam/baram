#  ICE Revision: $Id$
"""
Application class that implements pyFoamReadDictionary
"""

import sys,re

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from PyFoam.ThirdParty.six import print_

class ReadDictionary(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Reads a value from a Foam-Dictionary and prints it to the screen.  The
description of the value is word. If the value is non-atomic (a list
or a dictionary) it is output in Python-notation.  Parts of the
expression can be accessed by using the Python-notation for accessing
sub-expressions.

Example of usage:
      pyFoamReadDictionary.py pitzDaily/0/U "boundaryField['inlet']['type']"
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <dictfile> <key>",
                                   nr=2,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("--debug",
                               action="store_true",
                               default=None,
                               dest="debug",
                               help="Debugs the parser")


    def run(self):
        fName=self.parser.getArgs()[0]
        all=self.parser.getArgs()[1]
        if all[0]=='"':
            all=all[1:]
        if all[-1]=='"':
            all=all[:-1]

        match=re.compile("([a-zA-Z_][a-zA-Z0-9_]*)(.*)").match(all)
        if match==None:
            self.error("Expression",all,"not usable as an expression")

        key=match.group(1)
        sub=None
        if len(match.groups())>1:
            if match.group(2)!="":
                sub=match.group(2)

        try:
            dictFile=ParsedParameterFile(fName,backup=False,debug=self.opts.debug)
            val=dictFile[key]
        except KeyError:
            self.error("Key: ",key,"not existing in File",fName)
        except IOError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.error("Problem with file",fName,":",e)

        if sub==None:
            erg=val
        else:
            try:
                erg=eval(str(val)+sub)
            except Exception:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.error("Problem with subexpression:",sys.exc_info()[0],":",e)

        print_(erg)

# Should work with Python3 and Python2
