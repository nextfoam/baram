#  ICE Revision: $Id$
"""Check lines for continuity information"""

import re

continutityRegExp="^time step continuity errors : sum local = (.+), global = (.+), cumulative = (.+)$"

# from FileLineAnalyzer import FileLineAnalyzer
# from TimeLineLineAnalyzer import TimeLineLineAnalyzer

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class GeneralContinuityLineAnalyzer(GeneralLineAnalyzer):
    """Parses line for continuity information"""

    def __init__(self,
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        GeneralLineAnalyzer.__init__(self,
                                     titles=["Local","Global","Cumulative"],
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)
        self.exp=re.compile(continutityRegExp)
        self.registerRegexp(self.exp)

    def addToFiles(self,match):
        self.files.write(self.fName("continuity"),self.parent.getTime(),match.groups())

    def addToTimelines(self,match):
        self.lines.setValue(self.fName("Global"),match.groups()[1])
        self.lines.setValue(self.fName("Cumulative"),match.groups()[2])

class ContinuityLineAnalyzer(GeneralContinuityLineAnalyzer):
    """Parses line for continuity information"""

    def __init__(self):
        GeneralContinuityLineAnalyzer.__init__(self,doTimelines=False)


##        self.exp=re.compile(continutityRegExp)

##    def doAnalysis(self,line):
##        m=self.exp.match(line)
##        if m!=None:
##            self.files.write("continuity",self.parent.getTime(),m.groups())


class TimeLineContinuityLineAnalyzer(GeneralContinuityLineAnalyzer):
    """Parses line for continuity information"""

    def __init__(self):
        GeneralContinuityLineAnalyzer.__init__(self,doFiles=False)
##        self.exp=re.compile(continutityRegExp)

##    def doAnalysis(self,line):
##        m=self.exp.match(line)
##        if m!=None:
##            #            self.lines.setValue("Local",m.groups()[0])
##            self.lines.setValue("Global",m.groups()[1])
##            self.lines.setValue("Cumulative",m.groups()[2])

# Should work with Python3 and Python2
