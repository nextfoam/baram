#  ICE Revision: $Id$
"""Basis for the handling of OpenFOAM-files

Transparently accepts gnuzipped files"""

import os,re
from os import path
from tempfile import mktemp
import gzip


from PyFoam.Basics.Utilities import Utilities
from PyFoam.Basics.LineReader import LineReader

from PyFoam.Error import warning,error

from PyFoam.ThirdParty.six import PY3

class FileBasis(Utilities):
    """ Base class for the other OpenFOAM--file-classes"""

    removedString="//PyFoamRemoved: "
    """Comment for lines that were overwritten by PyFoam-routines"""

    addedString="//PyFoamAdded"
    """Comment for lines that were added by PyFoam-routines"""

    def __init__(self,name,
                 createZipped=True,
                 useBinary=False):
        """:param name: Name of the file. If the field is zipped the .gz is
        appended. Alternatively it can be a filehandle
        :param createZipped: if the file doesnot exist: should it be created
        as a zipped file?"""
        self.useBinary=useBinary
        if hasattr(name,"read"):
            self.name=None
            self.exists=True
            self.zipped=None
            self.fh=name
        else:
            self.name = path.abspath(name)
            self.exists = False

            if path.exists(self.name):
                self.exists = True
                self.zipped=False
                if path.splitext(self.name)[1]==".gz":
                    self.zipped=True
                elif path.exists(self.name+".gz"):
                    warning(self.name+".gz","and",self.name,"existing - using the unzipped")
            elif path.exists(self.name+".gz"):
                self.zipped=True
                self.exists = True
            else:
                self.zipped=createZipped

            if path.splitext(self.name)[1]==".gz":
                self.name=self.name[:-3]

            self.fh=None
        self.content=None

    def realName(self):
        """The full filename with appended .gz (if zipped)"""
        if self.name:
            if self.zipped:
                return self.name+".gz"
            else:
                return self.name
        else:
            return str(self.fh)

    def baseName(self):
        """Returns the basic file name (without .gz)"""
        if self.name:
            return path.basename(self.name)
        else:
            return path.basename(self.fh.name)

    def openFile(self,keepContent=False,mode="r"):
        """opens the file. To be overloaded by derived classes"""
        if not keepContent:
            self.content=None
        if self.useBinary and mode.find("b")<0:
            mode+="b"
        elif mode.find("b")>=0:
            self.useBinary=True
        if self.name:
            if self.zipped:
                self.fh=gzip.open(self.name+".gz",mode)
            else:
                self.fh=open(self.name,mode)
        else:
            if mode!="r":
                error("File-handle",str(self.fh),"can only be used with mode 'r'")

    def closeFile(self):
        """ closes the file"""
        self.fh.close()
        self.fh=None

    def readFile(self):
        """ read the whole File into memory"""
        self.openFile()
        txt=self.fh.read()
        if PY3 and self.zipped:
            txt=str(txt,"utf-8")
        elif PY3 and self.useBinary:
            txt=str(txt,encoding="latin-1")
        self.content=self.parse(txt)
        self.closeFile()

    def writeFile(self,content=None):
        """ write the whole File from memory
        :param content: content that should replace the old content"""
        if self.name:
            if content!=None:
                self.content=content
            if self.content!=None:
                self.openFile(keepContent=True,mode="w")
                txt=str(self)
                if bytes!=str and self.useBinary:
                    txt=bytes(txt,"utf-8")
                self.fh.write(self.encode(txt))
                self.closeFile()
        else:
            error("File-handle",str(self.fh),"can not be written")

    def encode(self,txt):
        """Encode a string to byte if necessary (for Python3)"""
        if PY3 and self.zipped and isinstance(txt,(str,)):
            return bytes(txt,"utf-8")
        else:
            return txt

    def writeFileAs(self,name):
        """ Writes a copy of the file. Extends with .gz if the original
        is zipped
        :param name: Name under which the file is written"""
        if self.name:
            if path.abspath(self.name)==path.abspath(name):
                warning(name,"and",self.name,"seem to be the same. Nothing done")
                return

        erase=False
        if self.content==None:
            erase=True
            self.readFile()

        tmp=self.name
        fh=self.fh
        self.name=name
        self.writeFile()
        self.name=tmp
        self.fh=fh

        if erase:
            self.content=None

    def parse(self,cnt):
        """ Parse a string that is to be the content, to be overriden
        by the sub-classes"""

        return cnt

    def __str__(self):
        """Build a string from self.content, to be overriden by sub-classes"""

        return self.content

    def __enter__(self):
        """Making the 'with'-statement happy"""
        return self

    def __exit__(self,typ,value,traceback):
        """Making the 'with'-statement happy"""
        if self.fh!=None:
            self.closeFile()

    def makeTemp(self):
        """creates a temporary file"""
        if self.name:
            fName=self.name
        else:
            fName=self.fh.name

        fn=mktemp(dir=path.dirname(fName))
        if self.zipped:
            fh=gzip.open(fn,"w")
        else:
            fh=open(fn,"w")

        return fh,fn

    def writeEncoded(self,out,txt):
        """Convert the text to 'bytes' is we encounter a zipped file"""
        if PY3:
            if type(out) is gzip.GzipFile:
                txt=bytes(txt,"utf-8")
        out.write(txt)

    def goTo(self,l,s,out=None,echoLast=False,stop=None):
        """Read lines until a token is found

        :param l: a LineReader object
        :param s: the string to look for
        :param out: filehandle to echo the lines to
        :param stop: pattern that indicates that exp will never be found (only passed through to goMatch)
        :param echoLast: echo the line with the string"""
        exp=re.compile("( |^)"+s+"( |$)")
        self.goMatch(l,exp,out=out,stop=stop)
        if out!=None and echoLast:
            self.writeEncoded(out,l.line+"\n")

    def goMatch(self,l,exp,out=None,stop=None):
        """Read lines until a regular expression is matched

        :param l: a LineReader object
        :param exp: the expression to look for
        :param out: filehandle to echo the lines to
        :param stop: pattern that indicates that exp will never be found
        :return: match-object if exp is found, the line if stop is found and None if the end of the file is reached"""
        while l.read(self.fh):
            m=exp.match(l.line)
            if m!=None:
                return m
            elif stop!=None:
                if stop.match(l.line):
                    return l.line
            if out!=None:
                self.writeEncoded(out,l.line+"\n")

        return None

    def copyRest(self,l,out):
        """Copy the rest of the file

        :param l: a LineReader object
        :param out: filehandle to echo the lines to"""
        while l.read(self.fh):
            self.writeEncoded(out,l.line+"\n")

    def purgeFile(self):
        """Undo all the manipulations done by PyFOAM

        Goes through the file and removes all lines that were added"""
        if not self.name:
            error("File-handle",str(self.fh),"can not be purged")

        rmExp= re.compile("^"+self.removedString+"(.*)$")
        addExp=re.compile("^(.*)"+self.addedString+"$")

        l=LineReader()
        self.openFile()

        (fh,fn)=self.makeTemp()

        while l.read(self.fh):
            toPrint=l.line

            m=addExp.match(l.line)
            if m!=None:
                continue

            m=rmExp.match(l.line)
            if m!=None:
                toPrint=m.group(1)

            self.writeEncoded(fh,toPrint+"\n")

        self.closeFile()
        fh.close()
        os.rename(fn,self.name)

    def getCaseDir(self):
        """Return the path to the case of this file (if any valid case is found).
        Else return None"""

        if self.name:
            fName=self.name
        else:
            fName=self.fh.name

        from .SolutionDirectory import NoTouchSolutionDirectory

        caseDir=None
        comp=path.split(fName)[0]
        while len(comp)>1:
            if NoTouchSolutionDirectory(comp).isValid():
                caseDir=comp
                break
            comp=path.split(comp)[0]

        return caseDir

