#  ICE Revision: $Id$
"""Working with direcotries from a time-step"""

from PyFoam.RunDictionary.SolutionFile import SolutionFile
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.RunDictionary.FileBasis import FileBasis
from PyFoam.Error import error,warning
from PyFoam.Basics.Utilities import remove

from os import listdir,stat,path,makedirs
from stat import ST_CTIME
from fnmatch import fnmatch

class TimeDirectory(object):
    """Represents a directory for a timestep"""

    def __init__(self,
                 name,
                 time,
                 create=False,
                 region=None,
                 processor=None,
                 tolerant=False,
                 yieldParsedFiles=False):
        """:param name: name of the case directory
        :param time: time in the directory
        :param create: Create the directory if it does not exist
        :param tolerant: Do not fail if there are inconsistencies
        :param region: The mesh region for multi-region cases
        :param yieldParsedFiles: let the iterator return PasedParameterFile objects instead of SolutionFile"""

        self.name=name
        self.yieldParsedFiles=yieldParsedFiles
        if processor!=None:
            if type(processor)==int:
                processor="processor%d" % processor
            self.name=path.join(self.name,processor)
        self.name=path.join(self.name,time)
        if region!=None:
            self.name=path.join(self.name,region)

        if path.exists(self.name):
            if not path.isdir(self.name):
                error(self.name,"is not a directory")
        elif create:
            makedirs(self.name)
        else:
            error(self.name,"does not exist")

        self.values=[]

        self.lastReread=0
        self.tolerant=tolerant
        self.reread()

    def baseName(self):
        """The name of the directory"""
        return path.basename(self.name)

    def reread(self,force=False):
        """Scan the directory for files with valid names"""

        if not force and stat(self.name)[ST_CTIME]<=self.lastReread:
            return

        self.values=[]

        ex=["*~",".svn"]

        for f in listdir(self.name):
            matched=False
            for e in ex:
                if fnmatch(f,e):
                    matched=True

            if path.isdir(path.join(self.name,f)):
                continue

            if not matched:
                nm=f
                if len(nm)>3:
                    if nm[-3:]==".gz":
                        nm=nm[:-3]
                if nm not in self.values:
                    self.values.append(nm)
                else:
                    if not self.tolerant:
                        error(nm," already found, propably exists as zipped and unzipped")
                    else:
                        warning(nm," already found, propably exists as zipped and unzipped")

        self.values.sort()

        self.lastReread=stat(self.name)[ST_CTIME]

    def getFiles(self):
        """Get a list of the solution files in that directory"""

        return self.values

    def __contains__(self,item):
        self.reread()
        return item in self.values

    def __len__(self):
        self.reread()
        return len(self.values)

    def __getitem__(self,key):
        self.reread()
        if type(key)!=str:
            raise TypeError(type(key),"of",key,"is not 'str'")

        if key not in self.values:
            raise KeyError(key)
        else:
            return SolutionFile(self.name,key)

    def __remove(self,key):
        f=path.join(self.name,key)
        if path.exists(f):
            remove(f)
        elif path.exists(f+".gz"):
            remove(f+".gz")
        else:
            error("Problem:",key,"(",f,") is supposed to exists, but no file found")
        self.values.remove(key)

    def __delitem__(self,key):
        self.reread()
        if key in self.values:
            self.__remove(key)
        else:
            raise KeyError(key)

        self.reread(force=True)

    def __setitem__(self,key,value):
        self.reread()
        if type(key)!=str:
            raise TypeError(type(key),"of",key,"is not 'str'")

        if key in self.values:
            self.__remove(key)

        if FileBasis in value.__class__.__mro__:
            value.writeFileAs(path.join(self.name,key))
        else:
            f=FileBasis(path.join(self.name,key))
            f.writeFile(str(value))
        self.reread(force=True)

    def __iter__(self):
        self.reread()
        for key in self.values:
            if self.yieldParsedFiles:
                yield ParsedParameterFile(path.join(self.name,key))
            else:
                yield SolutionFile(self.name,key)

    def clear(self):
        """Wipe the directory clean"""

        for v in self.values:
            nm=path.join(self.name,v)
            remove(nm)
            remove(nm+".gz")

        self.reread(force=True)

    def copy(self,orig,purge=False,overwrite=True,mustExist=False,exclude=[],include=['*']):
        """Copy SolutionFiles from another TimeDirectory to the
        current TimeDirectory. Returns a list with the copied values
        :param orig: the TimeDirectory with the original files
        :param purge: remove all current files in this directory
        :param overwrite: if the file already exists it is overwritten
        :param mustExist: only if the file already exists it is overwritten
        :param exclude: List of fnmatch-patterns that should be excluded
        (Default: none)
        :param include: List of fnmatch-patterns that should be included
        (Default: all)"""

        if not overwrite and mustExist:
            warning("The options mustExist needs the option overwrite")
            overwrite=True

        if type(orig)!=TimeDirectory:
            raise TypeError(type(value),"is not TimeDirectory")

        if purge:
            self.clear()

        copied=[]

        for v in orig:
            nm=v.baseName()

            doIt=False

            for p in include:
                if fnmatch(nm,p):
                    doIt=True

            for p in exclude:
                if fnmatch(nm,p):
                    doIt=False

            if not overwrite and nm in self:
                doIt=False

            if mustExist and nm not in self:
                doIt=False

            if doIt:
                copied.append(nm)
                self[nm]=v

        return copied

# Should work with Python3 and Python2