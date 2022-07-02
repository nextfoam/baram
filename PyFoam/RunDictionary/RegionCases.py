#  ICE Revision: $Id$
"""Pseudo-Cases for Regions, built from symlinks"""

from .SolutionDirectory import SolutionDirectory
from PyFoam.Error import error
from glob import glob
from PyFoam.Basics.Utilities import rmtree

from os import path,mkdir,symlink,unlink,listdir,renames

class RegionCases:
    """Builds pseudocases for the regions"""

    def __init__(self,sol,clean=False,processorDirs=True):
        """:param sol: solution directory
        :param clean: Remove old pseudo-cases"""

        self.master=sol
        regions=self.master.getRegions()
        if len(regions)<=0:
            error("No regions in",self.master.name)
        if clean:
            self.cleanAll()
        else:
            for r in regions:
                rName=self.master.name+"."+r
                if path.exists(rName):
                    error("Directory",rName,"alread existing. Did not clean up?")

        for r in regions:
            rName=self.master.name+"."+r
            mkdir(rName)

            mkdir(path.join(rName,"system"))
            for f in listdir(self.master.systemDir(region=r)):
                self._mklink(self.master.name,r,"system",prefix=path.pardir,postfix=f)
            symlink(path.join(path.pardir,path.pardir,self.master.name,"system","controlDict"),
                    path.join(rName,"system","controlDict"))
            origSys=path.join(path.pardir,path.pardir,
                              self.master.name,"system")
            for f in listdir(origSys):
                destFile=path.join(rName,"system",f)
                if not path.exists(destFile):
                    symlink(path.join(origSys,f),
                            destFile)

            self._mklink(self.master.name,r,"constant")
            for t in self.master.getTimes():
                self._mklink(self.master.name,r,t)
            if processorDirs:
                for p in self.master.processorDirs():
                    pDir=path.join(self.master.name,p)
                    sDir=path.join(self.master.name+"."+r,p)
                    if not path.exists(sDir):
                        mkdir(sDir)
                    for f in listdir(pDir):
                        self._mklink(self.master.name,r,path.join(p,f),prefix=path.pardir)

    def resyncAll(self):
        """Update the master Case from all the region-cases"""

        for r in self.master.getRegions():
            self.resync(r)

    def resync(self,region):
        """Update the master case from a region case
        :param region: Name of the region"""
        rCase=SolutionDirectory(self.master.name+"."+region)
        rTimes=rCase.getTimes()
        for t in rTimes+["constant"]:
            if path.exists(path.join(rCase.name,t)):
                if not path.exists(path.join(self.master.name,t,region)):
                    self._rename(self.master.name,region,t)
            for p in rCase.processorDirs():
                pDir=path.join(self.master.name,p)
                if not path.exists(pDir):
                    mkdir(pDir)
                    symlink(path.join(path.pardir,"system"),path.join(pDir,"system"))

                if path.exists(path.join(rCase.name,p,t)):
                    if not path.exists(path.join(pDir,region,t)):
                        self._rename(self.master.name,region,t,processor=p,prefix=path.pardir)
                if t=="constant":
                    for f in listdir(path.join(self.master.name,t,region)):
                        if f!="polyMesh":
                            #                            print path.join(pDir,"constant",region,f),"->",path.join(path.pardir,path.pardir,path.pardir,"constant",region,f)
                            #                            print path.exists(path.join(path.join(pDir,"constant",region),path.join(path.pardir,path.pardir,path.pardir,"constant",region,f)))
                            dest=path.join(pDir,"constant",region,f)
                            src=path.join(path.pardir,path.pardir,path.pardir,"constant",region,f)
                            if not path.exists(dest):
                                symlink(src,dest)

    def _mklink(self,master,region,name,prefix="",postfix=""):
        """Makes a link from the master case to the pseudo-case
        :param master: Name of the master directory
        :param region: Name of one region
        :param name: Name of the directory to link
        :param prefix:  A prefix to the path
        :param postfix:  An actual file to the path"""

        destname=path.join(master+"."+region,name)
        srcname=path.join(prefix,path.pardir,master,name,region,postfix)
        if postfix!="":
            destname=path.join(destname,postfix)

        #        print srcname,"->",destname

        symlink(srcname,destname)

        return path.exists(srcname)

    def _rename(self,master,region,name,prefix="",processor=""):
        """Moves a directory from
        :param master: Name of the master directory
        :param region: Name of one region
        :param name: Name of the directory to link
        :param prefix:  A prefix to the path"""

        rName=master+"."+region

        if processor=="":
            destName=path.join(master,name,region)
            srcName=path.join(rName,name)
            prefix=path.pardir
        else:
            destName=path.join(master,processor,name,region)
            srcName=path.join(rName,processor,name)
            prefix=path.join(path.pardir,path.pardir)

        #       print srcName,"->",destName

        if not path.exists(destName):
            renames(srcName,destName)
            symlink(path.join(prefix,destName),srcName)

    def cleanAll(self):
        for r in self.master.getRegions():
            self.clean(r)

    def clean(self,region):
        rmtree(self.master.name+"."+region,ignore_errors=True)

# Should work with Python3 and Python2
