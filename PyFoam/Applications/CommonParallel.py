"""
Class that implements the common functionality for running cases in parallel
"""
from optparse import OptionGroup

from PyFoam.Execution.ParallelExecution import LAMMachine

class CommonParallel(object):
    """ The class that defines options for parallel execution
    """

    def addOptions(self):
        grp=OptionGroup(self.parser,
                        "Parallel",
                        "Defines whether and on how many processors a parallel run should be executed")

        grp.add_option("--procnr",
                       type="int",
                       dest="procnr",
                       default=None,
                       help="The number of processors the run should be started on")

        grp.add_option("--machinefile",
                               dest="machinefile",
                               default=None,
                               help="The machinefile that specifies the parallel machine")

        grp.add_option("--autosense-parallel",
                       action="store_true",
                       dest="autosenseParallel",
                       default=False,
                       help="Automatically determine for how many processors the case is decomposed and start an adequat parallel run")

        self.parser.add_option_group(grp)

    def getParallel(self,sol=None):
        """
:param sol: SolutionDirectory for which the LAMMachine will be
constructed (with autosense)
        """
        lam=None
        if self.opts.procnr!=None or self.opts.machinefile!=None:
            lam=LAMMachine(machines=self.opts.machinefile,nr=self.opts.procnr)
        elif self.opts.autosenseParallel and sol!=None:
            if sol.nrProcs()>1:
                lam=LAMMachine(nr=sol.nrProcs())

        return lam
