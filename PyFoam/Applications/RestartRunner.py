#  ICE Revision: $Id$
"""
Application class that implements pyFoamRestartRunner
"""

from .PyFoamApplication import PyFoamApplication

from PyFoam.Execution.AnalyzedRunner import AnalyzedRunner
from PyFoam.Execution.BasicRunner import calcLogname,findRestartFiles
from PyFoam.LogAnalysis.BoundingLogAnalyzer import BoundingLogAnalyzer
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.RegionCases import RegionCases
from PyFoam.RunDictionary.ParameterFile import ParameterFile

from PyFoam.Error import warning

from .CommonPlotLines import CommonPlotLines
from .CommonReportUsage import CommonReportUsage
from .CommonReportRunnerData import CommonReportRunnerData
from .CommonWriteAllTrigger import CommonWriteAllTrigger
from .CommonLibFunctionTrigger import CommonLibFunctionTrigger
from .CommonStandardOutput import CommonStandardOutput
from .CommonParallel import CommonParallel
from .CommonServer import CommonServer
from .CommonVCSCommit import CommonVCSCommit
from .CommonPrePostHooks import CommonPrePostHooks
from .CommonBlink1 import CommonBlink1

from .CursesApplicationWrapper import CWindowAnalyzed

from PyFoam.ThirdParty.six import print_

from optparse import OptionGroup

class RestartRunner(PyFoamApplication,
                    CommonPlotLines,
                    CommonWriteAllTrigger,
                    CommonLibFunctionTrigger,
                    CommonReportUsage,
                    CommonReportRunnerData,
                    CommonParallel,
                    CommonServer,
                    CommonStandardOutput,
                    CommonVCSCommit,
                    CommonPrePostHooks,
                    CommonBlink1):

    CWindowType=CWindowAnalyzed

    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs an OpenFOAM solver repeatedly by restarting it from the last time-step
written by the previous run. Stops if the solver either
- reached the end time,
- did not write a new time-step during the last restart
- took less than a certain number of time-steps
- a number of predefined restarts is used

Purpose of this utility is to run cases where sometimes the solver fails for
reasons that have nothing to do with the physics but runs fine after a restart
        """

        CommonPlotLines.__init__(self)
        PyFoamApplication.__init__(self,
                                   exactNr=False,
                                   args=args,
                                   description=description,
                                   findLocalConfigurationFile=self.localConfigFromCasename,
                                   **kwargs)

    def addOptions(self):
        CommonReportUsage.addOptions(self)
        CommonReportRunnerData.addOptions(self)
        CommonStandardOutput.addOptions(self)
        CommonParallel.addOptions(self)
        CommonPlotLines.addOptions(self)
        CommonWriteAllTrigger.addOptions(self)
        CommonLibFunctionTrigger.addOptions(self)
        CommonServer.addOptions(self)
        CommonVCSCommit.addOptions(self)
        CommonPrePostHooks.addOptions(self)
        CommonBlink1.addOptions(self)

        restart=OptionGroup(self.parser,
                            "Restart",
                            "Controlling how often restarting is actually done")
        self.parser.add_option_group(restart)

        restart.add_option("--maximum-number-of-restarts",
                           action="store",
                           type="int",
                           dest="maximumRestarts",
                           default=99,
                           help="If the number of restarts is exceeded then the whole operation will stop. Default: %default")
        restart.add_option("--minimum-number-of-steps",
                           action="store",
                           type="int",
                           dest="minimumSteps",
                           default=5,
                           help="If the number of steps is smaller then this a restart is not considered. Default: %default")

    def run(self):
        casePath=self.parser.casePath()
        self.checkCase(casePath)
        #        self.addLocalConfig(casePath)

        self.addToCaseLog(casePath,"Starting")
        self.prepareHooks()

        self.processPlotLineOptions(autoPath=casePath)

        lam=self.getParallel(SolutionDirectory(casePath,archive=None))

        isParallel=lam is not None

        self.lastWrittenTime=None

        sol=SolutionDirectory(casePath,archive=None,parallel=isParallel)
        ctrlDict=ParameterFile(sol.controlDict(),backup=False)
        if ctrlDict.readParameter("startFrom")!="latestTime":
            self.error("In",casePath,"the value of 'startFrom' is not 'latestTime' (required for this script)")

        args=self.replaceAutoInArgs(self.parser.getArgs())

        def checkRestart(data=None):
            lastTimeName=sol.getLast()
            lastTime=float(lastTimeName)
            ctrlDict=ParameterFile(sol.controlDict(),backup=False)
            endTime=float(ctrlDict.readParameter("endTime"))
            if abs(endTime-lastTime)/endTime<1e-5:
                return "Reached endTime {}".format(endTime)
            logfile=calcLogname(self.opts.logname,args)
            isRestart,restartnr,restartName,lastlog=findRestartFiles(logfile,sol)
            # TODO: look into the logfile
            if self.lastWrittenTime is not None:
                if self.lastWrittenTime==lastTimeName:
                    return "Last restart didn't improve on {}. Further restarts make no sense".format(lastTime)
            self.lastWrittenTime=lastTimeName
            if data:
                if "stepNr" in data and data["stepNr"]<self.opts.minimumSteps:
                    return "Only {} steps done while {} are required".format(
                        data["stepNr"],
                        self.opts.minimumSteps
                    )
        redo=True

        reason=checkRestart()
        if reason is not None:
            self.warning("Not starting:",reason)
            redo=False

        self.checkAndCommit(sol)

        self.initBlink()

        startNr=0

        self.setLogname()

        while redo:
            startNr+=1
            print_()
            print_("Starting restart nr",startNr,"on case",casePath)
            print_()
            self.addToCaseLog(casePath,"Restart nr",startNr,"started")
            run=AnalyzedRunner(BoundingLogAnalyzer(progress=self.opts.progress,
                                                   doFiles=self.opts.writeFiles,
                                                   singleFile=self.opts.singleDataFilesOnly,
                                                   doTimelines=True),
                               silent=self.opts.progress or self.opts.silent,
                               splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                               split_fraction_unchanged=self.opts.split_fraction_unchanged,
                               argv=args,
                               server=self.opts.server,
                               lam=lam,
                               logname=self.opts.logname,
                               compressLog=self.opts.compress,
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

            self.addWriteAllTrigger(run,SolutionDirectory(casePath,archive=None))
            self.addLibFunctionTrigger(run,SolutionDirectory(casePath,archive=None))
            self.runPreHooks()

            if self.blink1:
                run.addTicker(lambda: self.blink1.ticToc())

            run.start()

            if run.data["keyboardInterrupt"]:
                print_()
                self.warning("Not restarting because of keyboard interrupt")

                redo=False

            self.setData({startNr:run.data})

            self.runPostHooks()

            self.reportUsage(run)
            self.reportRunnerData(run)

            self.addToCaseLog(casePath,"Restart nr",startNr,"ended")

            reason=checkRestart(data=run.data)
            if reason is not None:
                print_()
                self.warning("Not starting:",reason)
                self.addToCaseLog(casePath,"Stopping because of",reason)

                redo=False

            if startNr>=self.opts.maximumRestarts:
                print_()
                self.warning("Maximum number",self.opts.maximumRestarts,
                             "restarts reached")
                self.addToCaseLog(casePath,"Stopping because maximum number",
                                  self.opts.maximumRestarts,"of restarts reached")
                redo=False

        self.stopBlink()

        self.addToCaseLog(casePath,"Ended")

        print_()
        print_("Ended after",startNr,"restarts")
        print_()

# Should work with Python3 and Python2
