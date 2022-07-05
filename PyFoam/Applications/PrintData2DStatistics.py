#  ICE Revision: $Id$
"""
Application class that implements pyFoamPrintData2DStatistics
"""

from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication

from .CommonPickledDataInput import CommonPickledDataInput

from PyFoam.Basics.Data2DStatistics import Data2DStatistics

from PyFoam.ThirdParty.six import print_

class PrintData2DStatistics(PyFoamApplication,
                            CommonPickledDataInput):
    def __init__(self,
                 args=None,
                 inputApp=None,
                 **kwargs):
        description="""\
Reads a file with pickled information with statistics about data
series (as it is usually gnerated by pyFoamTimelinePlot.py and
pyFoamSamplePlot.py) and prints it in a human-readable form.
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options]",
                                   nr=0,
                                   changeVersion=False,
                                   interspersed=True,
                                   inputApp=inputApp,
                                   **kwargs)

    def addOptions(self):
        CommonPickledDataInput.addOptions(self)

        output=OptionGroup(self.parser,
                           "2D Statistics output",
                           "Options that determine what should be output")
        self.parser.add_option_group(output)
        output.add_option("--field",
                          action="append",
                          default=[],
                          dest="field",
                          help="""\
Name of the field that should be printed. Can be specified more than once
""")
        output.add_option("--function",
                          action="append",
                          default=[],
                          dest="function",
                          help="""\ Name of a function that should be
calculated on the data. Either a function in the lambda-syntax or a
function from the math-module
""")
        output.add_option("--relative-error",
                          action="store_true",
                          default=False,
                          dest="relativeError",
                          help="""\
Print the relative error as calculated from the metrics and the compare-data
""")
        output.add_option("--relative-average-error",
                          action="store_true",
                          default=False,
                          dest="relativeAverageError",
                          help="""\
Print the relative average error as calculated from the metrics and the compare-data (weighted average))
""")
        output.add_option("--range",
                          action="store_true",
                          default=False,
                          dest="range",
                          help="""\
Print the range (minimum and maximum) of the data
""")

        input=OptionGroup(self.parser,
                          "2D Statistics intput",
                          "Options that determine what should be used as input")
        self.parser.add_option_group(input)
        input.add_option("--metrics-name",
                          action="store",
                          default="metrics",
                          dest="metricsName",
                          help="""\
Name of the data metric (the main input). Default: %default
""")
        input.add_option("--compare-name",
                          action="store",
                          default="compare",
                          dest="compareName",
                          help="""\
Name of the comparison metric (the secondary input). Default:
%default. Ignored if not present in the data
""")

        parameters=OptionGroup(self.parser,
                               "2D Statistics Paramters",
                               "Options that determine the behaviour of the 2D statistics")
        self.parser.add_option_group(parameters)
        parameters.add_option("--small-threshold",
                              action="store",
                              default=1e-10,
                              type="float",
                              dest="smallThreshold",
                              help="""\
Value that is considered to be close enough to 0. Default:
%default. Used for instance for the relative error calculations
""")


    def run(self):
        data=self.readPickledData()
        result={"originalData":data}
        if self.opts.metricsName in data:
            metrics=data[self.opts.metricsName]
        else:
            self.error("Metrics set",self.opts.metricsName,"not in",list(data.keys()))
        if self.opts.metricsName==self.opts.compareName:
            self.warning("Metrics and comparison",self.opts.compareName,
                         "are the same. No comparison used")
            self.opts.compareName=None

        if self.opts.compareName==None:
            compare=None
        elif self.opts.compareName in data:
            compare=data[self.opts.compareName]
        else:
            self.error("Compare set",self.opts.compareName,"not in",list(data.keys()))

        stat=Data2DStatistics(metrics,
                              compare=compare,
                              small=self.opts.smallThreshold)

        result["statistics"]=stat

        for f in self.opts.field:
            print_("\nField",f)
            try:
                val=stat[f]
                print_(val)
                result[f]=val
            except KeyError:
                print_(" .... not present in",stat.names())

        for f in self.opts.function:
            for v in self.opts.field:
                print_("\nFunction",f,"on field",v)
                try:
                    val=stat.func(f,v)
                    print_(val)
                    result["%s on %s" % (f,v)]=val
                except KeyError:
                    print_(" .... not present in",stat.names())

        if self.opts.relativeError:
            print_("\nRelative Error")
            val=stat.relativeError()
            print_(val)
            result["relativeError"]=val

        if self.opts.relativeAverageError:
            print_("\nRelative Average Error")
            val=stat.relativeAverageError()
            print_(val)
            result["relativeAverageError"]=val

        if self.opts.range:
            print_("\nData range")
            val=stat.range()
            print_(val)
            result["dataRange"]=val

        self.setData(result)

# Should work with Python3 and Python2
