#  ICE Revision: $Id$
"""Base class for analyzing lines"""

from PyFoam.Error import error

class LogLineAnalyzer(object):
    """Base class for the analysis of all lines from a OpenFOAM-log

    Lines are available one at a time"""

    allRegexp=[]

    floatRegExp="[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"

    @classmethod
    def registerRegexp(self,exp):
        if exp not in LogLineAnalyzer.allRegexp:
            LogLineAnalyzer.allRegexp.append(exp)

    def __init__(self):
        self.parent=None
        self.eventListeners=[]

    def doAnalysis(self,line):
        """Analyze a line

        line - the line to be analyzed

        This method carries the main functionality in the sub-classes"""
        pass

    def timeChanged(self):
        """The value of the time has changed in the Log-file

        For subclasses that need to know the current time"""
        pass

    def setParent(self,parent):
        """Introduces the LineAnalyzer to its supervisor

        :param parent: The Analyzer class of which this is a part"""
        self.parent=parent

    def writeProgress(self,msg):
        """Let the parent write an additional progress message"""
        if self.parent:
            self.parent.writeProgress(msg)

    def setDirectory(self,oDir):
        """Set the directory to which output is to be written (if any
        output is written)"""
        pass

    def goOn(self):
        """If the analyzer thinks the simulation should be stopped
        (for instance because of convergence) it returns false"""
        return True

    def getTime(self):
        """:returns: current time"""
        return self.parent.getTime()

    def addListener(self,func):
        """:param func: a new listener-function that gets notified every time
        the line-analyzer encounters something interesting"""

        self.eventListeners.append(func)

    def notify(self,*data):
        """Notifys the event listeners of an event
        :param data: The data of the event. Everything is possible"""

        for f in self.eventListeners:
            f(*data)

    def tearDown(self):
        """Hook to let every analyzer give its stuff back when the analysis has ended"""
        pass

    def getCurrentData(self,structured=False):
        """Give back the current analyzed data in a dictionary

        To be overwritten by subclasses"""

        return {}

    def resetFile(self):
        """Restart the analysis because we're using a new input file"""
        pass
