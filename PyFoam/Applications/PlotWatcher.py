#  ICE Revision: $Id: PlotWatcher.py,v 2d3659384189 2020-02-27 10:48:04Z bgschaid $
"""
Class that implements pyFoamPlotWatcher
"""

from PyFoam.Execution.GnuplotRunner import GnuplotWatcher

from .PyFoamApplication import PyFoamApplication

from .CommonPlotLines import CommonPlotLines
from .CommonPlotOptions import CommonPlotOptions

from .CursesApplicationWrapper import CWindowAnalyzed

from os import path
from optparse import OptionGroup

from PyFoam.ThirdParty.six import PY3,print_

if PY3:
    long=int


class PlotWatcher(PyFoamApplication,
                  CommonPlotOptions,
                  CommonPlotLines):

    CWindowType=CWindowAnalyzed

    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Gets the name of a logfile which is assumed to be the output of a
OpenFOAM-solver. Parses the logfile for information about the
convergence of the solver and generates gnuplot-graphs. Watches the
file until interrupted.

If a log-file 'auto' is specified the utility looks for the newest file with
the extension '.logfile' in the directory and uses that
        """

        CommonPlotOptions.__init__(self,persist=False)
        CommonPlotLines.__init__(self)
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <logfile>",
                                   changeVersion=False,
                                   interspersed=True,
                                   nr=1,
                                   exactNr=False,
                                   findLocalConfigurationFile=self.localConfigInArgsFile,
                                   **kwargs)

    def addOptions(self):
        CommonPlotOptions.addOptions(self)

        input=OptionGroup(self.parser,
                           "Input",
                           "Specifics of the input")
        self.parser.add_option_group(input)

        input.add_option("--solver-not-running-anymore",
                          action="store_true",
                          dest="solverNotRunning",
                          default=False,
                          help="It makes no sense to wait for further output, because the solver is not running anymore. Watcher ends as soon as he encounters the end of the file. Only makes sense with --persist or --hardcopy")
        input.add_option("--no-auto-add-restart-files",
                         action="store_false",
                         dest="autoAddRestart",
                         default=True,
                         help="Do not automatically add restart logfiles if only one log-file was specified and files with similar names are present")

        output=OptionGroup(self.parser,
                           "Output",
                           "What should be output to the terminal")
        self.parser.add_option_group(output)

        output.add_option("--tail",
                          type="long",
                          dest="tail",
                          default=long(5000),
                          help="The length at the end of the file that should be output (in bytes. Default: %default)")
        output.add_option("--silent",
                          action="store_true",
                          dest="silent",
                          default=False,
                          help="Logfile is not copied to the terminal")
        output.add_option("--progress",
                          action="store_true",
                          default=False,
                          dest="progress",
                          help="Only prints the progress of the simulation, but swallows all the other output")
        output.add_option("--long-progress",
                          action="store_true",
                          default=False,
                          dest="longProgress",
                          help="Only prints the progress of the simulation in a long format")
        output.add_option("--replot-frequency",
                          action="store",
                          default=10,
                          type="float",
                          dest="replotFrequency",
                          help="If the tail of the file is not yet reached, how often the data should be plotted: Default: %default")

        limit=OptionGroup(self.parser,
                          "Limits",
                          "Where the plots should start and end")
        self.parser.add_option_group(limit)

        limit.add_option("--start",
                         action="store",
                         type="float",
                         default=None,
                         dest="start",
                         help="Start time starting from which the data should be plotted. If undefined the initial time is used")

        limit.add_option("--end",
                         action="store",
                         type="float",
                         default=None,
                         dest="end",
                         help="End time until which the data should be plotted. If undefined it is plotted till the end")

        CommonPlotLines.addOptions(self)

    def run(self):
        self.processPlotOptions()

        hereDir=path.abspath(path.dirname(self.parser.getArgs()[0]))
        self.processPlotLineOptions(autoPath=hereDir)
        # self.addLocalConfig(hereDir)

        if len(self.parser.getArgs())==1:
            import re,os
            logFile=self.parser.getArgs()[0]
            if logFile=="auto" and not path.exists("auto"):
                print_("Automatically detecting latest logfile")
                logFile,logDate=None,None
                for f in os.listdir(hereDir):
                    if path.splitext(f)[1]==".logfile":
                        if logDate is None:
                            logFile,logDate=f,path.getmtime(f)
                        else:
                            if logDate<path.getmtime(f):
                                logFile,logDate=f,path.getmtime(f)
                if logFile is None:
                    self.error("Could not find an appropriate logfile in",
                               hereDir)
            if self.opts.autoAddRestart:
                pattern=re.compile(
                    path.basename(logFile)+"\.restart[0-9]+")
                rest=[]
                logDir=path.dirname(path.abspath(logFile))
                for fName in os.listdir(logDir):
                    if pattern.match(path.basename(fName)):
                        rest.append(path.join(logDir,fName))
                if len(rest)>0:
                    logFile=[logFile]+rest
        else:
            logFile=self.parser.getArgs()
        run=GnuplotWatcher(logFile,
                           smallestFreq=self.opts.frequency,
                           persist=self.opts.persist,
                           quiet=self.opts.quietPlot,
                           splitThres=self.opts.splitDataPointsThreshold if self.opts.doSplitDataPoints else None,
                           split_fraction_unchanged=self.opts.split_fraction_unchanged,
                           tailLength=self.opts.tail,
                           silent=self.opts.silent or (self.opts.longProgress and self.cursesWindow),
                           hardcopy=self.opts.hardcopy,
                           hardcopyPrefix=self.opts.hardcopyPrefix,
                           hardcopyFormat=self.opts.hardcopyformat,
                           hardcopyTerminalOptions=self.opts.hardcopyTerminalOptions,
                           plotLinear=self.opts.linear,
                           plotCont=self.opts.continuity,
                           plotBound=self.opts.bound,
                           plotIterations=self.opts.iterations,
                           plotCourant=self.opts.courant,
                           plotExecution=self.opts.execution,
                           plotDeltaT=self.opts.deltat,
                           customRegexp=self.plotLines(),
                           writeFiles=self.opts.writeFiles,
                           raiseit=self.opts.raiseit,
                           progress=self.opts.progress,
                           longProgress=self.opts.longProgress and not self.cursesWindow,
                           start=self.opts.start,
                           end=self.opts.end,
                           singleFile=self.opts.singleDataFilesOnly,
                           replotFrequency=self.opts.replotFrequency,
                           writePickled=self.opts.writePickled,
                           plottingImplementation=self.opts.implementation,
                           gnuplotTerminal=self.opts.gnuplotTerminal,
                           solverNotRunning=self.opts.solverNotRunning)

        if self.cursesWindow:
            def fileChanged():
                self.cursesWindow.setAnalyzer(run.analyzer)
            run.analyzer.addTimeListener(self.cursesWindow)
            run.addChangeFileHook(fileChanged)
            if self.opts.longProgress:
                self.cursesWindow.addGenerator(run.analyzer.summarizeData)
                from .CursesApplicationWrapper import addExpr
                addExpr(r'^([^ ]+) ---*$')

        run.start()

# Should work with Python3 and Python2
