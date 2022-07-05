"""
Application-class that implements pyFoamInitVCSCase.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from PyFoam.Basics.GeneralVCSInterface import getVCS

from os import path
from glob import glob

ruleList=[(False,".*\\.gz$"),
          (False,".+~$")]

def addRegexpInclude(option,opt,value,parser,*args,**kwargs):
    ruleList.append((True,value))

def addRegexpExclude(option,opt,value,parser,*args,**kwargs):
    ruleList.append((False,value))

class InitVCSCase(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
This utility initializes a Version Control System (VCS) in an
OpenFOAM-directory. Certain parts of PyFoam take advantages of this.

Currenty only Mercurial is supported as a VCS-backend
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <caseDirectory>",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=1,
                                   exactNr=False,
                                   **kwargs)

    def addOptions(self):
        what=OptionGroup(self.parser,
                         "What",
                         "What should be added to version control")
        self.parser.add_option_group(what)

        what.add_option("--include-files",
                        action="callback",
                        callback=addRegexpInclude,
                        type="string",
                        help="Files that should be added in instead of the usual suspects (Regular expression)")
        what.add_option("--exclude-files",
                        action="callback",
                        callback=addRegexpExclude,
                        type="string",
                        help="Files that should not be added (regular expression)")
        what.add_option("--additional",
                        action="append",
                        dest="additional",
                        default=[],
                        help="Additional files and directories to be added")

        vcs=OptionGroup(self.parser,
                        "VCS System",
                        "Control the source-control system")
        self.parser.add_option_group(vcs)

        vcs.add_option("--no-init",
                       action="store_false",
                       default=True,
                       dest="init",
                       help="Don't initialize the repository (assumes that it is already under source control)")

        self.vcsChoices=["hg"]
        vcs.add_option("--vcs",
                       type="choice",
                       default="hg",
                       dest="vcs",
                       action="store",
                       choices=self.vcsChoices,
                       help="Which VCS should be used (Choices: "+", ".join(self.vcsChoices)+") Default: %default")

        how=OptionGroup(self.parser,
                        "Behaviour",
                        "What should be done")
        self.parser.add_option_group(vcs)

        vcs.add_option("--commit-message",
                       action="store",
                       default="Initial commit",
                       dest="commitMessage",
                       help="Message that should be added to the initial commit")

    def run(self):
        sol=SolutionDirectory(self.parser.getArgs()[0])
        if not self.opts.init:
            vcs=sol.determineVCS()
            if vcs==None:
                self.error("not under version control")
            if not vcs in self.vcsChoices:
                self.error("Unsupported VCS",vcs)
        else:
            vcs=self.opts.vcs

        vcsInter=getVCS(vcs,
                        path=sol.name,
                        init=self.opts.init)

        vcsInter.addPath(path.join(sol.name,"constant"),rules=ruleList)
        vcsInter.addPath(path.join(sol.name,"system"),rules=ruleList)
        if sol.initialDir()!=None:
            vcsInter.addPath(sol.initialDir(),rules=ruleList)
        else:
            self.warning("No initial-directory found")

        # special PyFoam-files
        for f in ["customRegexp","LocalConfigPyFoam"]:
            p=path.join(sol.name,f)
            if path.exists(p):
                vcsInter.addPath(p,rules=ruleList)

        # Add the usual files from the tutorials
        for g in ["Allrun*","Allclean*"]:
            for f in glob(path.join(sol.name,g)):
                vcsInter.addPath(f,rules=ruleList)

        for a in self.opts.additional:
            vcsInter.addPath(a,rules=ruleList)

        vcsInter.commit(self.opts.commitMessage)

# Should work with Python3 and Python2
