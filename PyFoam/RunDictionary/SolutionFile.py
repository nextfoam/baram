#  ICE Revision: $Id$
""" Working with solutions """

import re,os
from os import path

from PyFoam.Basics.LineReader import LineReader
from PyFoam.RunDictionary.FileBasis import FileBasis
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

class SolutionFile(FileBasis):
    """ Solution data file

        Represents a file with the solution data for one
        OpenFOAM-field at one point of time

        Currently this can only handle uniform field values (and never
        will handle more because the ParsedParameterFile-class does a
        much better job)"""

    def __init__(self,directory,name):
        """ :param directory: name of the directory containing the solutions
        for a specific time
        :param name: name of the field."""

        FileBasis.__init__(self,path.abspath(path.join(directory,name)))

    def dimensionPattern(self):
        """pattern for the dimension string"""
        return re.compile("^dimensions +\[(.+)\]\s*;")

    def internalPatternUniform(self):
        """pattern for internal fields"""
        return re.compile("^internalField +uniform +(.+);")

    def internalPattern(self):
        """pattern for internal fields"""
        return re.compile("^internalField +nonuniform .+[0-9]\((.+)\);")

    def internalPatternGeneral(self):
        """general pattern for internal fields"""
        return re.compile("^internalField +(non|)uniform +(.+);")

    def valuePattern(self):
        """pattern for values"""
        return re.compile("value +uniform +(.+);")

    def stopPattern(self):
        """pattern that ends a boundary"""
        return re.compile("^\b*}")

    def readBoundary(self,name):
        """read the value at a boundary

        name - the name of the boundary patch"""
        exp=self.valuePattern()
        erg=""

        l=LineReader()
        self.openFile()

        self.goTo(l,"boundaryField")
        self.goTo(l,name)

        m=self.goMatch(l,exp)
        if m!=None:
            erg=m.group(1)

        self.closeFile()
        return erg

    def replaceBoundary(self,name,newval):
        """write the value at a boundary

        :param name: the name of the boundary patch
        :param newval: the new value"""
        exp=self.valuePattern()

        l=LineReader()
        self.openFile()

        fh,fn=self.makeTemp()

        self.goTo(l,"boundaryField",out=fh,echoLast=True)
        self.goTo(l,name,out=fh,echoLast=True)

        m=self.goMatch(l,exp,out=fh,stop=self.stopPattern())

        if m!=None:
            if type(m)==str:
                self.writeEncoded(fh,"value uniform "+str(newval)+"; "+self.addedString+"\n")
                self.writeEncoded(fh,l.line+"\n")
            else:
                self.writeEncoded(fh,self.removedString+l.line+"\n")
                self.writeEncoded(fh,"value uniform "+str(newval)+"; "+self.addedString+"\n")
        else:
            self.writeEncoded(fh,l.line+"\n")

        self.copyRest(l,fh)

        self.closeFile()
        fh.close()
        os.rename(fn,self.realName())

    def readInternal(self):
        """read the value of the internal field"""
        exp=self.internalPattern()
        erg=""

        l=LineReader()
        self.openFile()

        while l.read(self.fh):
            m=exp.match(l.line)
            if m!=None:
                erg=m.group(1)
                break

        self.closeFile()
        return erg

    def readDimension(self):
        """read the dimension of the field"""
        exp=self.dimensionPattern()
        erg=""

        l=LineReader()
        self.openFile()

        while l.read(self.fh):
            m=exp.match(l.line)
            if m!=None:
                erg=m.group(1)
                break

        self.closeFile()
        return erg

    def getDimensionString(self):
        """builds a dimension string from the dimension information in the file"""
        dim=self.readDimension()
        units=["kg","m","s","K","mol","A","cd"]
        dims=dim.split()

        result=""

        for i in range(len(dims)):
            if float(dims[i])==1.:
                result+=" "+units[i]
            elif float(dims[i])!=0.:
                result+=" "+units[i]+"^"+dims[i]

        if result=="":
            result="1"
        else:
            result=result[1:]

        return result

    def readInternalUniform(self):
        """read the value of the internal field"""
        exp=self.internalPatternUniform()
        erg=""

        l=LineReader()
        self.openFile()

        while l.read(self.fh):
            m=exp.match(l.line)
            if m!=None:
                erg=m.group(1)
                break

        self.closeFile()
        return erg

    def replaceInternal(self,newval):
        """overwrite the value of the internal field

        newval - the new value"""
        exp=self.internalPatternGeneral()

        l=LineReader()
        self.openFile()

        fh,fn=self.makeTemp()

        m=self.goMatch(l,exp,out=fh)

        if m!=None:
            self.writeEncoded(fh,self.removedString+l.line+"\n")
            self.writeEncoded(fh,"internalField uniform "+str(newval)+"; "+self.addedString+"\n")
        else:
            self.writeEncoded(fh,l.line+"\n")

        self.copyRest(l,fh)

        self.closeFile()
        fh.close()
        os.rename(fn,self.realName())

    def getContent(self,
                   treatBinaryAsASCII=False,
                   listLengthUnparsed=None,
                   doMacroExpansion=False):
        """Returns the parsed content of the file"""
        return ParsedParameterFile(self.name,
                                   treatBinaryAsASCII=treatBinaryAsASCII,
                                   listLengthUnparsed=listLengthUnparsed,
                                   doMacroExpansion=doMacroExpansion)

# Should work with Python3 and Python2
