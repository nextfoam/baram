#  ICE Revision: $Id: AnalyzedCommon.py,v 3f8df529776e 2020-02-28 20:07:20Z bgschaid $
"""Common stuff for classes that use analyzers"""

from os import path,mkdir
from shutil import move,rmtree

from PyFoam.Basics.PlotTimelinesFactory import createPlotTimelines,createPlotTimelinesDirect
from PyFoam.Basics.TimeLineCollection import signedMax
from PyFoam.LogAnalysis.RegExpLineAnalyzer import RegExpLineAnalyzer
from PyFoam.LogAnalysis.PhaseChangerLineAnalyzer import PhaseChangerLineAnalyzer
from PyFoam.LogAnalysis.CountLineAnalyzer import CountLineAnalyzer
from PyFoam.LogAnalysis.TriggerLineAnalyzer import TriggerLineAnalyzer
from PyFoam.LogAnalysis.ExecNameLineAnalyzer import ExecNameLineAnalyzer
from PyFoam.LogAnalysis.ReplayDataFileAnalyzer import ReplayDataFileAnalyzer

from PyFoam.Error import error,warning

# import pickle
from PyFoam.ThirdParty.six.moves import cPickle as pickle
from PyFoam.ThirdParty.six import print_

from PyFoam.Basics.GeneralPlotTimelines import allPlots
from PyFoam.Basics.TimeLineCollection import allLines

from threading import Lock

