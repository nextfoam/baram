#  ICE Revision: $Id$
"""Stop solver at convergence"""

from .AnalyzedRunner import AnalyzedRunner
from PyFoam.LogAnalysis.SteadyConvergedLineAnalyzer import SteadyConvergedLineAnalyzer

class ConvergenceRunner(AnalyzedRunner):
    """It is assumed that the provided solver is a steady state
    solver. After all the linear solvers have initial residuals below
    their limits the run is assumed to be convergent and the run is
    stopped by setting

    stopAt nextWrite;
    writeInterval 1;

    in the controlDict"""

    def __init__(self,analyzer,
                 argv=None,
                 silent=False,
                 splitThres=2048,
                 split_fraction_unchanged=0.2,
                 logname="PyFoamSolve",
                 server=False,
                 lam=None,
                 restart=False,
                 compressLog=False,
                 noLog=False,
                 logTail=None,
                 remark=None,
                 parameters=None,
                 jobId=None,
                 echoCommandLine=None):
        """See AnalyzedRunner"""
        AnalyzedRunner.__init__(self,
                                analyzer,
                                argv,
                                silent,
                                logname,
                                splitThres=splitThres,
                                split_fraction_unchanged=split_fraction_unchanged,
                                server=server,
                                lam=lam,
                                compressLog=compressLog,
                                restart=restart,
                                noLog=noLog,
                                logTail=logTail,
                                remark=remark,
                                parameters=parameters,
                                echoCommandLine=echoCommandLine,
                                jobId=jobId)

        self.analyzer.addAnalyzer("Convergence", SteadyConvergedLineAnalyzer())

    def lineHandle(self,line):
        """Not to be called: Stops the solver"""
        AnalyzedRunner.lineHandle(self,line)

        if not self.analyzer.goOn():
            self.stopGracefully()

# Should work with Python3 and Python2
