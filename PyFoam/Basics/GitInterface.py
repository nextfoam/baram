#  ICE Revision: $Id$
"""A VCS-interface to Mercurial"""

from PyFoam.Error import warning,error,notImplemented

from .GeneralVCSInterface import GeneralVCSInterface

from os import path as opath
import subprocess
import os

class GitInterface(GeneralVCSInterface):
    """\
The interface class to git

Only a partial implementation (As much as the BuildHelper needs)"""

    def __init__(self,
                 path,
                 init=False):

        GeneralVCSInterface.__init__(self,path,init)
        if init:
            notImplemented(self,"__init__ (creation of a repository)")


    def getRoot(self,path):
        oldDir=os.getcwd()
        os.chdir(path)
        result=self.executeWithOuput("git rev-parse --show-toplevel")
        os.chdir(oldDir)
        return result

    def branchName(self):
        return self.doInPath(self.executeWithOuput,"git rev-parse --abbrev-ref HEAD")

    def getRevision(self):
        return self.doInPath(self.executeWithOuput,"git rev-parse --short HEAD")

    def update(self,
               timeout=None):
        ok=self.doInPath(subprocess.call,["git","pull"])
        return ok==0


# Should work with Python3 and Python2
