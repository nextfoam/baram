#  ICE Revision: $Id$
"""Analyze standard solver"""

from .FoamLogAnalyzer import FoamLogAnalyzer

from .ContinuityLineAnalyzer import GeneralContinuityLineAnalyzer
from .LinearSolverLineAnalyzer import GeneralLinearSolverLineAnalyzer,GeneralLinearSolverIterationsLineAnalyzer
from .ExecutionTimeLineAnalyzer import GeneralExecutionLineAnalyzer
from .DeltaTLineAnalyzer import GeneralDeltaTLineAnalyzer

class StandardLogAnalyzer(FoamLogAnalyzer):
    """
    The analyzer for the most common OpenFOAM solvers

    It checks:
     - Continuity
     - the Linear solvers
     - Execution time
    """
    def __init__(self,
                 progress=False,
                 doTimelines=False,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        """
        :param progress: Print time progress on console?
        :param doTimelines: generate timelines?
        :param doFiles: generate files?
        """
        FoamLogAnalyzer.__init__(self,progress=progress)

        self.addAnalyzer("Continuity",
                         GeneralContinuityLineAnalyzer(doTimelines=doTimelines,
                                                       doFiles=doFiles,
                                                       singleFile=singleFile,
                                                       startTime=startTime,
                                                       endTime=endTime))
        self.addAnalyzer("Linear",
                         GeneralLinearSolverLineAnalyzer(doTimelines=doTimelines,
                                                         doFiles=doFiles,
                                                         singleFile=singleFile,
                                                         startTime=startTime,
                                                         endTime=endTime))
        self.addAnalyzer("Iterations",
                         GeneralLinearSolverIterationsLineAnalyzer(doTimelines=doTimelines,
                                                                   doFiles=doFiles,
                                                                   singleFile=singleFile,
                                                                   startTime=startTime,
                                                                   endTime=endTime))
        self.addAnalyzer("Execution",
                         GeneralExecutionLineAnalyzer(doTimelines=doTimelines,
                                                      doFiles=doFiles,
                                                      singleFile=singleFile,
                                                      startTime=startTime,
                                                      endTime=endTime))
        self.addAnalyzer("DeltaT",
                         GeneralDeltaTLineAnalyzer(doTimelines=doTimelines,
                                                   doFiles=doFiles,
                                                   singleFile=singleFile,
                                                   startTime=startTime,
                                                   endTime=endTime))

class StandardPlotLogAnalyzer(StandardLogAnalyzer):
    """This analyzer checks the current residuals and generates timelines"""
    def __init__(self):
        StandardLogAnalyzer.__init__(self,progress=True,doTimelines=True,doFiles=False)

##        self.addAnalyzer("PlotContinuity",GeneralContinuityLineAnalyzer())
##        self.addAnalyzer("PlotLinear",GeneralLinearSolverLineAnalyzer())
##        self.addAnalyzer("PlotIterations",GeneralLinearSolverIterationsLineAnalyzer())
##        self.addAnalyzer("PlotExecution",GeneralExecutionLineAnalyzer())


# Should work with Python3 and Python2
