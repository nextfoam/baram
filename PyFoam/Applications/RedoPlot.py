#! /usr/bin/env python
"""A test utility that ghets all the information necessary for plotting from a remote machine and writes some plots<<"""

import sys

from PyFoam.Applications.PyFoamApplication import PyFoamApplication

from PyFoam.ThirdParty.six import PY3
if PY3:
    from xmlrpc.client import Fault,ProtocolError
else:
    from xmlrpclib import Fault,ProtocolError

from PyFoam.Infrastructure.ServerBase import getServerProxy

import socket

from optparse import OptionGroup
from PyFoam.ThirdParty.six.moves import cPickle as pickle
from time import sleep

from PyFoam.Basics.TimeLineCollection import TimeLineCollection,TimeLinesRegistry
from PyFoam.Basics.PlotTimelinesFactory import createPlotTimelines
from PyFoam.Basics.GeneralPlotTimelines import PlotLinesRegistry
from PyFoam.Basics.CustomPlotInfo import CustomPlotInfo
from PyFoam.Error import error,warning

from PyFoam.ThirdParty.six import print_,iteritems

class RedoPlot(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Either connects to a running pyFoam-Server and gets all the
information for plotting or reads the relevant data from a pickle file
and either displays the plot or writes the plots to file
        """
        if args:
            self.quiet=True
        else:
            self.quiet=False

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] (<host> <port>|<pickleFile>)",
                                   interspersed=True,
                                   nr=1,
                                   exactNr=False,
                                   **kwargs)

    def addOptions(self):
        mode=OptionGroup(self.parser,
                         "Input mode",
                         "How we get the data")
        mode.add_option("--server",
                        dest="server",
                        action="store_true",
                        default=False,
                        help="Get the data from a FoamServer")
        mode.add_option("--pickle-file",
                        dest="pickle",
                        action="store_true",
                        default=False,
                        help="Get the data from a pickle-file")

        self.parser.add_option_group(mode)

        output=OptionGroup(self.parser,
                           "Output",
                           "Output of the data")
        output.add_option("--csv-files",
                          dest="csvFiles",
                          action="store_true",
                          default=False,
                          help="Write CSV-files instead of plotting")
        output.add_option("--excel-files",
                          dest="excelFiles",
                          action="store_true",
                          default=False,
                          help="Write Excel-files (using pandas) instead of plotting")
        output.add_option("--pandas-data",
                          dest="pandasData",
                          action="store_true",
                          default=False,
                          help="Pass the raw data in pandas-format")
        output.add_option("--pandas-series",
                          dest="pandasSeries",
                          action="store_true",
                          default=False,
                          help="Pass the raw data in pandas-series")
        output.add_option("--numpy-data",
                          dest="numpyData",
                          action="store_true",
                          default=False,
                          help="Pass the raw data in numpy")
        output.add_option("--file-prefix",
                          dest="filePrefix",
                          default="",
                          help="Prefix to add to the names of the data files")
        output.add_option("--raw-lines",
                          dest="rawLines",
                          action="store_true",
                          default=False,
                          help="Write the raw line data (not the way it is plotted)")
        self.parser.add_option_group(output)

        plot=OptionGroup(self.parser,
                         "Plot mode",
                         "How the data should be plotted")

        plot.add_option("--implementation",
                        default="matplotlib",
                        dest="implementation",
                        help="The implementation that should be used for plotting")
        plot.add_option("--terminal-options",
                        default="",
                        dest="terminalOptions",
                        help="Terminal options that should be sent to the implementation (for instance 'size 1280,960' for gnuplot). Not all implementations will use this")
        plot.add_option("--show-window",
                        dest="showWindow",
                        action="store_true",
                        default=False,
                        help="Show the window with the plot")
        plot.add_option("--no-write-pictures",
                        dest="writePictures",
                        action="store_false",
                        default=True,
                        help="Do not write picture files")
        plot.add_option("--picture-prefix",
                        dest="prefix",
                        default="",
                        help="Prefix to add to the names of the picture files")
        plot.add_option("--sleep-time",
                        dest="sleepTime",
                        action="store",
                        default=0.1,
                        type="float",
                        help="How long to wait to allow gnuplot to finish. Default: %default")
        plot.add_option("--insert-titles",
                        dest="insertTitles",
                        action="store_true",
                        default=False,
                        help="Add the title to the plots")
        plot.add_option("--start",
                        dest="start",
                        action="store",
                        default=None,
                        type="float",
                        help="Start the plot at this time. If undefined starts at the beginning of the data")
        plot.add_option("--end",
                        dest="end",
                        action="store",
                        default=None,
                        type="float",
                        help="End the plot at this time. If undefined ends at the end of the data")

        self.parser.add_option_group(plot)

    def run(self):
        if not self.opts.server and not self.opts.pickle:
            error("No mode selected")
        if self.opts.server and self.opts.pickle:
            error("Both modes selected")

        doPandas=self.opts.pandasData or self.opts.pandasSeries

        if self.opts.server:
            if len(self.parser.getArgs())!=2:
                error("Need a server and a port to be specified")

            host=self.parser.getArgs()[0]
            port=int(self.parser.getArgs()[1])

            try:
                self.server=getServerProxy(host,port)
                methods=self.server.system.listMethods()
            except socket.error:
                reason = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.error("Socket error while connecting:",reason)
            except ProtocolError:
                reason = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.error("XMLRPC-problem",reason)

            plotInfo=self.executeCommand("getPlots()")
            lineInfo=self.executeCommand("getPlotData()")
        else:
            if len(self.parser.getArgs())!=1:
                warning("Only the first parameter is used")

            fName=self.parser.getArgs()[0]
            unpick=pickle.Unpickler(open(fName,"rb"))

            lineInfo=unpick.load()
            plotInfo=unpick.load()

        if not self.quiet:
            print_("Found",len(plotInfo),"plots and",len(lineInfo),"data sets")

        registry=TimeLinesRegistry()
        for nr,line in iteritems(lineInfo):
            if not self.quiet:
                print_("Adding line",nr)
            TimeLineCollection(preloadData=line,registry=registry)

        registry.resolveCollectors()

        if (self.opts.csvFiles or self.opts.excelFiles or doPandas or self.opts.numpyData) and self.opts.rawLines:
            rawData={}
            rawSeries={}
            rawNumpy={}

            for k,l in iteritems(registry.lines):
                name=str(k)
                if type(k)==int:
                    name="Line%d" % k
                csvName=self.opts.filePrefix+name+".csv"
                if self.opts.csvFiles:
                    if not self.quiet:
                        print_("Writing",k,"to",csvName)
                    l.getData().writeCSV(csvName)
                if self.opts.excelFiles:
                    xlsName=self.opts.filePrefix+name+".xls"
                    if not self.quiet:
                        print_("Writing",k,"to",xlsName)
                    l.getData().getData().to_excel(xlsName)
                if self.opts.pandasData:
                    rawData[k]=l.getData().getData()
                if self.opts.numpyData:
                    rawNumpy[k]=l.getData().data.copy()
                if self.opts.pandasSeries:
                    rawSeries[k]=l.getData().getSeries()

            if self.opts.numpyData:
                self.setData({"rawNumpy":rawNumpy})
            if self.opts.pandasData:
                self.setData({"rawData":rawData})
            if self.opts.pandasSeries:
                self.setData({"rawSeries":rawSeries})

            if self.opts.csvFiles or self.opts.excelFiles:
                return

        pRegistry=PlotLinesRegistry()

        plotNumpy={}
        plotData={}
        plotSeries={}

        for i,p in iteritems(plotInfo):
            theId=p["id"]
            if not self.quiet:
                print_("Plotting",i,":",theId,end=" ")
            spec=CustomPlotInfo(raw=p["spec"])
            if len(registry.get(p["data"]).getTimes())>0 and len(registry.get(p["data"]).getValueNames())>0:
                if self.opts.csvFiles or self.opts.excelFiles or doPandas or self.opts.numpyData:
                    dataSet=registry.get(p["data"]).getData()
                    if self.opts.csvFiles:
                        dataSet.writeCSV(self.opts.filePrefix+theId+".csv")
                    if self.opts.excelFiles:
                        dataSet.getData().to_excel(self.opts.filePrefix+theId+".xls")
                    if self.opts.numpyData:
                        plotNumpy[theId]=dataSet.data.copy()
                    if self.opts.pandasData:
                        plotData[theId]=dataSet.getData()
                    if self.opts.pandasSeries:
                        plotSeries[theId]=dataSet.getSeries()
                else:
                    if self.opts.start or self.opts.end:
                        # rewrite CustomPlotInfo one of these days
                        if "start" in spec.getDict():
                            self.warning("Overriding plot start",spec["start"],
                                         "with",self.opts.start)
                        spec.set("start",self.opts.start)
                        if "end" in spec.getDict():
                            self.warning("Overriding plot end",spec["end"],
                                         "with",self.opts.end)
                        spec.set("end",self.opts.end)

                    mp=createPlotTimelines(registry.get(p["data"]),
                                           spec,
                                           implementation=self.opts.implementation,
                                           showWindow=self.opts.showWindow,
                                           registry=pRegistry)
                    if self.opts.insertTitles:
                        mp.actualSetTitle(p["spec"]["theTitle"])
                    if self.opts.writePictures:
                        if mp.hasData():
                            mp.doHardcopy(self.opts.prefix+theId,
                                          "png",
                                          termOpts=self.opts.terminalOptions)
                        else:
                            if not self.quiet:
                                print_("has no data",end=" ")
                if not self.quiet:
                    print_()
            else:
                if not self.quiet:
                    print_("No data - skipping")

            if not(self.opts.csvFiles or doPandas):
                sleep(self.opts.sleepTime) # there seems to be a timing issue with Gnuplot

        if self.opts.numpyData:
            self.setData({"plotNumpy":plotNumpy})
        if self.opts.pandasData:
            self.setData({"plotData":plotData})
        if self.opts.pandasSeries:
            self.setData({"plotSeries":plotSeries})


    def executeCommand(self,cmd):
        result=None
        try:
            result=eval("self.server."+cmd)
            if result==None: # this needed to catch the unmarschalled-None-exception
                return None
        except Fault:
            reason = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            if not self.quiet:
                print_("XMLRPC-problem:",reason.faultString)
        except socket.error:
            reason = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            if not self.quiet:
                print_("Problem with socket (server propably dead):",reason)
        except TypeError:
            reason = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            if not self.quiet:
                print_("Type error: ",reason)
            result=None
        except SyntaxError:
            reason = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            if not self.quiet:
                print_("Syntax Error in:",cmd)

        return result

# Should work with Python3 and Python2
