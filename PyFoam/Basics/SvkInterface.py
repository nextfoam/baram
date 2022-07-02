#  ICE Revision: $Id$
"""A VCS-interface to Mercurial"""

from PyFoam.Error import warning,error,notImplemented

from .GeneralVCSInterface import GeneralVCSInterface

from os import path as opath
import subprocess
import os

class SvkInterface(GeneralVCSInterface):
    """\
The interface class to svk

Only a partial implementation (As much as the BuildHelper needs)"""

    def __init__(self,
                 path,
                 init=False):

        GeneralVCSInterface.__init__(self,path,init)
        if init:
            notImplemented(self,"__init__ (creation of a repository)")

    def getInfo(self,info):
        output=self.doInPath(self.executeWithOuput,"svk info")
        for l in output.split("\n"):
            if l.find(info)==0:
                return l[len(info)+2:]

        return "nix"

    def getRevision(self):
        return self.getInfo("Revision")

    def branchName(self):
        # svk does not have branch names
        return self.getInfo("Depot Path")

    def update(self,
               timeout=None):
        ok=self.doInPath(subprocess.call,["svk","pull"])
        return ok==0

# Should work with Python3 and Python2
