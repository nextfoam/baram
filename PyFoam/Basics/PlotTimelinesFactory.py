#  ICE Revision: $Id$
"""Creates subclasses of GeneralPlotTimelines"""

from PyFoam.Basics.GnuplotTimelines import GnuplotTimelines,validTerminals
from PyFoam.Basics.MatplotlibTimelines import MatplotlibTimelines
from PyFoam.Basics.XkcdMatplotlibTimelines import XkcdMatplotlibTimelines
from PyFoam.Basics.QwtPlotTimelines import QwtPlotTimelines
from PyFoam.Basics.DummyPlotTimelines import DummyPlotTimelines

from .CustomPlotInfo import CustomPlotInfo


from PyFoam import configuration
from PyFoam.Error import error

lookupTable = { "gnuplot" : GnuplotTimelines ,
                "matplotlib" : MatplotlibTimelines,
                "xkcd" : XkcdMatplotlibTimelines,
                "qwtplot" : QwtPlotTimelines,
                "dummy" : DummyPlotTimelines  }

def createPlotTimelines(timelines,
                        custom,
                        implementation=None,
                        gnuplotTerminal=None,
                        showWindow=True,
                        quiet=False,
                        registry=None):
    """Creates a plotting object
    :param timelines: The timelines object
    :type timelines: TimeLineCollection
    :param custom: specifies how the block should look like
    :param implementation: the implementation that should be used
    """
    if implementation==None:
        implementation=configuration().get("Plotting","preferredImplementation")

    if implementation not in lookupTable:
        error("Requested plotting implementation",implementation,
              "not in list of available implementations",list(lookupTable.keys()))

    options={
        "showWindow" : showWindow,
        "quiet"      : quiet,
        "registry"   : registry
    }

    if implementation=="gnuplot":
        if not gnuplotTerminal:
            gnuplotTerminal=configuration().get("Plotting","gnuplot_terminal")
            if gnuplotTerminal not in validTerminals():
                error("Terminal",gnuplotTerminal,"not in list of valid terminals",
                      ", ".join(validTerminals()))
        options["terminal"]=gnuplotTerminal

    return lookupTable[implementation](timelines,
                                       custom,
                                       **options)

def createPlotTimelinesDirect(name,
                              timelines,
                              persist=None,
                              quiet=False,
                              raiseit=True,
                              with_="lines",
                              alternateAxis=[],
                              forbidden=[],
                              start=None,
                              end=None,
                              logscale=False,
                              alternateLogscale=False,
                              ylabel=None,
                              y2label=None,
                              gnuplotTerminal=None,
                              implementation=None):
    """Creates a plot using some prefefined values
    :param timelines: The timelines object
    :type timelines: TimeLineCollection
    :param persist: Gnuplot window persistst after run
    :param raiseit: Raise the window at every plot
    :param with_: how to plot the data (lines, points, steps)
    :param alternateAxis: list with names that ought to appear on the alternate y-axis
    :param forbidden: A list with strings. If one of those strings is found in a name, it is not plotted
    :param start: First time that should be plotted. If undefined everything from the start is plotted
    :param end: Last time that should be plotted. If undefined data is plotted indefinitly
    :param logscale: Scale the y-axis logarithmic
    :param ylabel: Label of the y-axis
    :param y2label: Label of the alternate y-axis
    :param implementation: the implementation that should be used
    """

    ci=CustomPlotInfo(name=name)
    ci.persist=persist
    ci.raiseit=raiseit
    ci.with_=with_
    ci.alternateAxis=alternateAxis
    ci.forbidden=forbidden
    ci.start=start
    ci.end=end
    ci.logscale=logscale
    ci.alternateLogscale=alternateLogscale
    ci.ylabel=ylabel
    ci.y2label=y2label

    return createPlotTimelines(timelines,ci,
                               quiet=quiet,
                               implementation=implementation,
                               gnuplotTerminal=gnuplotTerminal)

# Should work with Python3 and Python2
