#  ICE Revision: $Id: PlotRunner.py,v 2d3659384189 2020-02-27 10:48:04Z bgschaid $
"""
Class that implements pyFoamPlotRunner
"""

from .PyFoamApplication import PyFoamApplication

from PyFoam.Execution.GnuplotRunner import GnuplotRunner

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from .CommonStandardOutput import CommonStandardOutput
from .CommonPlotLines import CommonPlotLines
from .CommonParallel import CommonParallel
from .CommonRestart import CommonRestart
from .CommonPlotOptions import CommonPlotOptions
from .CommonClearCase import CommonClearCase
from .CommonReportUsage import CommonReportUsage
from .CommonReportRunnerData import CommonReportRunnerData
from .CommonSafeTrigger import CommonSafeTrigger
from .CommonWriteAllTrigger import CommonWriteAllTrigger
from .CommonLibFunctionTrigger import CommonLibFunctionTrigger
from .CommonServer import CommonServer
from .CommonVCSCommit import CommonVCSCommit
from .CommonPrePostHooks import CommonPrePostHooks
from .CommonBlink1 import CommonBlink1

from .CursesApplicationWrapper import CWindowAnalyzed

class PlotRunner(PyFoamApplication,
                 CommonPlotOptions,
                 CommonPlotLines,
                 CommonSafeTrigger,
                 CommonWriteAllTrigger,
                 CommonLibFunctionTrigger,
                 CommonClearCase,
                 CommonServer,
                 CommonReportUsage,
                 CommonReportRunnerData,
                 CommonParallel,
                 CommonRestart,
                 CommonStandardOutput,
                 CommonVCSCommit,
                 CommonPrePostHooks,
                 CommonBlink1):

    CWindowType=CWindowAnalyzed

    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs an OpenFoam solver needs the usual 3 arguments (<solver>
<directory> <case>) and passes them on (plus additional arguments).
Output is sent to stdout and a logfile inside the case directory
(PyFoamSolver.logfile) Information about the residuals is output as
graphs

If the directory contains a file customRegexp this is automatically
read and the regular expressions in it are displayed
        """
        CommonPlotOptions.__init__(self,persist=True)
        CommonPlotLines.__init__(self)

        PyFoamApplication.__init__(self,
                                   exactNr=False,
                                   args=args,
                                   description=description,
                                   findLocalConfigurationFile=self.localConfigFromCasename,
                                   **kwargs)

    def addOptions(self):
        CommonClearCase.addOptions(self)

        CommonPlotOptions.addOptions(self)

        self.parser.add_option("--steady-run",
                               action="store_true",
                               default=False,
                               dest="steady",
                               help="This is a steady run. Stop it after convergence")

        CommonReportUsage.addOptions(self)
        CommonReportRunnerData.addOptions(self)
        CommonStandardOutput.addOptions(self,longProgress=True)
        CommonParallel.addOptions(self)
        CommonRestart.addOptions(self)
        CommonPlotLines.addOptions(self)
        CommonSafeTrigger.addOptions(self)
        CommonWriteAllTrigger.addOptions(self)
        CommonLibFunctionTrigger.addOptions(self)
        CommonServer.addOptions(self)
        CommonVCSCommit.addOptions(self)
        CommonPrePostHooks.addOptions(self, auto_enable=False)
        CommonBlink1.addOptions(self)

    def run(self):
        self.processPlotOptions()

        cName=self.parser.casePath()
        self.checkCase(cName)
#        self.addLocalConfig(cName)

        self.prepareHooks()

        self.processPlotLineOptions(autoPath=cName)

        sol=SolutionDirectory(cName,archive=None)

        lam=self.getParallel(sol)

        self.clearCase(SolutionDirectory(cName,
                                         archive=None,
                                         parallel=lam is not None))

        self.setLogname()

        self.checkAndCommit(sol)

        self.initBlink()

        run=GnuplotRunner(argv=self.replaceAutoInArgs(self.parser.getArgs()),
                          smallestFreq=self.opts.frequency,
                          persist=self.opts.persist,
                          quiet=self.opts.quietPlot,
                          splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                          split_fraction_unchanged=self.opts.split_fraction_unchanged,
                          plotLinear=self.opts.linear,
                          plotCont=self.opts.continuity,
                          plotBound=self.opts.bound,
                          plotIterations=self.opts.iterations,
                          plotCourant=self.opts.courant,
                          plotExecution=self.opts.execution,
                          plotDeltaT=self.opts.deltat,
                          customRegexp=self.plotLines(),
                          writeFiles=self.opts.writeFiles,
                          hardcopy=self.opts.hardcopy,
                          hardcopyPrefix=self.opts.hardcopyPrefix,
                          hardcopyFormat=self.opts.hardcopyformat,
                          hardcopyTerminalOptions=self.opts.hardcopyTerminalOptions,
                          server=self.opts.server,
                          lam=lam,
                          raiseit=self.opts.raiseit,
                          steady=self.opts.steady,
                          silent=self.opts.silent or (self.opts.longProgress and self.cursesWindow),
                          progress=self.opts.progress or self.opts.silent,
                          longProgress=self.opts.longProgress and not self.cursesWindow,
                          restart=self.opts.restart,
                          logname=self.opts.logname,
                          compressLog=self.opts.compress,
                          noLog=self.opts.noLog,
                          logTail=self.opts.logTail,
                          plottingImplementation=self.opts.implementation,
                          gnuplotTerminal=self.opts.gnuplotTerminal,
                          writePickled=self.opts.writePickled,
                          singleFile=self.opts.singleDataFilesOnly,
                          remark=self.opts.remark,
                          parameters=self.getRunParameters(),
                          echoCommandLine=self.opts.echoCommandPrefix,
                          jobId=self.opts.jobId)

        if self.cursesWindow:
            self.cursesWindow.setAnalyzer(run.analyzer)
            self.cursesWindow.setRunner(run)
            run.analyzer.addTimeListener(self.cursesWindow)
            if self.opts.longProgress:
                self.cursesWindow.addGenerator(run.analyzer.summarizeData)
                from .CursesApplicationWrapper import addExpr
                addExpr(r'^([^ ]+) ---*$')

        self.addSafeTrigger(run,sol,steady=self.opts.steady)
        self.addWriteAllTrigger(run,sol)
        self.addLibFunctionTrigger(run,sol)
        self.runPreHooks()

        if self.blink1:
            run.addTicker(lambda: self.blink1.ticToc())

        self.addToCaseLog(cName,"Starting")

        run.start()

        self.stopBlink()

        self.setData(run.data)

        self.addToCaseLog(cName,"Ending")

        self.runPostHooks()

        self.reportUsage(run)
        self.reportRunnerData(run)

        return run.data

# Should work with Python3 and Python2
