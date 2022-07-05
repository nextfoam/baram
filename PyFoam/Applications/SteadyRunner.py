#  ICE Revision: $Id$
"""
Application class that implements pyFoamSteadyRunner
"""

from .PyFoamApplication import PyFoamApplication

from PyFoam.Execution.ConvergenceRunner import ConvergenceRunner
from PyFoam.LogAnalysis.BoundingLogAnalyzer import BoundingLogAnalyzer
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from .CommonParallel import CommonParallel
from .CommonRestart import CommonRestart
from .CommonPlotLines import CommonPlotLines
from .CommonClearCase import CommonClearCase
from .CommonReportUsage import CommonReportUsage
from .CommonReportRunnerData import CommonReportRunnerData
from .CommonSafeTrigger import CommonSafeTrigger
from .CommonWriteAllTrigger import CommonWriteAllTrigger
from .CommonStandardOutput import CommonStandardOutput
from .CommonServer import CommonServer
from .CommonVCSCommit import CommonVCSCommit

from .CursesApplicationWrapper import CWindowAnalyzed

class SteadyRunner(PyFoamApplication,
                   CommonPlotLines,
                   CommonSafeTrigger,
                   CommonWriteAllTrigger,
                   CommonClearCase,
                   CommonServer,
                   CommonReportUsage,
                   CommonReportRunnerData,
                   CommonParallel,
                   CommonRestart,
                   CommonStandardOutput,
                   CommonVCSCommit):

    CWindowType=CWindowAnalyzed

    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs an OpenFoam steady solver.  Needs the usual 3 arguments (<solver>
<directory> <case>) and passes them on (plus additional arguments)
Output is sent to stdout and a logfile inside the case directory
(PyFoamSolver.logfile).  The Directory PyFoamSolver.analyzed contains
this information a) Residuals and other information of the linear
solvers b) Execution time c) continuity information d) bounding of
variables

If the solver has converged (linear solvers below threshold) it is
stopped and the last simulation state is written to disk
        """

        CommonPlotLines.__init__(self)
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   **kwargs)

    def addOptions(self):
        CommonClearCase.addOptions(self)
        CommonRestart.addOptions(self)
        CommonReportUsage.addOptions(self)
        CommonReportRunnerData.addOptions(self)
        CommonStandardOutput.addOptions(self)
        CommonParallel.addOptions(self)
        CommonPlotLines.addOptions(self)
        CommonSafeTrigger.addOptions(self)
        CommonWriteAllTrigger.addOptions(self)
        CommonServer.addOptions(self)
        CommonVCSCommit.addOptions(self)

    def run(self):
        cName=self.parser.casePath()
        self.checkCase(cName)

        self.processPlotLineOptions(autoPath=cName)

        sol=SolutionDirectory(cName,archive=None)

        lam=self.getParallel(sol)

        self.clearCase(SolutionDirectory(cName,
                                         archive=None,
                                         parallel=lam is not None))

        self.setLogname()

        self.checkAndCommit(sol)

        run=ConvergenceRunner(BoundingLogAnalyzer(progress=self.opts.progress,
                                                  doFiles=self.opts.writeFiles,
                                                  singleFile=self.opts.singleDataFilesOnly,
                                                  doTimelines=True),
                              silent=self.opts.progress or self.opts.silent,
                              splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                              split_fraction_unchanged=self.opts.split_fraction_unchanged,
                              argv=self.parser.getArgs(),
                              restart=self.opts.restart,
                              server=self.opts.server,
                              logname=self.opts.logname,
                              compressLog=self.opts.compress,
                              lam=lam,
                              logTail=self.opts.logTail,
                              noLog=self.opts.noLog,
                              remark=self.opts.remark,
                              parameters=self.getRunParameters(),
                              echoCommandLine=self.opts.echoCommandPrefix,
                              jobId=self.opts.jobId)

        run.createPlots(customRegexp=self.lines_,
                        splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                        split_fraction_unchanged=self.opts.split_fraction_unchanged,
                        writeFiles=self.opts.writeFiles)

        if self.cursesWindow:
            self.cursesWindow.setAnalyzer(run.analyzer)
            self.cursesWindow.setRunner(run)
            run.analyzer.addTimeListener(self.cursesWindow)

        self.addSafeTrigger(run,sol)
        self.addWriteAllTrigger(run,sol)

        self.addToCaseLog(cName,"Starting")

        run.start()

        self.addToCaseLog(cName,"Ending")

        self.setData(run.data)

        self.reportUsage(run)
        self.reportRunnerData(run)

        return run.data

# Should work with Python3 and Python2
