#  ICE Revision: $Id$
"""Working with a solution directory"""

from PyFoam.Basics.Utilities import Utilities
from PyFoam.Basics.BasicFile import BasicFile
from PyFoam.Error import warning,error
from PyFoam import configuration as conf

from PyFoam.RunDictionary.TimeDirectory import TimeDirectory
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile,WriteParameterFile

from PyFoam.Basics.DataStructures import DictProxy

from PyFoam.ThirdParty.six import print_

from os import listdir,path,mkdir,stat,environ
from platform import uname
from time import asctime
from stat import ST_CTIME
import tarfile,fnmatch,glob
import re,os

try:
    from os import getlogin
except ImportError:
    try:
        import PyFoam.ThirdParty.winhacks
    except ImportError:
        print_("Unable to import the getlogin function.")
        import sys
        sys.exit(-1)

class SolutionDirectory(Utilities):
    """Represents a solution directory

    In the solution directory subdirectories whose names are numbers
    are assumed to be solutions for a specific time-step"""

    def __init__(self,
                 name,
                 archive=None,
                 paraviewLink=True,
                 parallel=False,
                 addLocalConfig=False,
                 tolerant=False,
                 region=None):
        """:param name: Name of the solution directory
        :param archive: name of the directory where the lastToArchive-method
        should copy files, if None no archive is created. Deprecated as it was never used
        :param paraviewLink: Create a symbolic link controlDict.foam for paraview
        :param tolerant: do not fail for minor inconsistencies
        :param parallel: use the first processor-subdirectory for the authorative information
        :param region: Mesh region for multi-region cases"""

        self.name=path.abspath(name)
        self.archive=None
        if archive!=None:
            self.archive=path.join(name,archive)
            if not path.exists(self.archive):
                mkdir(self.archive)

        self.region=region
        self.backups=[]

        self.parallel=parallel
        self.tolerant=tolerant

        self.lastReread=0
        self.reread()

        self.dirPrefix=''
        if self.processorDirs() and parallel:
            self.dirPrefix = self.processorDirs()[0]

        self.essential=set([self.systemDir(),
                            self.constantDir()])

        # only add the initial directory if no template exists
        if not path.exists(path.join(self.name,"0.org")) and not self.initialDir() is None:
            self.addToClone(self.initialDir())

        # PyFoam-specific
        self.addToClone("PyFoamHistory")
        self.addToClone("customRegexp")
        self.addToClone("LocalConfigPyFoam")

        # this usually comes with the tutorials
        self.addToClone("Allclean")
        self.addToClone("Allrun")

        self.addToClone("*.ipynb")

        emptyFoamFile=path.join(self.name,path.basename(self.name)+".foam")
        if paraviewLink and not path.exists(emptyFoamFile):
            dummy=open(emptyFoamFile,"w") # equivalent to touch

        if addLocalConfig:
            self.addLocalConfig()

        # These are used by PrepareCase
        self.addToClone("*.org")
        self.addToClone("*.template")
        self.addToClone("*.sh")
        self.addToClone("*.parameters")
        self.addToClone("derivedParameters.py")
        self.addToClone("*.postTemplate")
        self.addToClone("*.finalTemplate")

        self.__postprocDirs=[]
        self.__postprocInfo={}
        self.addPostprocDir(".")
        self.addPostprocDir("postProcessing",fail=False)

    def regions(self):
        """Detect sub-region cases by looking through constant and finding
        directories with polyMesh-directories"""
        regions=[]
        for f in listdir(self.constantDir()):
            fName=path.join(self.constantDir(),f)
            if path.isdir(fName):
                pF=path.join(fName,"polyMesh")
                if path.exists(pF) and path.isdir(pF):
                    if self.region is None:
                        regions.append(f)
                    else:
                        # sub-regions. Do they even exist?
                        regions.append(path.join(self.region,f))
        return regions

    def setToParallel(self):
        """Use the parallel times instead of the serial.

        Used to reset the behaviour after it has been set by the constructor"""
        if self.parallel:
            warning(self.name,"is already in parallel mode")
        else:
            self.parallel=True
            if self.processorDirs():
                self.dirPrefix = self.processorDirs()[0]
            self.reread(force=True)

    def addLocalConfig(self):
        """Add the local configuration file of the case to the configuration"""
        fName=path.join(self.name,"LocalConfigPyFoam")
        if path.exists(fName):
            conf().addFile(fName)

    def __len__(self):
        self.reread()
        return len(self.times)

    def __contains__(self,item):
        self.reread()

        if self.timeName(item)!=None:
            return True
        else:
            return False

    def __getitem__(self,key):
        self.reread()

        ind=self.timeName(key)
        if ind==None:
            raise KeyError(key)
        else:
            return TimeDirectory(self.name, self.fullPath(ind), region=self.region)

    def __setitem__(self,key,value):
        self.reread()
        if type(key)!=str:
            raise TypeError(type(key),"of",key,"is not 'str'")

        if type(value)!=TimeDirectory:
            raise TypeError(type(value),"is not TimeDirectory")

        dest=TimeDirectory(self.name, self.fullPath(key), create=True,region=self.region)
        dest.copy(value)

        self.reread(force=True)

    def __delitem__(self,key):
        self.reread()
        nm=self.timeName(key)
        if nm==None:
            raise KeyError(key)

        self.rmtree(path.join(self.name, self.fullPath(nm)),ignore_errors=True)

        self.reread(force=True)

    def __iter__(self):
        self.reread()
        for key in self.times:
            yield TimeDirectory(self.name,
                                self.fullPath(key),
                                region=self.region,
                                tolerant=self.tolerant)

    def timeName(self,item,minTime=False):
        """Finds the name of a directory that corresponds with the given parameter
        :param item: the time that should be found
        :param minTime: search for the time with the minimal difference.
        Otherwise an exact match will be searched"""

        if type(item)==int:
            return self.times[item]
        else:
            ind=self.timeIndex(item,minTime)
            if ind==None:
                return None
            else:
                return self.times[ind]

    def timeIndex(self,item,minTime=False):
        """Finds the index of a directory that corresponds with the given parameter
        :param item: the time that should be found
        :param minTime: search for the time with the minimal difference.
        Otherwise an exact match will be searched"""
        self.reread()

        time=float(item)
        result=None

        if minTime:
            result=0
            for i in range(1,len(self.times)):
                if abs(float(self.times[result])-time)>abs(float(self.times[i])-time):
                    result=i
        else:
            for i in range(len(self.times)):
                t=self.times[i]
                if abs(float(t)-time)<1e-6:
                    if result==None:
                        result=i
                    elif abs(float(t)-time)<abs(float(self.times[result])-time):
                        result=i

        return result

    def fullPath(self,time):
        if self.dirPrefix:
            return path.join(self.dirPrefix, time)
        return time

    def isValid(self):
        """Checks whether this is a valid case directory by looking for
        the system- and constant-directories and the controlDict-file"""

        return len(self.missingFiles())==0

    def missingFiles(self):
        """Return a list of all the missing files and directories that
        are needed for a valid case"""
        missing=[]
        if not path.exists(self.systemDir()):
            missing.append(self.systemDir())
        elif not path.isdir(self.systemDir()):
            missing.append(self.systemDir())
        if not path.exists(self.constantDir()):
            missing.append(self.constantDir())
        elif not path.isdir(self.constantDir()):
            missing.append(self.constantDir())
        if not path.exists(self.controlDict()) and not path.exists(self.controlDict()+".gz"):
            missing.append(self.controlDict())

        return missing

    def addToClone(self,name):
        """add directory to the list that is needed to clone this case
        :param name: name of the subdirectory (the case directory is prepended)"""
        if path.exists(path.join(self.name,name)):
            self.essential.add(path.join(self.name,name))
        elif self.parallel:
            if path.exists(path.join(self.name,"processor0",name)):
                self.essential.add(path.join(self.name,name))
        else:
            # check whether this is a file pattern
            for f in glob.glob(path.join(self.name,name)):
                # no check for existence necessary
                self.essential.add(f)

    def cloneCase(self,
                  name,
                  svnRemove=True,
                  paraviewLink=True,
                  followSymlinks=False):
        """create a clone of this case directory. Remove the target directory, if it already exists

        :param name: Name of the new case directory
        :param svnRemove: Look for .svn-directories and remove them
        :param followSymlinks: Follow symbolic links instead of just copying them
        :rtype: :class:`SolutionDirectory` or correct subclass
        :return: The target directory"""

        additional=eval(conf().get("Cloning","addItem"))
        for a in additional:
            self.addToClone(a)

        if path.exists(name):
            self.rmtree(name)
        mkdir(name)
        if self.parallel:
            for i in range(self.nrProcs()):
                mkdir(path.join(name,"processor%d" % i))

        for d in self.essential:
            if d!=None:
                fs=followSymlinks
                if fs:
                    noForce=eval(conf().get("Cloning","noForceSymlink"))
                    pth,fl=path.split(d)
                    for n in noForce:
                        if fnmatch.fnmatch(fl,n):
                            fs=False
                            break

                if self.parallel:
                    pth,fl=path.split(d)
                    if path.exists(path.join(pth,"processor0",fl)):
                        for i in range(self.nrProcs()):
                            self.copytree(path.join(pth,"processor%d" % i,fl),
                                          path.join(name,"processor%d" % i),
                                          symlinks=not fs)

                if path.exists(d):
                    self.copytree(d,name,symlinks=not fs)

        if svnRemove:
            self.execute("find "+name+" -name .svn -exec rm -rf {} \\; -prune")

        return self.__class__(name,
                              paraviewLink=paraviewLink,
                              archive=self.archive)

    def symlinkCase(self,
                    name,
                    followSymlinks=False,
                    maxLevel=1,
                    relPath=False):
        """create a clone of this case directory by creating a
        directory with symbolic links

        :param name: Name of the new case directory
        :param maxLevel: Maximum level down to which directories are created instead of symbolically linked
        :param followSymlinks: Follow symbolic links instead of just copying them
        :param relPath: the created symbolic links are relative (instead of absolute)
        :rtype: :class:`SolutionDirectory` or correct subclass
        :return: The target directory
        """
        here=path.abspath(self.name)
        polyDirs=[path.relpath(p,here) for p in self.find("polyMesh*",here)]

        additional=eval(conf().get("Cloning","addItem"))
        for a in additional:
            self.addToClone(a)

        if path.exists(name):
            self.rmtree(name)
        mkdir(name)
        toProcess=[]
        for d in self.essential:
            if d!=None:
                if self.parallel:
                    pth,fl=path.split(d)
                    if path.exists(path.join(pth,"processor0",fl)):
                        for i in range(self.nrProcs()):
                            toProcess.append("processor%d" % i)
                if path.exists(d):
                    toProcess.append(path.relpath(d,here))

        maxLevel=max(0,maxLevel)

        self.__symlinkDir(src=here,
                          dest=path.abspath(name),
                          toProcess=toProcess,
                          maxLevel=maxLevel,
                          relPath=relPath,
                          polyDirs=polyDirs,
                          symlinks=not followSymlinks)

        return self.__class__(name,archive=self.archive)

    def __symlinkDir(self,src,dest,toProcess,maxLevel,relPath,polyDirs,symlinks):
        for f in toProcess:
            there=path.join(src,f)
            here=path.join(dest,f)
            if path.islink(there) and not symlinks:
                there=path.realpath(there)

            doSymlink=False
            done=False

            if not path.isdir(there):
                doSymlink=True
                if path.basename(src)=="polyMesh":
                    if f not in ["blockMeshDict","blockMeshDict.gz"]:
                        doSymlink=False
            else:
                poly=[p for p in polyDirs if p.split(path.sep)[0]==f]
                if maxLevel>0 or len(poly)>0:
                    done=True
                    mkdir(here)
                    self.__symlinkDir(src=there,dest=here,
                                      toProcess=[p for p in os.listdir(there) if p[0]!='.'],
                                      maxLevel=max(0,maxLevel-1),
                                      relPath=relPath,
                                      polyDirs=[path.join(*p.split(path.sep)[1:]) for p in poly if len(p.split(path.sep))>1],
                                      symlinks=symlinks)
                else:
                    doSymlink=True

            if not done:
                if doSymlink:
                    if relPath:
                        linkTo=path.relpath(there,dest)
                    else:
                        linkTo=path.abspath(there)
                    os.symlink(linkTo,here)
                else:
                    self.copytree(there,here,symlinks=symlinks)

    def packCase(self,tarname,
                 last=False,
                 exclude=[],
                 verbose=False,
                 additional=[],
                 base=None):
        """Packs all the important files into a compressed tarfile.
        Uses the essential-list and excludes the .svn-directories.
        Also excludes files ending with ~
        :param tarname: the name of the tar-file
        :param last: add the last directory to the list of directories to be added
        :param exclude: List with additional glob filename-patterns to be excluded
        :param additional: List with additional glob filename-patterns
        that are to be added
        :param base: Different name that is to be used as the baseName for the case inside the tar"""

        ex=["*~",".svn"]+exclude
        members=list(self.essential)
        addClone=eval(conf().get("Cloning","addItem"))
        members+=addClone
        if last:
            if self.getLast()!=self.first:
                if verbose:
                    print_("Adding last ",self.getLast())
                members.append(self.latestDir())
        for p in additional:
            for f in listdir(self.name):
                if (f not in members) and fnmatch.fnmatch(f,p):
                    if verbose:
                        print_("Adding additional",f)
                    members.append(path.join(self.name,f))

        tar=tarfile.open(tarname,"w:gz")

        for m in members:
            self.addToTar(tar,m,
                          verbose=verbose,
                          exclude=ex,base=base)

        additional=eval(conf().get("Cloning","addItem"))
        for a in additional:
            self.addToTar(tar,
                          path.join(self.name,a),
                          verbose=verbose,
                          exclude=ex,
                          base=base)

        tar.close()

    def addToTar(self,tar,pattern,
                 exclude=[],
                 base=None,
                 proc=None,
                 verbose=False):
        """The workhorse for the packCase-method"""

        if base==None:
            base=path.basename(self.name)

        if self.parallel and proc is None:
            for p in self.processorDirs():
                self.addToTar(tar,
                              path.join(path.dirname(pattern),p,path.basename(pattern)),
                              exclude=exclude,
                              base=base,
                              verbose=verbose,
                              proc=p)

        for name in glob.glob(pattern):
            excluded=False
            for e in exclude:
                if fnmatch.fnmatch(path.basename(name),e):
                    excluded=True
            if excluded:
                continue

            if path.isdir(name):
                for m in listdir(name):
                    self.addToTar(tar,
                                  path.join(name,m),
                                  exclude=exclude,
                                  verbose=verbose,
                                  proc=proc,
                                  base=base)
            else:
                arcname=path.join(base,name[len(self.name)+1:])
                if path.islink(name):
                    # if the symbolic link points to a file in the case keep it
                    # otherwise replace with the real file
                    lPath=path.os.readlink(name)
                    if not path.isabs(lPath):
                        rPath=path.realpath(name)
                        common=path.commonprefix([path.abspath(rPath),
                                                  path.abspath(base)])
                        # if the path is shorter than the base it must be outside the case
                        if len(common)<len(path.abspath(base)):
                            name=path.abspath(rPath)
                    else:
                        # use the abolute path
                        name=lPath
                try:
                    tar.getmember(arcname)
                    # don't add ... the file is already there'
                except KeyError:
                    # file not in tar
                    if verbose:
                        print_("Adding",name,"to tar")
                    tar.add(name,arcname=arcname)

    def getParallelTimes(self):
        """Get a list of the times in the processor0-directory"""
        result=[]

        proc0=path.join(self.name,"processor0")
        if path.exists(proc0):
            for f in listdir(proc0):
                try:
                    val=float(f)
                    result.append(f)
                except ValueError:
                    pass
        result.sort(key=float)
        return result

    def reread(self,force=False):
        """Rescan the directory for the time directories"""

        if force:
            del self.procDirs

        if not force and stat(self.name)[ST_CTIME]<=self.lastReread:
            return

        self.times=[]
        self.first=None
        self.firstParallel=None
        self.last=None

        procDirs = self.processorDirs()
        if len(procDirs) > 1:
            self.procNr = len(procDirs)
        elif len(procDirs) == 1:
            self.procNr = int(procDirs[0][len("processors"):])
        else:
            self.procNr = 1

        if procDirs and self.parallel:
            timesDir = path.join(self.name, procDirs[0])
        else:
            timesDir = self.name

        for f in listdir(timesDir):
            try:
                val=float(f)
                self.times.append(f)
            except ValueError:
                pass

        self.lastReread=stat(self.name)[ST_CTIME]

        self.times.sort(key=float)
        if self.times:
            self.first = self.times[0]
            self.last = self.times[-1]

        if self.parallel and len(procDirs)>0:
            parTimes=[]
            for f in listdir(path.join(self.name, procDirs[0])):
                try:
                    val=float(f)
                    parTimes.append(f)
                except ValueError:
                    pass
            if len(parTimes)>0:
                self.firstParallel=min(parTimes)

    def processorDirs(self):
        """List with the processor directories"""
        try:
            return self.procDirs
        except:
            pass
        self.procDirs=[]
        for f in listdir(self.name):
            if re.compile("processor[0-9]+").match(f):
                self.procDirs.append(f)
        self.procDirs.sort(key=lambda x:int(x[len("processor"):]))
        if len(self.procDirs) == 0:
            tmp = []
            for f in listdir(self.name):
                if re.compile("processors[0-9]+").match(f):
                    tmp.append(f)
            if len(tmp) == 1:
                self.procDirs = tmp
        return self.procDirs

    def nrProcs(self):
        """The number of directories with processor-data"""
        self.reread()
        return self.procNr

    def getTimes(self):
        """ :return: List of all the available times"""
        self.reread()
        return self.times

    def addBackup(self,pth):
        """add file to list of files that are to be copied to the
        archive"""
        self.backups.append(path.join(self.name,pth))

    def getFirst(self):
        """:return: the first time for which a solution exists
        :rtype: str"""
        self.reread()
        return self.first

    def getLast(self):
        """:return: the last time for which a solution exists
        :rtype: str"""
        self.reread()
        return self.last

    def lastToArchive(self,name):
        """copy the last solution (plus the backup-files to the
        archive)

        :param name: name of the sub-directory in the archive"""
        if self.archive==None:
            print_("Warning: nor Archive-directory")
            return

        self.reread()
        fname=path.join(self.archive,name)
        if path.exists(fname):
            self.rmtree(fname)
        mkdir(fname)
        self.copytree(path.join(self.name,self.last),fname)
        for f in self.backups:
            self.copytree(f,fname)

    def clearResults(self,
                     after=None,
                     removeProcs=False,
                     keepLast=False,
                     vtk=True,
                     keepRegular=False,
                     keepParallel=False,
                     keepInterval=None,
                     keepTimes=[],
                     functionObjectData=False,
                     dryRun=False,
                     verbose=False,
                     additional=[]):
        """remove all time-directories after a certain time. If not time ist
        set the initial time is used
        :param after: time after which directories ar to be removed
        :param removeProcs: if True the processorX-directories are removed.
        Otherwise the timesteps after last are removed from the
        processor-directories
        :param keepLast: Keep the data from the last timestep
        :param keepInterval: if set: keep timesteps that are this far apart
        :param vtk: Remove the VTK-directory if it exists
        :param keepRegular: keep all the times (only remove processor and other stuff)
        :param functionObjectData: tries do determine which data was written by function obejects and removes it
        :param additional: List with glob-patterns that are removed too"""

        self.reread()

        last=self.getLast()

        if after==None:
            try:
                time=float(self.first)
            except TypeError:
                warning("The first timestep in",self.name," is ",self.first,"not a number. Doing nothing")
                return
        else:
            time=float(after)

        lastKeptIndex=int(-1e5)

        if keepInterval!=None:
            if keepInterval<=0:
                error("The keeping interval",keepInterval,"is smaller that 0")

        if not keepRegular:
            for f in self.times:
                keep=False
                if keepInterval!=None:
                    thisIndex=int((float(f)+1e-10)/keepInterval)
                    if thisIndex!=lastKeptIndex:
                        keep=True
                for k in keepTimes:
                    if self.timeIndex(float(f),True)==self.timeIndex(k,True):
                        keep=True
                if float(f)>time and not (keepLast and f==last) and not keep:
                    #                   print "Removing",path.join(self.name,f)
                    if path.exists(path.join(self.name,f)):
                        if verbose:
                            print_("Clearing",path.join(self.name,f))
                        if not dryRun:
                            self.rmtree(path.join(self.name,f))
                elif keepInterval!=None:
                    lastKeptIndex=int((float(f)+1e-10)/keepInterval)

        if path.exists(path.join(self.name,"VTK")) and vtk:
            if verbose:
                print_("Clearing",path.join(self.name,"VTK"))
            if not dryRun:
                self.rmtree(path.join(self.name,"VTK"))

        if self.nrProcs() and not keepParallel and not self.firstParallel is None:
            lastKeptIndex=int(-1e5)
            time=max(time,float(self.firstParallel))
            for f in listdir(self.name):
                if re.compile("processor(|s)[0-9]+").match(f):
                    if removeProcs:
                        if verbose:
                            print_("Clearing",path.join(self.name,f))
                        if not dryRun:
                            self.rmtree(path.join(self.name,f))
                    else:
                        pDir=path.join(self.name,f)
                        for t in listdir(pDir):
                            try:
                                keep=False
                                val=float(t)
                                if keepInterval!=None:
                                    thisIndex=int((float(t)+1e-10)/keepInterval)
                                    if thisIndex!=lastKeptIndex:
                                        keep=True
                                for k in keepTimes:
                                    if self.timeIndex(val,True)==self.timeIndex(k,True):
                                        keep=True
                                if val>time and not (keepLast and t==last) and not keep:
                                    if path.exists(path.join(pDir,t)):
                                        if verbose:
                                            print_("Clearing",path.join(pDir,t))
                                        if not dryRun:
                                            self.rmtree(path.join(pDir,t))
                                elif keepInterval!=None:
                                    lastKeptIndex=int((float(t)+1e-10)/keepInterval)
                            except ValueError:
                                pass

        if functionObjectData:
            cd=ParsedParameterFile(self.controlDict(),doMacroExpansion=True)
            if "functions" in cd:
                if type(cd["functions"]) in [DictProxy,dict]:
                    for f in cd["functions"]:
                        pth=path.join(self.name,f)
                        if path.exists(pth):
                            if verbose:
                                print_("Clearing",pth)
                            if not dryRun:
                                self.rmtree(pth)
                else:
                    for f in cd["functions"][0::2]:
                        pth=path.join(self.name,f)
                        if path.exists(pth):
                            if verbose:
                                print_("Clearing",pth)
                            if not dryRun:
                                self.rmtree(pth)

        additional+=eval(conf().get("Clearing","additionalpatterns"))
        for a in additional:
            self.clearPattern(a,
                              dryRun=dryRun,
                              verbose=verbose)

    def clearPattern(self,
                     globPat,
                     dryRun=False,
                     verbose=False):
        """Clear all files that fit a certain shell (glob) pattern
        :param glob: the pattern which the files are going to fit"""

        for f in glob.glob(path.join(self.name,globPat)):
            if verbose:
                print_("Clearing",f)
            if not dryRun:
                if path.isdir(f):
                    self.rmtree(f,ignore_errors=False)
                else:
                    os.unlink(f)

    def clearOther(self,
                   pyfoam=True,
                   removeAnalyzed=False,
                   verbose=False,
                   dryRun=False,
                   clearHistory=False,
                   clearParameters=False):
        """Remove additional directories
        :param pyfoam: rremove all directories typically created by PyFoam"""

        if pyfoam:
            self.clearPattern("PyFoam.?*",
                              dryRun=dryRun,
                              verbose=verbose)
            if removeAnalyzed:
                self.clearPattern("*?.analyzed",
                                  dryRun=dryRun,
                                  verbose=verbose)
        if clearParameters:
            self.clearPattern("PyFoamPrepareCaseParameters",
                              dryRun=dryRun,
                              verbose=verbose)
        if clearHistory:
            self.clearPattern("PyFoamHistory",
                              dryRun=dryRun,
                              verbose=verbose)

    def clear(self,
              after=None,
              processor=True,
              pyfoam=True,
              keepLast=False,
              vtk=True,
              verbose=False,
              keepRegular=False,
              keepParallel=False,
              keepInterval=None,
              keepTimes=[],
              removeAnalyzed=False,
              clearHistory=False,
              clearParameters=False,
              functionObjectData=False,
              dryRun=False,
              additional=[]):
        """One-stop-shop to remove data
        :param after: time after which directories ar to be removed
        :param processor: remove the processorXX directories
        :param pyfoam: rremove all directories typically created by PyFoam
        :param keepLast: Keep the last time-step
        :param additional: list with additional patterns to clear"""
        self.clearResults(after=after,
                          removeProcs=processor,
                          keepLast=keepLast,
                          keepInterval=keepInterval,
                          keepTimes=keepTimes,
                          vtk=vtk,
                          verbose=verbose,
                          keepRegular=keepRegular,
                          keepParallel=keepParallel,
                          functionObjectData=functionObjectData,
                          dryRun=dryRun,
                          additional=additional)
        self.clearOther(pyfoam=pyfoam,
                        removeAnalyzed=removeAnalyzed,
                        clearParameters=clearParameters,
                        clearHistory=clearHistory,
                        dryRun=dryRun,
                        verbose=verbose)

    def initialDir(self):
        """:return: the name of the first time-directory (==initial
        conditions)
        :rtype: str"""
        self.reread()

        if self.first:
            return path.join(self.name,self.first)
        else:
            if path.exists(path.join(self.name,"0.org")):
                return path.join(self.name,"0.org")
            else:
                return None

    def latestDir(self):
        """:return: the name of the first last-directory (==simulation
        results)
        :rtype: str"""
        self.reread()

        last=self.getLast()
        if last:
            return path.join(self.name,last)
        else:
            return None

    def constantDir(self,region=None,processor=None):
        """:param region: Specify the region for cases with more than 1 mesh
        :param processor: name of the processor directory
        :return: the name of the C{constant}-directory
        :rtype: str"""
        pre=self.name
        if processor!=None:
            if type(processor)==int:
                processor="processor%d" % processor
            pre=path.join(pre,processor)

        if region==None and self.region!=None:
            region=self.region
        if region:
            return path.join(pre,"constant",region)
        else:
            return path.join(pre,"constant")

    def systemDir(self,region=None,noRegion=False):
        """:param region: Specify the region for cases with more than 1 mesh
        :return: the name of the C{system}-directory
        :rtype: str"""
        if region==None and self.region!=None:
            region=self.region
        if region and not noRegion:
            return path.join(self.name,"system",region)
        else:
            return path.join(self.name,"system")

    def controlDict(self):
        """:return: the name of the C{controlDict}
        :rtype: str"""
        return path.join(self.systemDir(noRegion=True),"controlDict")

    def polyMeshDir(self,region=None,time=None,processor=None):
        """:param region: Specify the region for cases with more than 1 mesh
        :return: the name of the C{polyMesh}
        :param time: Time for which the  mesh should be looked at
        :param processor: Name of the processor directory for decomposed cases
        :rtype: str"""
        if region==None and self.region!=None:
            region=self.region
        if time==None:
            return path.join(
                self.constantDir(
                    region=region,
                    processor=processor),
                "polyMesh")
        else:
            return path.join(
                TimeDirectory(self.name,
                              time,
                              region=region,
                              processor=processor).name,
                "polyMesh")

    def boundaryDict(self,region=None,time=None,processor=None):
        """:param region: Specify the region for cases with more than 1 mesh
        :return: name of the C{boundary}-file
        :rtype: str"""
        if region==None and self.region!=None:
            region=self.region
        return path.join(self.polyMeshDir(region=region,time=time,processor=processor),"boundary")

    def blockMesh(self,region=None):
        """:param region: Specify the region for cases with more than 1 mesh
        :return: the name of the C{blockMeshDict} if it exists. Returns
        an empty string if it doesn't
        :rtype: str"""
        if region==None and self.region!=None:
            region=self.region
        for d in [self.systemDir(region=region),self.polyMeshDir(region=region)]:
            p=path.join(d,"blockMeshDict")
            if path.exists(p):
                return p
        return ""

    def makeFile(self,name):
        """create a file in the solution directory and return a
        corresponding BasicFile-object

        :param name: Name of the file
        :rtype: :class:`BasicFile`"""
        return BasicFile(path.join(self.name,name))

    def getRegions(self,defaultRegion=False):
        """Gets a list of all the available mesh regions by checking all
        directories in constant and using all those that have a polyMesh-subdirectory
        :param defaultRegion: should the default region also be added (as None)"""
        lst=[]
        for d in self.listDirectory(self.constantDir()):
            if path.isdir(path.join(self.constantDir(),d)):
                if path.exists(self.polyMeshDir(region=d)):
                    lst.append(d)

        if defaultRegion:
            if path.exists(self.polyMeshDir()):
                lst.append(None)

        lst.sort()
        return lst

    def addToHistory(self,*text):
        """Adds a line with date and username to a file 'PyFoamHistory'
        that resides in the local directory"""
        hist=open(path.join(self.name,"PyFoamHistory"),"a")

        try:
            # this seems to fail when no stdin is available
            username=getlogin()
        except OSError:
            try:
                username=environ["USER"]
            except KeyError:
                username="unknown"
        hist.write("%s by %s in %s :" % (asctime(),username,uname()[1]))

        for t in text:
            hist.write(str(t)+" ")

        hist.write("\n")
        hist.close()

    def listFiles(self,directory=None):
        """List all the plain files (not directories) in a subdirectory
        of the case
        :param directory: the subdirectory. If unspecified the
        case-directory itself is used
        :return: List with the plain filenames"""

        result=[]
        theDir=self.name
        if directory:
            theDir=path.join(theDir,directory)

        for f in listdir(theDir):
            if f[0]!='.' and f[-1]!='~':
                if path.isfile(path.join(theDir,f)):
                    result.append(f)

        return result

    def getDictionaryText(self,directory,name):
        """:param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :return: the contents of the file as a big string"""

        result=None
        theDir=self.name
        if directory:
            theDir=path.join(theDir,directory)

        if path.exists(path.join(theDir,name)):
            result=open(path.join(theDir,name)).read()
        else:
            warning("File",name,"does not exist in directory",directory,"of case",self.name)

        return result

    def writeDictionaryContents(self,directory,name,contents):
        """Writes the contents of a dictionary
        :param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :param contents: Python-dictionary with the dictionary contents"""

        theDir=self.name
        if directory:
            theDir=path.join(theDir,directory)

        result=WriteParameterFile(path.join(theDir,name))
        result.content=contents
        result.writeFile()

    def writeDictionaryText(self,directory,name,text):
        """Writes the contents of a dictionary
        :param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :param text: String with the dictionary contents"""

        theDir=self.name
        if directory:
            theDir=path.join(theDir,directory)

        result=open(path.join(theDir,name),"w").write(text)

    def getDictionaryContents(self,directory,name):
        """:param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :return: the contents of the file as a python data-structure"""

        result={}
        theDir=self.name
        if directory:
            theDir=path.join(theDir,directory)

        if path.exists(path.join(theDir,name)) or path.exists(path.join(theDir,name+".gz")):
            result=ParsedParameterFile(path.join(theDir,name)).content
        else:
            warning("File",name,"does not exist in directory",directory,"of case",self.name)

        return result

    def determineVCS(self):
        """Find out whether this directory is controlled by a VCS and
        return the abbreviation of that VCS"""

        if path.isdir(path.join(self.name,".hg")):
            return "hg"
        elif path.isdir(path.join(self.name,".git")):
            return "git"
        elif path.isdir(path.join(self.name,".svn")):
            return "svn"
        else:
            return None

    def addPostprocDir(self,dirName,fail=True):
        if dirName in self.__postprocDirs:
            return
        full=path.join(self.name,dirName)
        if not path.isdir(full):
            if fail:
                error(full,"does not exist or is no directory")
            else:
                return

        self.__postprocDirs.append(dirName)
        self.__postprocInfo={}

    def __classifyDirectory(self,dPath):
        cnt=0
        minimum="1e40"
        for d in listdir(dPath):
            full=path.join(dPath,d)
            if not path.isdir(full):
                continue
            try:
                if float(d)<float(minimum):
                    minimum=d
                cnt+=1
            except ValueError:
                continue
        if cnt<=0:
            return None
        first=path.join(dPath,minimum)
        hypothesis=None
        for f in listdir(first):
            ff=path.join(first,f)
            if not path.isfile(ff):
                continue
            try:
                float(f)
                continue
            except ValueError:
                pass
            b,e=path.splitext(f)
            if e==".xy":
                newHypothesis="sample"
            elif e==".vtk":
                newHypothesis="surface"
            elif e=="":
                if b.find("istribution")>0:
                    newHypothesis="distribution"
                else:
                    newHypothesis="timeline"
            else:
                newHypothesis=None

            if hypothesis==None:
                hypothesis=newHypothesis
            elif hypothesis!=newHypothesis and newHypothesis:
                error("Can not decide between",hypothesis,
                "and",newHypothesis,"for",full)
        return hypothesis

    def __scanForPostproc(self,dirName):
        for d in listdir(path.join(self.name,dirName)):
            full=path.join(self.name,dirName,d)
            if not path.isdir(full):
                continue
            try:
                # we don't want time directories
                float(d)
                continue
            except ValueError:
                pass
            c=self.__classifyDirectory(full)
            use=path.join(dirName,d)
            if c=="timeline":
                self.__postprocInfo["timelines"].append(use)
            elif c=="sample":
                self.__postprocInfo["samples"].append(use)
            elif c=="surface":
                self.__postprocInfo["surfaces"].append(use)
            elif c=="distribution":
                self.__postprocInfo["distributions"].append(use)
            elif c==None:
                pass
            else:
                error("Unknown classification",c,"for",full)

            # Pick up additional distributions certain swak-functionobjects generate
            if path.exists(path.join(full,"distributions")):
                c=self.__classifyDirectory(path.join(full,"distributions"))
                if c=="distribution":
                    self.__postprocInfo["distributions"].append(path.join(use,"distributions"))

    def __scanPostproc(self):
        self.__postprocInfo={"timelines":[],
                             "samples":[],
                             "distributions":[],
                             "surfaces":[]}
        for d in self.__postprocDirs:
            self.__scanForPostproc(d)

    @property
    def pickledData(self):
        """Get the pickled data files. Newest first"""
        dirAndTime=[]
        for f in ["pickledData","pickledUnfinishedData","pickledStartData"]:
            for g in glob.glob(path.join(self.name,"*.analyzed")):
                pName=path.join(g,f)
                if path.exists(pName):
                    dirAndTime.append((path.getmtime(pName),pName))
        dirAndTime.sort(key=lambda x:x[0],reverse=True)
        return [s[len(self.name)+1:] for t,s in dirAndTime]

    @property
    def pickledPlots(self):
        """Get the pickled plot files. Newest first"""
        dirAndTime=[]
        for g in glob.glob(path.join(self.name,"*.analyzed")):
            pName=path.join(g,"pickledPlots")
            if path.exists(pName):
                dirAndTime.append((path.getmtime(pName),pName))
        dirAndTime.sort(key=lambda x:x[0],reverse=True)
        return [s[len(self.name)+1:] for t,s in dirAndTime]

    @property
    def timelines(self):
        """Return sub-directories that contain timeline-data"""
        if "timelines" not in self.__postprocInfo:
            self.__scanPostproc()
        return self.__postprocInfo["timelines"]

    @property
    def distributions(self):
        """Return sub-directories that contain distribution-data"""
        if "distributions" not in self.__postprocInfo:
            self.__scanPostproc()
        return self.__postprocInfo["distributions"]

    @property
    def samples(self):
        """Return sub-directories that contain sample-data"""
        if "samples" not in self.__postprocInfo:
            self.__scanPostproc()
        return self.__postprocInfo["samples"]

    @property
    def surfaces(self):
        if "surfaces" not in self.__postprocInfo:
            self.__scanPostproc()
        return self.__postprocInfo["surfaces"]

    def getParametersFromFile(self):
        """Get Parameters from the file created by PrepareCase"""
        fName=path.join(self.name,"PyFoamPrepareCaseParameters")
        if path.exists(fName):
            return ParsedParameterFile(fName,noHeader=True).content
        else:
            return {}

class ChemkinSolutionDirectory(SolutionDirectory):
    """Solution directory with a directory for the Chemkin-files"""

    chemkinName = "chemkin"

    def __init__(self,name,archive="ArchiveDir"):
        SolutionDirectory.__init__(self,name,archive=archive)

        self.addToClone(self.chemkinName)

    def chemkinDir(self):
        """:rtype: str
        :return: The directory with the Chemkin-Files"""

        return path.join(self.name,self.chemkinName)

class NoTouchSolutionDirectory(SolutionDirectory):
    """Convenience class that makes sure that nothing new is created"""

    def __init__(self,
                 name,
                 region=None):
        SolutionDirectory.__init__(self,
                                  name,
                                  archive=None,
                                  paraviewLink=False,
                                  region=region)

# Should work with Python3 and Python2
