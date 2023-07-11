#  ICE Revision: $Id$
"""Working with parameter-files"""

import re,os

from PyFoam.Basics.LineReader import LineReader
from PyFoam.RunDictionary.FileBasis import FileBasisBackup

class ParameterFile(FileBasisBackup):
    """Represents a OpenFOAM parameter file"""

    def __init__(self,name,backup=False):
        """:param name: The name of the parameter file
        :param backup: create a backup-copy of the file"""

        FileBasisBackup.__init__(self,name,backup=backup)

    def parameterPattern(self,parameter):
        """creates a regular expression that looks for aparameter

        parameter - name of the parameter"""
        return re.compile("(.*)\s*"+parameter+"\s+(.*)\s*;(.*)")

    def readParameter(self,parameter):
        """reads the value of a parameter

        parameter - name of the parameter"""
        exp=self.parameterPattern(parameter)

        l=LineReader()
        self.openFile()

        erg=""

        while l.read(self.fh):
            m=exp.match(l.line)
            if m!=None:
                if m.group(1).find(self.removedString)<0:
                    if l.line.find("//")>=0 and l.line.find("//")<l.line.find(parameter):
                        continue
                    erg=m.group(2)
                    break

        self.closeFile()
        return erg

    def replaceParameter(self,parameter,newval):
        """writes the value of a parameter

        :param parameter: name of the parameter
        :param newval: the new value
        :return: old value of the parameter"""

        oldVal=self.readParameter(parameter)

        exp=self.parameterPattern(parameter)

        l=LineReader()
        self.openFile()

        (fh,fn)=self.makeTemp()

        while l.read(self.fh):
            toPrint=l.line

            m=exp.match(l.line)
            if m!=None:
                if m.group(1).find(self.removedString)<0:
                    toPrint =self.removedString+l.line+"\n"
                    toPrint+=parameter+" "+str(newval)+"; "+self.addedString
            fh.write(toPrint+"\n")

        self.closeFile()
        fh.close()
        os.rename(fn,self.name)

        return oldVal
