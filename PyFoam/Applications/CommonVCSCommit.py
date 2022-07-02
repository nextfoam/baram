"""
Class that implements the common functionality commiting cases to the VCS
"""

from optparse import OptionGroup
from os import path
import sys

from PyFoam.Basics.GeneralVCSInterface import getVCS

class CommonVCSCommit(object):
    """ The class that defines options for commiting cases
    """

    def addOptions(self):
        grp=OptionGroup(self.parser,
                        "Commit to VCS",
                        "Whether a VCS-controlled case should be commited")
        
        grp.add_option("--commit-to-vcs",
                       action="store_true",
                       dest="commitToVCS",
                       default=False,
                       help="Should the case be commited before further action is taken")
        
        grp.add_option("--message-to-commit",
                       dest="commitMessage",
                       default=None,
                       help="Message that should go along with the commit. If undefined an automatic mesage is used. If undefined implicitly assumes --commit-to-vcs")

        self.parser.add_option_group(grp)

    def checkAndCommit(self,sol,msg=None):
        """
        :param sol: SolutionDirectory that should be commited
        :param msg: The commit message that should be used if none is specified by the user
        """

        if self.opts.commitToVCS or self.opts.commitMessage:
            if msg==None:
                msg=path.basename(sys.argv[0])
                
            if self.opts.commitMessage:
                msg=self.opts.commitMessage+" ("+msg+")"
            vcs=sol.determineVCS()
            if vcs==None:
                self.warning("Case",sol.name,"is not under version control.",
                             "Can not commit with message:",msg)
                return

            vcsInter=getVCS(vcs,
                            path=sol.name)
            vcsInter.commit(msg)
            
            
