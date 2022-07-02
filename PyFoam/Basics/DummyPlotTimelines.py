#  ICE Revision: $Id$
"""Plots a collection of timelines"""

from PyFoam.Error import warning,error

from PyFoam.Basics.CustomPlotInfo import readCustomPlotInfo,CustomPlotInfo

from .GeneralPlotTimelines import GeneralPlotTimelines

from platform import uname

class DummyPlotTimelines(GeneralPlotTimelines):
    """This class doesn't open a window and plots nothing"""

    def __init__(self,
                 timelines,
                 custom,
                 showWindow=True,
                 quiet=False,
                 registry=None):
        """:param timelines: The timelines object
        :type timelines: TimeLineCollection
        :param custom: A CustomplotInfo-object. Values in this object usually override the
        other options
        """

        GeneralPlotTimelines.__init__(self,timelines,custom,showWindow=showWindow,registry=registry)

        self.redo()

    def buildData(self, times, name, title, lastValid, tag=None):
        """Build the implementation specific data
        :param times: The vector of times for which data exists
        :param name: the name under which the data is stored in the timeline
        :param title: the title under which this will be displayed"""

        pass

    def preparePlot(self):
        """Prepare the plotting window"""

        pass

    def doReplot(self):
        """Replot the whole data"""

        pass

    def addVerticalMarker(self,colorRGB=None,label=None):
        """Add a vertical line to the graph at the current time. Optionally
        color it and add a label"""

        pass

    def actualSetTitle(self,title):
        """Sets the title"""

        pass

    def setYLabel(self,title):
        """Sets the label on the first Y-Axis"""

        pass

    def setYLabel2(self,title):
        """Sets the label on the second Y-Axis"""

        pass

    def doHardcopy(self,filename,form,termOpts=None):
        """Write the contents of the plot to disk
        :param filename: Name of the file without type extension
        :param form: String describing the format"""

        pass

# Should work with Python3 and Python2
