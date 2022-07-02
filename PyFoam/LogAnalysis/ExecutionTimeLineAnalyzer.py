#  ICE Revision: $Id$
"""Check for Execution-Time information"""

import re

def executionRegexp():
    """@Return: The regular expression that parses the execution time
    depending on the OpenFOAM-Version"""

    if foamVersionNumber(useConfigurationIfNoInstallation=True)>=(1,3):
        return "^ExecutionTime = (.+) s .ClockTime = (.+) s$"
    else:
        return "^ExecutionTime = (.+) s$"

# from FileLineAnalyzer import FileLineAnalyzer
# from TimeLineLineAnalyzer import TimeLineLineAnalyzer

from .GeneralLineAnalyzer import GeneralLineAnalyzer

from PyFoam.FoamInformation import foamVersionNumber
from PyFoam.Error import warning

class GeneralExecutionLineAnalyzer(GeneralLineAnalyzer):
    """Parses lines for the execution time"""

    def __init__(self,
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        self.hasClock=(foamVersionNumber(useConfigurationIfNoInstallation=True)>=(1,3))
        titles=["cumulated"]
        if self.hasClock:
            titles.append("delta")

        GeneralLineAnalyzer.__init__(self,
                                     titles=titles,
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)

        self.exp=re.compile(executionRegexp())
        self.registerRegexp(self.exp)

        self.resetFile()

    def resetFile(self):
        self.lastTime=0.
        self.time=0.
        if self.hasClock:
            self.lastClock=0.
            self.clock=0.

        self.first=True;
        self.firstTime=0.
        if self.hasClock:
            self.firstClock=0.

    def startAnalysis(self,match):
        try:
            self.time=float(match.group(1))

            # clear phase (if set) so that function objects don't append a phase name
            self.setPhase()

        except ValueError:
            warning(match.group(1),"is not a valid number")
            self.time=float("NaN")
        if self.hasClock:
            try:
                self.clock=float(match.group(2))
            except ValueError:
                warning(match.group(2),"is not a valid number")
                self.clock=float("NaN")

    def endAnalysis(self,match):
        self.lastTime = self.time
        if self.first:
            self.firstTime=self.time

        if self.hasClock:
            self.lastClock = self.clock
            if self.first:
                self.firstClock=self.clock

        self.first=False

    def addToFiles(self,match):
        self.files.write("executionTime",self.parent.getTime(),(self.time,self.time-self.lastTime))

        if self.hasClock:
            self.files.write("wallClockTime",self.parent.getTime(),(self.clock,self.clock-self.lastClock))

    def addToTimelines(self,match):
        self.lines.setValue("cpu",self.time-self.lastTime)

        if self.hasClock:
            self.lines.setValue("clock",self.clock-self.lastClock)

    def clockFirst(self):
        """Returns the Wall-Clock-Time of the first timestep"""
        if self.hasClock:
            return self.firstClock
        else:
            return None

    def clockTotal(self):
        """Returns the total Wall-Clock-Time"""
        if self.hasClock:
            return self.clock
        else:
            return None

    def timeFirst(self):
        """Returns the CPU-Time of the first timestep"""
        return self.firstTime

    def timeTotal(self):
        """Returns the total CPU-Time"""
        return self.time


class ExecutionTimeLineAnalyzer(GeneralExecutionLineAnalyzer):
    """Parses lines for the execution time"""

    def __init__(self):
        GeneralExecutionLineAnalyzer.__init__(self,doTimelines=False)

##        self.exp=re.compile(executionRegexp())
##        self.lastTime=0.

##    def doAnalysis(self,line):
##        """Writes total execution time and time needed since last
##        time-step"""
##        m=self.exp.match(line)
##        if m!=None:
##            time=float(m.group(1))

##            self.files.write("executionTime",self.parent.getTime(),(time,time-self.lastTime))

##            self.lastTime = time

class TimeLineExecutionTimeLineAnalyzer(GeneralExecutionLineAnalyzer):
    """Parses lines for the execution time"""

    def __init__(self):
        GeneralExecutionLineAnalyzer.__init__(self,doFiles=False)

##        self.hasClock=(foamVersionNumber()>=(1,3))

##        self.exp=re.compile(executionRegexp())

##        self.lastTime=0.
##        if self.hasClock:
##            self.lastClock=0.

##    def doAnalysis(self,line):
##        """Writes total execution time and time needed since last
##        time-step"""
##        m=self.exp.match(line)
##        if m!=None:
##            time=float(m.group(1))
##            if self.hasClock:
##                clock=float(m.group(2))

##            self.lines.setValue("cpu",time-self.lastTime)
##            self.lastTime = time

##            if self.hasClock:
##                self.lines.setValue("clock",clock-self.lastClock)
##                self.lastClock = clock



# Should work with Python3 and Python2