class AnalyzedCommon(object):
    """This class collects information and methods that are needed for
    handling analyzers"""

    def __init__(self,
                 filenames,
                 analyzer,
                 splitThres=2048,
                 split_fraction_unchanged=0.2,
                 doPickling=True):
        """:param filename: name of the file that is being analyzed
        :param analyzer: the analyzer itself
        :param doPickling: write the pickled plot data"""

        if type(filenames) is list:
            filename=filenames[0]
        else:
            filename=filenames

        self.analyzer=analyzer
        self.analyzer.addResetFileTrigger(self.resetFile)

        if 'dir' in dir(self):
            self.logDir=path.join(self.dir,filename+".analyzed")
        else:
            self.logDir=filename+".analyzed"

        if path.exists(self.logDir):
            # Clean away
            rmtree(self.logDir,ignore_errors=True)
        mkdir(self.logDir)

        self.doPickling=doPickling
        if self.doPickling:
            self.pickleLock=Lock()

        self.reset()

        if hasattr(self,"data"):
            pickleFile=path.join(self.logDir,"pickledStartData")
            pick=pickle.Pickler(open(pickleFile,"wb"))
            pick.dump(self.data)

        self.persist=None
        self.start_=None
        self.end=None
        self.raiseit=False
        self.writeFiles=False
        self.splitThres=splitThres
        self.split_fraction_unchanged=split_fraction_unchanged
        self.plottingImplementation="dummy"
        self.gnuplotTerminal=None

        eName=ExecNameLineAnalyzer()
        eName.addListener(self.execNameFound)
        self.addAnalyzer("ExecName",eName)
        self.automaticCustom=None

        self.tickers=[]
        self.plots={}

    def addTicker(self,ticker):
        """Add a callable that will be called at every timestep"""
        if ticker is not None:
            self.tickers.append(ticker)

    def addPlots(self,plots):
        "Add plots. To be overriden"
        pass

    def execNameFound(self,execName):
        if hasattr(self,"oldExecName"):
            if execName==self.oldExecName:
                return

        self.automaticCustom=[]
        self.oldExecName=execName
        from PyFoam import configuration as conf
        from PyFoam.Basics.CustomPlotInfo import CustomPlotInfo

        solvers=set([execName])

        for name,lst in conf().items("SolverBase"):
            if execName.lower().startswith(name):
                solvers|=set(eval(lst))

        import re
        autoplots=[a.lower() for a in conf().getList("Plotting","autoplots")]

        for name,dataString in conf().items("Autoplots"):
            found=False
            try:
                data=eval(dataString)
                solverPatterns=data["solvers"]
                info=data["plotinfo"]
                for s in solverPatterns:
                    try:
                        for eName in solvers:
                            if re.compile(s).fullmatch(eName):
                                found=True
                                break
                        if found:
                            break
                    except AttributeError:
                        # python 2 has no fullmatch
                        for eName in solvers:
                            if re.compile("(?:" + s + r")\Z").match(eName):
                                found=True
                                break
                        if found:
                            break
            except KeyError:
                import sys
                e = sys.exc_info()[1]
                warning("Miss-configured automatic expression",name,
                        "Missing key",e.args[0])
            except re.error:
                import sys
                warning("Problem with regular expression",s,"of",name,
                        ":",sys.exc_info()[1])
            except SyntaxError:
                warning("Syntax error in",dataString)

            if found or name.lower() in autoplots:
                self.automaticCustom.append(CustomPlotInfo(raw=info,
                                                           name=name))

    def tearDown(self):
        self.analyzer.tearDown()
        if hasattr(self,"data"):
            pickleFile=path.join(self.logDir,"pickledData")
            pick=pickle.Pickler(open(pickleFile,"wb"))
            pick.dump(self.data)

    def listAnalyzers(self):
        """:returns: A list with the names of the analyzers"""
        return self.analyzer.listAnalyzers()

    def getAnalyzer(self,name):
        """:param name: name of the LineAnalyzer to get"""
        return self.analyzer.getAnalyzer(name)

    def hasAnalyzer(self,name):
        """:param name: name of the LineAnalyzer we ask for"""
        return self.analyzer.hasAnalyzer(name)

    def addAnalyzer(self,name,analyzer):
        """:param name: name of the LineAnalyzer to add
        :param analyzer: the analyzer to add"""
        analyzer.setDirectory(self.logDir)
        return self.analyzer.addAnalyzer(name,analyzer)

    def lineHandle(self,line):
        """Not to be called: calls the analyzer for the current line"""
        self.analyzer.analyzeLine(line)

        if self.automaticCustom:
            # if one of the readers added custom plots add them AFTER
            # processing the whole line
            if len(self.automaticCustom)>0:
                print_("Adding automatic plots:",", ".join(
                    [e.name for e in self.automaticCustom]))

                automaticPlots=self.addCustomExpressions(self.automaticCustom,
                                                         persist=self.persist,
                                                         quiet=self.quiet,
                                                         start=self.start_,
                                                         end=self.end,
                                                         raiseit=self.raiseit,
                                                         writeFiles=self.writeFiles,
                                                         splitThres=self.splitThres,
                                                         split_fraction_unchanged=self.split_fraction_unchanged,
                                                         gnuplotTerminal=self.gnuplotTerminal,
                                                         plottingImplementation=self.plottingImplementation)
                self.reset()
                self.addPlots(automaticPlots)

            self.automaticCustom=None


    def reset(self):
        """reset the analyzer"""
        self.analyzer.setDirectory(self.logDir)

    def getDirname(self):
        """Get the name of the directory where the data is written to"""
        return self.logDir

    def getTime(self):
        """Get the execution time"""
        return self.analyzer.getTime()

    def addTrigger(self,time,func,once=True,until=None):
        """Adds a timed trigger to the Analyzer
        :param time: the time at which the function should be triggered
        :param func: the trigger function
        :param once: Should this function be called once or at every time-step
        :param until: The time until which the trigger should be called"""

        self.analyzer.addTrigger(time,func,once=once,until=until)

    def createPlots(self,
                    persist=None,
                    quiet=False,
                    raiseit=False,
                    splitThres=2048,
                    split_fraction_unchanged=0.2,
                    plotLinear=True,
                    plotCont=True,
                    plotBound=True,
                    plotIterations=True,
                    plotCourant=True,
                    plotExecution=True,
                    plotDeltaT=True,
                    start=None,
                    end=None,
                    writeFiles=False,
                    customRegexp=None,
                    gnuplotTerminal=None,
                    plottingImplementation="dummy"):

        plots={}

        self.persist=persist
        self.quiet=quiet
        self.start_=start
        self.end=end
        self.raiseit=raiseit
        self.writeFiles=writeFiles
        self.splitThres=splitThres
        self.plottingImplementation=plottingImplementation
        self.gnuplotTerminal=gnuplotTerminal

        if plotLinear and self.hasAnalyzer("Linear"):
            plots["linear"]=createPlotTimelinesDirect("linear",
                                                      self.getAnalyzer("Linear").lines,
                                                      persist=persist,
                                                      quiet=quiet,
                                                      raiseit=raiseit,
                                                      forbidden=["final","iterations"],
                                                      start=start,
                                                      end=end,
                                                      logscale=True,
                                                      gnuplotTerminal=gnuplotTerminal,
                                                      implementation=plottingImplementation)
            self.getAnalyzer("Linear").lines.setSplitting(splitThres=splitThres,
                                                          split_fraction_unchanged=split_fraction_unchanged,
                                                          splitFun=max,
                                                          advancedSplit=True)

            plots["linear"].setTitle("Residuals")
            plots["linear"].setYLabel("Initial residual")

        if plotCont and self.hasAnalyzer("Continuity"):
            plots["cont"]=createPlotTimelinesDirect("continuity",
                                                    self.getAnalyzer("Continuity").lines,
                                                    persist=persist,
                                                    quiet=quiet,
                                                    alternateAxis=["Global"],
                                                    raiseit=raiseit,
                                                    start=start,
                                                    end=end,
                                                    gnuplotTerminal=gnuplotTerminal,
                                                    implementation=plottingImplementation)
            plots["cont"].setYLabel("Cumulative")
            plots["cont"].setYLabel2("Global")
            self.getAnalyzer("Continuity").lines.setSplitting(splitThres=splitThres,
                                                              split_fraction_unchanged=split_fraction_unchanged,
                                                              advancedSplit=True)

            plots["cont"].setTitle("Continuity")

        if plotBound and self.hasAnalyzer("Bounding"):
            plots["bound"]=createPlotTimelinesDirect("bounding",
                                                     self.getAnalyzer("Bounding").lines,
                                                     persist=persist,
                                                     quiet=quiet,
                                                     raiseit=raiseit,
                                                     start=start,
                                                     end=end,
                                                     gnuplotTerminal=gnuplotTerminal,
                                                     implementation=plottingImplementation)
            self.getAnalyzer("Bounding").lines.setSplitting(splitThres=splitThres,
                                                            split_fraction_unchanged=split_fraction_unchanged,
                                                            splitFun=signedMax,
                                                            advancedSplit=True)
            plots["bound"].setTitle("Bounded variables")

        if plotIterations and self.hasAnalyzer("Iterations"):
            plots["iter"]=createPlotTimelinesDirect("iterations",
                                                    self.getAnalyzer("Iterations").lines,
                                                    persist=persist,
                                                    quiet=quiet,
                                                    with_="steps",
                                                    raiseit=raiseit,
                                                    start=start,
                                                    end=end,
                                                    gnuplotTerminal=gnuplotTerminal,
                                                    implementation=plottingImplementation)
            self.getAnalyzer("Iterations").lines.setSplitting(splitThres=splitThres,
                                                              split_fraction_unchanged=split_fraction_unchanged,
                                                              advancedSplit=True)

            plots["iter"].setTitle("Iterations")
            plots["iter"].setYLabel("Sum of iterations")

        if plotCourant and self.hasAnalyzer("Courant"):
            plots["courant"]=createPlotTimelinesDirect("courant",
                                                       self.getAnalyzer("Courant").lines,
                                                       persist=persist,
                                                       quiet=quiet,
                                                       raiseit=raiseit,
                                                       start=start,
                                                       end=end,
                                                       gnuplotTerminal=gnuplotTerminal,
                                                       implementation=plottingImplementation)
            self.getAnalyzer("Courant").lines.setSplitting(splitThres=splitThres,
                                                           split_fraction_unchanged=split_fraction_unchanged,
                                                           advancedSplit=True)

            plots["courant"].setTitle("Courant")
            plots["courant"].setYLabel("Courant Number [1]")

        if plotDeltaT and self.hasAnalyzer("DeltaT"):
            plots["deltaT"]=createPlotTimelinesDirect("timestep",
                                                      self.getAnalyzer("DeltaT").lines,
                                                      persist=persist,
                                                      quiet=quiet,
                                                      raiseit=raiseit,
                                                      start=start,
                                                      end=end,
                                                      logscale=True,
                                                      gnuplotTerminal=gnuplotTerminal,
                                                      implementation=plottingImplementation)
            self.getAnalyzer("DeltaT").lines.setSplitting(splitThres=splitThres,
                                                          split_fraction_unchanged=split_fraction_unchanged,
                                                          advancedSplit=True)

            plots["deltaT"].setTitle("DeltaT")
            plots["deltaT"].setYLabel("dt [s]")

        if plotExecution and self.hasAnalyzer("Execution"):
            plots["execution"]=createPlotTimelinesDirect("execution",
                                                         self.getAnalyzer("Execution").lines,
                                                         persist=persist,
                                                         quiet=quiet,
                                                         with_="steps",
                                                         raiseit=raiseit,
                                                         start=start,
                                                         end=end,
                                                         gnuplotTerminal=gnuplotTerminal,
                                                         implementation=plottingImplementation)
            self.getAnalyzer("Execution").lines.setSplitting(splitThres=splitThres,
                                                             split_fraction_unchanged=split_fraction_unchanged,
                                                             advancedSplit=True)

            plots["execution"].setTitle("Execution Time")
            plots["execution"].setYLabel("Time [s]")

        self.plots.update(plots)

        if customRegexp:
            customPlots=self.addCustomExpressions(customRegexp,
                                                  persist=persist,
                                                  quiet=quiet,
                                                  start=start,
                                                  end=end,
                                                  raiseit=raiseit,
                                                  writeFiles=writeFiles,
                                                  splitThres=splitThres,
                                                  split_fraction_unchanged=split_fraction_unchanged,
                                                  gnuplotTerminal=gnuplotTerminal,
                                                  plottingImplementation=plottingImplementation)
            plots.update(customPlots)
            self.reset()

        self.addPlots(plots)

    def addCustomExpressions(self,
                             customRegexp,
                             persist=None,
                             quiet=False,
                             start=None,
                             end=None,
                             raiseit=False,
                             writeFiles=False,
                             splitThres=2048,
                             split_fraction_unchanged=0.2,
                             gnuplotTerminal=None,
                             plottingImplementation="dummy"):
        plots={}
        publishers={}
        collectors=[]
        canonical={}
        marks=[]

        plotTypes= [
            ("regular"    , "Matches regular expression and plots"),
            ("collector"  , "Plot data on a different plot (the 'publisher')"),
            ("slave"      , "Old (deprecated) terminology for 'collector'"),
            ("dynamic"    , "Dynamically creates lines depending on the match found at 'idNr'"),
            ("dynamiccollector" , "Combination of 'dynamic' and 'collector'"),
            ("dynamicslave" , "Old (deprecated) terminology for 'dynamiccollector'"),
            ("data"       , "Reads data from a file and plots it"),
            ("datacollector"  , "Combination of 'data' and 'collector'"),
            ("dataslave"  , "Old (deprecated) terminology for 'datacollector'"),
            ("count"      , "Counts how often an expression occured (no plotting but used for 'alternateTime')"),
            ("mark"       , "If the expression matches then a vertical marker is drawn on the 'targets'"),
            ("phase"      , "Changes the phase prefix (for multi-region cases)")
        ]

        for i,custom in enumerate(customRegexp):
            if not custom.enabled:
                continue

            if persist!=None:
                custom.persist=persist
            if start!=None:
                custom.start=start
            if end!=None:
                custom.end=end
            custom.raiseit=raiseit

            if custom.type not in [p[0] for p in plotTypes]:
                error("type '{}' of custom plot '{}' not in known types:\n   {}".format(
                    custom.type,custom.id,
                    "\n   ".join(["{:15} : {}".format(n,d) for n,d in plotTypes])))

            createPlot=True
            if custom.type=="phase":
                self.addAnalyzer(custom.name,
                                 PhaseChangerLineAnalyzer(custom.expr,
                                                          idNr=custom.idNr))
                createPlot=False
            elif custom.type=="count":
                self.addAnalyzer(custom.name,
                                 CountLineAnalyzer(custom.expr))
                createPlot=False
            elif custom.type=="mark":
                a=TriggerLineAnalyzer(custom.expr)
                self.addAnalyzer(custom.name,
                                 a)
                marks.append((custom,a))
                createPlot=False
            elif custom.type in ["dynamic", "dynamicslave", "dynamiccollector"]:
                self.addAnalyzer(custom.name,
                                 RegExpLineAnalyzer(custom.name.lower(),
                                                    custom.expr,
                                                    titles=custom.titles,
                                                    doTimelines=True,
                                                    doFiles=writeFiles or custom.writeFiles,
                                                    accumulation=custom.accumulation,
                                                    dataTransformations=custom.dataTransformations,
                                                    progressTemplate=custom.progress,
                                                    singleFile=True,
                                                    idNr=custom.idNr,
                                                    stringValues=custom.stringValues,
                                                    startTime=custom.start,
                                                    endTime=custom.end))

            elif custom.type in ["regular", "slave", "collector"]:
                self.addAnalyzer(custom.name,
                                 RegExpLineAnalyzer(custom.name.lower(),
                                                    custom.expr,
                                                    titles=custom.titles,
                                                    doTimelines=True,
                                                    doFiles=writeFiles or custom.writeFiles,
                                                    accumulation=custom.accumulation,
                                                    dataTransformations=custom.dataTransformations,
                                                    progressTemplate=custom.progress,
                                                    stringValues=custom.stringValues,
                                                    singleFile=True,
                                                    startTime=custom.start,
                                                    endTime=custom.end))
            elif custom.type in ["data", "dataslave", "datacollector"]:
                self.addAnalyzer(custom.name,
                                 ReplayDataFileAnalyzer(timeName=custom.timeName,
                                                        validData=custom.validData,
                                                        validMatchRegexp=custom.validMatchRegexp,
                                                        csvName=custom.csvName,
                                                        txtName=custom.txtName,
                                                        namePrefix=custom.namePrefix,
                                                        excelName=custom.excelName,
                                                        skip_header=custom.skip_header,
                                                        stripCharacters=custom.stripCharacters,
                                                        progressTemplate=custom.progress,
                                                        replaceFirstLine=custom.replaceFirstLine,
                                                        startTime=custom.start,
                                                        endTime=custom.end))
            else:
                error("Unknown type",custom.type,"in custom expression",custom.name)

            canonical[custom.id]=custom.name

            if createPlot:
                if custom.publisher==None:
                    if custom.type in ["slave", "dynamicslave", "dataslave", "collector", "dynamiccollector", "datacollector"]:
                        error("Custom expression", custom.name,
                              "is supposed to be a 'collector' but no publisher is defined")
                    publishers[custom.id] = custom
                    plotCustom = createPlotTimelines(self.getAnalyzer(custom.name).lines,
                                                     quiet=quiet,
                                                     custom=custom,
                                                     gnuplotTerminal=gnuplotTerminal,
                                                     implementation=plottingImplementation)
                    self.getAnalyzer(custom.name).lines.setSplitting(splitThres=splitThres,
                                                                     split_fraction_unchanged=split_fraction_unchanged,
                                                                     advancedSplit=True)
                    plotCustom.setTitle(custom.theTitle)
                    plots["custom%04d" % i]=plotCustom
                    self.plots[custom.id]=plotCustom
                else:
                    if custom.type not in ["slave", "dynamicslave", "dataslave", "collector", "dynamiccollector", "datacollector"]:
                        error("'publisher' only makes sense if type is 'collector' or 'dynamiccollector' for",custom.name)
                    if getattr(custom,"alternateAxis",None):
                        error("Specify alternate values in 'alternateAxis' of publisher",
                              custom.publisher, "for", custom.name)
                    collectors.append(custom)

        for custom in customRegexp:
            if custom.alternateTime:
                self.getAnalyzer(custom.name).setParent(
                    self.getAnalyzer(canonical[custom.alternateTime])
                )
                self.getAnalyzer(canonical[custom.alternateTime]).addTimeListener(self.getAnalyzer(custom.name))

        for s in collectors:
            if s.publisher not in publishers:
                error("The custom plot", s.id, "wants the publisher plot",
                      s.publisher, "but it is not found in the list of publishers",
                      list(publishers.keys()))
            else:
                collector=self.getAnalyzer(s.name)
                m = publishers[s.publisher]
                if m.xvalue is not None and s.xvalue is None:
                    error("Publisher plot", m.id, "is parameteric with xvalue",
                          m.xvalue, "so", s.id, "has to be parameteric as well")
                if m.xvalue is None and s.xvalue is not None:
                    error("Collector plot", s.id, "is parameteric with xvalue",
                          s.xvalue, "so", m.id, "has to be parameteric as well")

                publisher=self.getAnalyzer(m.name)
                collector.setPublisher(publisher)

        for custom,analyzer in marks:
            for pName in custom.targets:
                try:
                    p=self.plots[pName]
                except KeyError as e:
                    print_("Available plots:",list(self.plots.keys()))
                    raise e

                def mark(p):
                    def makeMark():
                        p.addVerticalMarker()
                    return makeMark
                analyzer.addFunction(mark(p))

        return plots

    def picklePlots(self,wait=False):
        """Writes the necessary information for the plots permanently to disc,
        so that it doesn't have to be generated again
        :param wait: wait for the lock to be allowed to pickle"""

        #        print "Putting some pickles in the jar"

        lines=allLines()
        plots=allPlots()
        if lines and plots:
#            print "Getting lock"
            gotIt=self.pickleLock.acquire(wait)
#            print "Got lock"

            if not gotIt:
                return

            pickleFile=path.join(self.logDir,"pickledPlots")
            pick=pickle.Pickler(open(pickleFile+".tmp","wb"))
            pick.dump(lines.prepareForTransfer())
            pick.dump(plots.prepareForTransfer())
            move(pickleFile+".tmp",pickleFile)

            if hasattr(self,"data"):
                pickleFile=path.join(self.logDir,"pickledUnfinishedData")
                pick=pickle.Pickler(open(pickleFile+".tmp","wb"))
                pick.dump(self.data)
                del pick
                move(pickleFile+".tmp",pickleFile)

#            print "Releasing lock"
            self.pickleLock.release()
#            print "Released lock"

    def setDataSet(self,data):
        if hasattr(self,"data"):
            self.data["analyzed"]=data

    def resetFile(self):
        """The input file changed and we add a marker to all plots"""
        for n in self.plots:
            p = self.plots[n]
            p.addVerticalMarker(colorRGB=(1.,0,0),label="Restart")

# Should work with Python3 and Python2
