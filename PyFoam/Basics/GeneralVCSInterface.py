#  ICE Revision: $Id$
"""General interface to VCS implementations"""

from PyFoam.Error import notImplemented,error
from os import path,getcwd,chdir
import subprocess,os

from PyFoam.ThirdParty.six import exec_,PY3

class GeneralVCSInterface(object):
    """This is an abstract class that implements an interface to general VCS operations"""

    def __init__(self,
                 path,
                 init=False):
        """:param path: path which is supposed to be under version control
        :param init: initialize the version control system here"""

        if init:
            self.path=path
        else:
            self.path=self.getRoot(path)

    def getRoot(self,path):
        """\
Returns the actual repository root for a path. Default implmentation
passes through the path
"""
        return path

    def executeWithOuput(self,cmd):
        """Executes a command and returns the output"""
        p = subprocess.Popen(cmd,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        result=p.communicate()[0]
        return result.strip()

    def doInPath(self,
                 func,
                 *args,**kwargs):
        """\
Execute a function in the root directory of the repository. Afterwards
change back ot the original directory. Result of the function is returned

:param func: the function to be executed"""
        oldDir=os.getcwd()
        os.chdir(self.path)
        result=func(*args,**kwargs)
        os.chdir(oldDir)
        return result

    def getRevision(self):
        """Get the current revision number"""

        notImplemented(self,"commit")

    def commit(self,
               msg):
        """Commit the current state
        :param msg: Commit message"""

        notImplemented(self,"commit")

    def update(self,
               timeout=None):
        """Update the working copy from the parent repository
        :param timeout: Wait a maximum time (if the VCS supports this)"""

        notImplemented(self,"update")

    def branchName(self):
        """Return the branch-name (or another identifying string)"""


        notImplemented(self,"commit")

    def addPath(self,
                path,
                rules=[]):
        """Add the path to the repository (no commit)
        :param path: the path (directory or file) to commit
        :param rules: a list of tuples: first is whether to include or exclude
        the regular expression that is the second member of the tuple"""

        notImplemented(self,"addPath")

    def clone(self,
              dest):
        """Clone the repository
        :param dest: the path that should be clones to"""

        notImplemented(self,"clone")

    def addRegexpToIgnore(self,
                          expr):
        """Add to the ignore-facility of the current VCS
        :param expr: a regular expression"""

        notImplemented(self,"addRegexpToIgnore")

    def addGlobToIgnore(self,
                          expr):
        """Add to the ignore-facility of the current VCS
        :param expr: a glob expression"""

        notImplemented(self,"addGlobToIgnore")

    def addStandardIgnores(self):
        """Add the usual ignores"""
        self.addGlobToIgnore("*.gz")
        self.addGlobToIgnore("*~")
        self.addGlobToIgnore("*.foam")
        self.addGlobToIgnore("PlyParser*")
        self.addGlobToIgnore("PyFoam*")
        self.addGlobToIgnore("postProcessing")
        self.addRegexpToIgnore(".*\\.logfile")
        self.addRegexpToIgnore(".*\\.analyzed")

def getVCS(vcs,
           path,
           init=False,
           tolerant=False):
    """Factory to create a proper VCS-interface
    :param vcs: name of the VCS-implementation
    :param path: path which is under version control
    :param init: whether the Version-control should be initialized here
    :param tolerant: If there is no interface for the VCS in question return None"""

    table = { "hg"   : "HgInterface" ,
              "git"  : "GitInterface",
              "svn"  : "SvnInterface",
              "svk"  : "SvkInterface" }

    if vcs not in table:
        if tolerant:
            return None
        else:
            error("Unknown VCS",vcs,". Known are",list(table.keys()))

    modName=table[vcs]

    if PY3:
        # fix the import.
        dot="."
    else:
        dot=""
    exec_("from "+dot+modName+" import "+modName)

    return eval(modName+"(path,init)")

def whichVCS(dpath):
    """Diagnose which VCS a specific directory is under

    Returns a string that is consistent with the creation table in getVCS
"""
    if path.exists(path.join(dpath,".svn")):
        return "svn"

    def runTest(test):
        p = subprocess.Popen(test,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        pid, sts = os.waitpid(p.pid, 0)
        return sts

    if not runTest("hg stat -q --cwd %s" % dpath):
        return "hg"

    if not runTest("svk info %s" % dpath):
        return "svk"

    oldDir=getcwd()
    chdir(dpath)
    status=runTest("git rev-parse")
    chdir(oldDir)
    if not status:
        return "git"

    return ""
