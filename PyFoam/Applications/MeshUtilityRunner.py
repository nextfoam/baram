#  ICE Revision: $Id$
"""
Application class that implements pyFoamMeshUtilityRunner
"""

from os import listdir,path,system

from .PyFoamApplication import PyFoamApplication

from PyFoam.Execution.BasicRunner import BasicRunner
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from .CommonLibFunctionTrigger import CommonLibFunctionTrigger
from .CommonServer import CommonServer
from .CommonVCSCommit import CommonVCSCommit

from PyFoam.ThirdParty.six import print_

class MeshUtilityRunner(PyFoamApplication,
                        CommonServer,
                        CommonLibFunctionTrigger,
                        CommonVCSCommit):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs an OpenFoam utility that manipulates meshes.  Needs the usual 3
arguments (<solver> <directory> <case>) and passes them on (plus
additional arguments).

Output is sent to stdout and a logfile inside the case directory
(PyFoamMeshUtility.logfile)

Before running it clears all timesteps but the first.

After the utility ran it moves all the data from the
polyMesh-directory of the first time-step to the
constant/polyMesh-directory

ATTENTION: This utility erases quite a lot of data without asking and
should therefor be used with care
        """

        PyFoamApplication.__init__(self,
                                   exactNr=False,
                                   args=args,
                                   description=description,
                                   **kwargs)

    def addOptions(self):
        CommonLibFunctionTrigger.addOptions(self)
        CommonServer.addOptions(self,False)
        CommonVCSCommit.addOptions(self)

    def run(self):
        cName=self.parser.casePath()

        self.checkCase(cName)

        sol=SolutionDirectory(cName,archive=None)

        print_("Clearing out old timesteps ....")

        sol.clearResults()

        self.checkAndCommit(SolutionDirectory(cName,archive=None))

        run=BasicRunner(argv=self.parser.getArgs(),
                        server=self.opts.server,
                        logname="PyFoamMeshUtility")

        self.addLibFunctionTrigger(run,sol)

        self.addToCaseLog(cName,"Starting")

        run.start()

        self.setData(run.data)

        sol.reread(force=True)

        self.addToCaseLog(cName,"Ending")

        if sol.latestDir()!=sol.initialDir():
            for f in listdir(path.join(sol.latestDir(),"polyMesh")):
                system("mv -f "+path.join(sol.latestDir(),"polyMesh",f)+" "+sol.polyMeshDir())

            print_("\nClearing out new timesteps ....")

            sol.clearResults()
        else:
            print_("\n\n  No new timestep. Utility propably failed")

# Should work with Python3 and Python2
