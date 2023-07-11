#  ICE Revision: $Id: GnuplotRunner.py,v 2d3659384189 2020-02-27 10:48:04Z bgschaid $
"""Runner that outputs the residuals of the linear solver with Gnuplot"""

from .StepAnalyzedCommon import StepAnalyzedCommon
from .BasicRunner import BasicRunner
from .BasicWatcher import BasicWatcher

from PyFoam.LogAnalysis.BoundingLogAnalyzer import BoundingLogAnalyzer
from PyFoam.LogAnalysis.SteadyConvergedLineAnalyzer import SteadyConvergedLineAnalyzer
from PyFoam.Basics.TimeLineCollection import TimeLineCollection
from PyFoam.Error import error
from PyFoam.ThirdParty.six import print_

from os import path

class GnuplotCommon(StepAnalyzedCommon):
    """Class that collects the Gnuplotting-Stuff for two other classes"""
    def __init__(self,
                 fname,
                 smallestFreq=0.,
                 persist=None,
                 quiet=False,
                 splitThres=2048,
                 split_fraction_unchanged=0.2,
                 plotLinear=True,
                 plotCont=True,
                 plotBound=True,
                 plotIterations=False,
                 plotCourant=False,
                 plotExecution=False,
                 plotDeltaT=False,
                 hardcopy=False,
                 hardcopyFormat="png",
                 hardcopyPrefix=None,
                 hardcopyTerminalOptions=None,
                 customRegexp=None,
                 writeFiles=False,
                 raiseit=False,
                 progress=False,
                 longProgress=False,
                 start=None,
                 end=None,
                 singleFile=False,
                 writePickled=True,
                 plottingImplementation=None,
                 gnuplotTerminal=None,
                 adaptFrequency=True):
        """
        TODO: Docu
        """
        StepAnalyzedCommon.__init__(self,
                                    fname,
                                    BoundingLogAnalyzer(doTimelines=True,
                                                        doFiles=writeFiles,
                                                        progress=progress,
                                                        singleFile=singleFile,
                                                        startTime=start,
                                                        endTime=end),
                                    writePickled=writePickled,
                                    smallestFreq=smallestFreq,
                                    adaptFrequency=adaptFrequency)

        self.startTime=start
        self.endTime=end

        self.plots={}
        self.createPlots(persist=persist,
                         quiet=quiet,
                         raiseit=raiseit,
                         start=start,
                         end=end,
                         writeFiles=writeFiles,
                         splitThres=splitThres,
                         split_fraction_unchanged=split_fraction_unchanged,
                         plotLinear=plotLinear,
                         plotCont=plotCont,
                         plotBound=plotBound,
                         plotIterations=plotIterations,
                         plotCourant=plotCourant,
                         plotExecution=plotExecution,
                         plotDeltaT=plotDeltaT,
                         customRegexp=customRegexp,
                         gnuplotTerminal=gnuplotTerminal,
                         plottingImplementation=plottingImplementation)

        self.hardcopy=hardcopy
        self.hardcopyFormat=hardcopyFormat
        self.hardcopyPrefix=hardcopyPrefix
        self.hardcopyTerminalOptions=hardcopyTerminalOptions

        self.longProgress=longProgress

    def addPlots(self,plots):
        for k in plots:
            if k not in self.plots:
                self.plots[k]=plots[k]
            else:
                # key already there. Try to build an unique key
                newK=k
                while newK in self.plots:
                    newK+="_"
                self.plots[newK]=plots[k]

    def timeHandle(self):
        StepAnalyzedCommon.timeHandle(self)

        for p in self.plots:
            self.plots[p].redo()

    def timeChanged(self):
        StepAnalyzedCommon.timeChanged(self)

        if self.longProgress:
            print_(self.analyzer.summarizeData())

    def stopHandle(self):
        StepAnalyzedCommon.stopHandle(self)
#        print("Done common")
        self.timeHandle()
#        print("Done time")
        if self.hardcopy:
            if self.hardcopyPrefix:
                prefix=self.hardcopyPrefix+"."
            else:
                prefix=""

            for p in self.plots:
                if not self.plots[p].hasData():
                    continue
                if p.find("custom")==0:
                    name=p+"_"+self.plots[p].spec.id
                else:
                    name=p
                self.plots[p].doHardcopy(prefix+name,
                                         self.hardcopyFormat,
                                         self.hardcopyTerminalOptions)
#        print("Done handle")