class CleanCharactersFile(FileBasis):
    """Read file and remove characters from the content"""
    def __init__(self,name,charsToRemove):
        """@param charsToRemove: string with characters that should be removed"""
        FileBasis.__init__(self,name)
        self.chars=charsToRemove
        self.readFile()

    def parse(self,cnt):
        for c in self.chars:
            cnt=cnt.replace(c,"")
        return cnt

class FileBasisBackup(FileBasis):
    """A file with a backup-copy"""

    counter={}

    def __init__(self,name,
                 backup=False,
                 createZipped=True,
                 useBinary=False):
        """:param name: The name of the parameter file
        :type name: str
        :param backup: create a backup-copy of the file
        :type backup: boolean"""

        if hasattr(name,"read"):
            if backup:
                warning(str(name),"is a file-handle. No backup possible")
            backup=False

        FileBasis.__init__(self,
                           name,
                           createZipped=createZipped,
                           useBinary=useBinary)

        if backup:
            self.backupName=self.name+".backup"
            try:
                FileBasisBackup.counter[self.name]+=1
            except KeyError:
                FileBasisBackup.counter[self.name]=1
                if self.zipped:
                    self.copyfile(self.name+".gz",self.backupName+".gz")
                else:
                    self.copyfile(self.name,self.backupName)
        else:
            self.backupName=None

    def restore(self):
        """if a backup-copy was made the file is restored from this"""
        if self.backupName is not None:
            FileBasisBackup.counter[self.name] -= 1
            if FileBasisBackup.counter[self.name] == 0:
                if self.zipped:
                    bkpName = self.backupName + ".gz"
                    fileName = self.name + ".gz"
                else:
                    bkpName = self.backupName
                    fileName = self.name

                self.copyfile(bkpName, fileName)
                self.remove(bkpName)
                del FileBasisBackup.counter[self.name]


def exists(name):
    f = FileBasis(name)
    return f.exists

# Should work with Python3 and Python2
