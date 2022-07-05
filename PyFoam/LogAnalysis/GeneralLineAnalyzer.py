#  ICE Revision: $Id$
"""Line analyzer with output and the capability to store lines"""

from .LogLineAnalyzer import LogLineAnalyzer
from PyFoam.Basics.OutFileCollection import OutFileCollection
from PyFoam.Basics.TimeLineCollection import TimeLineCollection

from PyFoam.Error import warning
import sys

class GeneralLineAnalyzer(LogLineAnalyzer):
    """Base class for analyzers that write data to files and store time-lines

    Combines the capabilities of TimeLineLineAnalyzer and FileLineAnalyzer"""

    # phase of the solver to distinguish similar results
    __phase = ""

    def __init__(self,
                 doTimelines=False,
                 doFiles=False,
                 titles=[],
                 accumulation=None,
                 singleFile=False,
                 progressTemplate=None,
                 plotIterations=False,
#                 plotIterations=True,
                 startTime=None,
                 endTime=None):
        """
        :param titles: The titles of the data elements
        :param progressTemplate: Progress output to be reported
        :param plotIterations: plot iterations instead of the real time
        """
        LogLineAnalyzer.__init__(self)

        self.doTimelines=doTimelines
        self.doFiles=doFiles
        self.singleFile=singleFile
        self.plotIterations=plotIterations
        if self.plotIterations:
            self.iterCounter=0

        self.files=None
        self.titles=titles

        self.setTitles(titles)

        accu="first"
        if accumulation!=None:
            accu=accumulation
        if self.doTimelines:
            self.lines=TimeLineCollection(accumulation=accu)
        else:
            self.lines=None

        self.startTime=startTime
        self.endTime=endTime

        self.publisher = None

        self.didProgress=False
        self.progressTemplate=progressTemplate

    @staticmethod
    def setPhase(p=""):
        GeneralLineAnalyzer.__phase = p

    @staticmethod
    def fName(n):
        if GeneralLineAnalyzer.__phase=="":
            return n
        else:
            return n+"_"+GeneralLineAnalyzer.__phase

    def getCurrentData(self,structured=False):
        if self.lines:
            return self.lines.getLatestData(structured=structured)
        else:
            return {}

    def setMaster(self, master):
        self.setPublisher(master)

    def setPublisher(self, publisher):
        """Assign another line-analyzer that will do the actual data gathering"""
        self.publisher = publisher
        if self.lines and self.publisher.lines:
            self.publisher.lines.addCollector(self.lines)

    def setTitles(self,titles):
        """
        Sets the titles anew
        :param titles: the new titles
        """
        if self.doFiles:
            self.titles=titles
            if self.files!=None:
                self.files.setTitles(titles)

    def setDirectory(self,oDir):
        """Creates the OutFileCollection-object"""
        if self.doFiles:
            self.files=OutFileCollection(oDir,
                                         titles=self.titles,
                                         singleFile=self.singleFile)
        else:
            self.files=None

    def timeChanged(self):
        """Sets the current time in the timelines"""
        if self.doTimelines and not self.plotIterations:
            try:
                time=float(self.getTime())
                if (self.startTime==None or time>=self.startTime) and (self.endTime==None or time<=self.endTime):
                    self.lines.setTime(self.getTime())
            except ValueError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                warning("Problem with lines",e)
                raise e
        if self.plotIterations:
            self.lines.setTime(self.iterCounter)

        self.didProgress=False
        self.setPhase()

    def getTimeline(self,name):
        """:param name: Name of the timeline to return
        :return: the timeline as two list: the times and the values"""
        if self.doTimelines:
            return self.lines.getTimes(),self.lines.getValues(name)
        else:
            return [],[]

    def stringToMatch(self,line):
        """Returns string to match. To be overriden for multi-line expressions"""
        return line.strip()

    def doMatch(self,line):
        return self.exp.match(self.stringToMatch(line))

    def doAnalysis(self,line):
        """General analysis method. Derived classes should instead override callbacks"""

        m=self.doMatch(line)
        if m!=None:
            self.startAnalysis(m)

            if self.doTimelines:
                if self.plotIterations:
                    self.iterCounter+=1
                    self.lines.setTime(self.iterCounter)
                try:
                    time=float(self.getTime())
                    try:
                        if (self.startTime==None or time>=self.startTime) and (self.endTime==None or time<=self.endTime) or self.plotIterations:
                            self.addToTimelines(m)
                    except ValueError:
                        e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                        warning("Problem doing timelines",e)
                except ValueError:
                    # no valid time information yet
                    pass

            if self.doFiles:
                self.addToFiles(m)

            self.endAnalysis(m)

            if not self.didProgress and self.progressTemplate:
                self.writeProgress(self.processProgressTemplate(m))

            self.didProgress=False

    def processProgressTemplate(self,data):
        """Add progress information"""
        return ""

    def startAnalysis(self,match):
        """Method at the start of a successfull match"""
        pass

    def endAnalysis(self,match):
        """Method at the end of a successfull match"""
        pass

    def addToTimelines(self,match):
        """Method that adds matched data to timelines

        :param match: data matched by a regular expression"""

        pass

    def addToFiles(self,match):
        """Method that adds matched data to files

        :param match: data matched by a regular expression"""

        pass

    def tearDown(self):
        """Closes files"""
        LogLineAnalyzer.tearDown(self)

        if self.files!=None:
            self.files.close()

# Should work with Python3 and Python2