class GnuplotRunner(GnuplotCommon,BasicRunner):
    def __init__(self,
                 argv=None,
                 smallestFreq=0.,
                 persist=None,
                 quiet=False,
                 splitThres=2048,
                 split_fraction_unchanged=0.2,
                 plotLinear=True,
                 plotCont=True,
                 plotBound=True,
                 plotIterations=False,
                 plotCourant=False,
                 plotExecution=False,
                 plotDeltaT=False,
                 customRegexp=None,
                 hardcopy=False,
                 hardcopyFormat="png",
                 hardcopyPrefix=None,
                 hardcopyTerminalOptions=None,
                 writeFiles=False,
                 server=False,
                 lam=None,
                 raiseit=False,
                 steady=False,
                 progress=False,
                 longProgress=False,
                 silent=False,
                 restart=False,
                 logname=None,
                 compressLog=False,
                 noLog=False,
                 logTail=None,
                 singleFile=False,
                 writePickled=True,
                 plottingImplementation=None,
                 gnuplotTerminal=None,
                 remark=None,
                 parameters=None,
                 jobId=None,
                 echoCommandLine=None):
        """:param smallestFreq: smallest Frequency of output
        :param persist: Gnuplot window persistst after run
        :param steady: Is it a steady run? Then stop it after convergence"""
        BasicRunner.__init__(self,
                             argv=argv,
                             silent=progress or longProgress or silent,
                             server=server,
                             lam=lam,
                             restart=restart,
                             logname=logname,
                             compressLog=compressLog,
                             noLog=noLog,
                             logTail=logTail,
                             remark=remark,
                             parameters=parameters,
                             echoCommandLine=echoCommandLine,
                             jobId=jobId)
        GnuplotCommon.__init__(self,
                               "Gnuplotting",
                               smallestFreq=smallestFreq,
                               persist=persist,
                               quiet=quiet,
                               splitThres=splitThres,
                               split_fraction_unchanged=split_fraction_unchanged,
                               plotLinear=plotLinear,
                               plotCont=plotCont,
                               plotBound=plotBound,
                               plotIterations=plotIterations,
                               plotCourant=plotCourant,
                               plotExecution=plotExecution,
                               plotDeltaT=plotDeltaT,
                               customRegexp=customRegexp,
                               hardcopy=hardcopy,
                               hardcopyFormat=hardcopyFormat,
                               hardcopyPrefix=hardcopyPrefix,
                               hardcopyTerminalOptions=hardcopyTerminalOptions,
                               writeFiles=writeFiles,
                               raiseit=raiseit,
                               progress=progress,
                               longProgress=longProgress,
                               singleFile=singleFile,
                               writePickled=writePickled,
                               gnuplotTerminal=gnuplotTerminal,
                               plottingImplementation=plottingImplementation)
        self.steady=steady
        if self.steady:
            self.steadyAnalyzer=SteadyConvergedLineAnalyzer()
            self.addAnalyzer("Convergence",self.steadyAnalyzer)

    def lineHandle(self,line):
        """Not to be called: Stops the solver"""
        GnuplotCommon.lineHandle(self,line)

        if self.steady:
            if not self.steadyAnalyzer.goOn():
                self.stopGracefully()

    def stopHandle(self):
        """Not to be called: Restores controlDict"""
        GnuplotCommon.stopHandle(self)
        BasicRunner.stopHandle(self)

class GnuplotWatcher(GnuplotCommon,BasicWatcher):
    def __init__(self,
                 logfile,
                 smallestFreq=0.,
                 persist=None,
                 quiet=False,
                 splitThres=2048,
                 split_fraction_unchanged=0.2,
                 silent=False,
                 tailLength=1000,
                 sleep=0.1,
                 replotFrequency=3600,
                 plotLinear=True,
                 plotCont=True,
                 plotBound=True,
                 plotIterations=False,
                 plotCourant=False,
                 plotExecution=False,
                 plotDeltaT=False,
                 customRegexp=None,
                 writeFiles=False,
                 hardcopy=False,
                 hardcopyFormat="png",
                 hardcopyPrefix=None,
                 hardcopyTerminalOptions=None,
                 raiseit=False,
                 progress=False,
                 longProgress=False,
                 start=None,
                 end=None,
                 singleFile=False,
                 writePickled=True,
                 gnuplotTerminal=None,
                 plottingImplementation=None,
                 solverNotRunning=False):
        """:param smallestFreq: smallest Frequency of output
        :param persist: Gnuplot window persistst after run"""
        BasicWatcher.__init__(self,
                              logfile,
                              silent=(silent or progress or longProgress),
                              tailLength=tailLength,
                              sleep=sleep,
                              endTime=end,
                              follow=not solverNotRunning)
        GnuplotCommon.__init__(self,
                               logfile,
                               smallestFreq=smallestFreq,
                               persist=persist,
                               quiet=quiet,
                               splitThres=splitThres,
                               split_fraction_unchanged=split_fraction_unchanged,
                               plotLinear=plotLinear,
                               plotCont=plotCont,
                               plotBound=plotBound,
                               plotIterations=plotIterations,
                               plotCourant=plotCourant,
                               plotExecution=plotExecution,
                               plotDeltaT=plotDeltaT,
                               customRegexp=customRegexp,
                               hardcopy=hardcopy,
                               hardcopyFormat=hardcopyFormat,
                               hardcopyPrefix=hardcopyPrefix,
                               hardcopyTerminalOptions=hardcopyTerminalOptions,
                               writeFiles=writeFiles,
                               raiseit=raiseit,
                               progress=progress,
                               longProgress=longProgress,
                               start=start,
                               end=end,
                               singleFile=singleFile,
                               writePickled=writePickled,
                               gnuplotTerminal=gnuplotTerminal,
                               plottingImplementation=plottingImplementation,
                               adaptFrequency=False)

        self.hasPlotted=False
        self.replotFrequency=replotFrequency

        if self.analyzer.hasAnalyzer("Time"):
            self.addChangeFileHook(self.analyzer.getAnalyzer("Time").reset)


    def startHandle(self):
        self.bakFreq=self.freq
        if self.endTime!=None:
            self.freq=1
        else:
            self.freq=self.replotFrequency

    def tailingHandle(self):
        self.freq=self.bakFreq
        self.oldtime=0

    def timeHandle(self):
        plotNow=True
        if not self.hasPlotted and self.endTime!=None:
            try:
                if float(self.getTime())>self.endTime:
                    self.hasPlotted=True
            except ValueError:
                pass
        elif self.hasPlotted:
            plotNow=False
        if plotNow:
            for p in self.plots:
                self.plots[p].redo()

    def timeChanged(self):
        StepAnalyzedCommon.timeChanged(self)

        if self.longProgress and self.isTailing:
            print_(self.analyzer.summarizeData())

# Should work with Python3 and Python2
