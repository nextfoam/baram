#  ICE Revision: $Id$
"""Check lines for Boundedness"""

import re

boundingRegExp="^bounding (.+), min: (.+) max: (.+) average: (.+)$"

# from FileLineAnalyzer import FileLineAnalyzer
# from TimeLineLineAnalyzer import TimeLineLineAnalyzer

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class GeneralBoundingLineAnalyzer(GeneralLineAnalyzer):
    """Parses the line for information about variables being bounded

    Writes files of the form bounding_<var>"""

    def __init__(self,
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        GeneralLineAnalyzer.__init__(self,
                                     titles=['Minimum','Maximum','Average'],
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)
        self.exp=re.compile(boundingRegExp)
        self.registerRegexp(self.exp)

    def addToFiles(self,match):
        name=self.fName(match.groups()[0])
        rest=match.groups()[1:]
        self.files.write("bounding_"+name,self.parent.getTime(),rest)

    def addToTimelines(self,match):
        name=self.fName(match.groups()[0])
        rest=match.groups()[1:]

        self.lines.setValue(name+"_min",rest[0])
        self.lines.setValue(name+"_max",rest[1])
        self.lines.setValue(name+"_avg",rest[2])

class BoundingLineAnalyzer(GeneralBoundingLineAnalyzer):
    """Parses the line for information about variables being bounded

    Writes files of the form bounding_<var>"""

    def __init__(self):
        GeneralBoundingLineAnalyzer.__init__(self,doTimelines=False)

##        FileLineAnalyzer.__init__(self,titles=['Minimum','Maximum','Average'])
##        self.exp=re.compile(boundingRegExp)

##    def doAnalysis(self,line):
##        m=self.exp.match(line)
##        if m!=None:
##            name=m.groups()[0]
##            rest=m.groups()[1:]
##            self.files.write("bounding_"+name,self.parent.getTime(),rest)

class TimeLineBoundingLineAnalyzer(GeneralBoundingLineAnalyzer):
    """Parses the line for information about variables being bounded"""

    def __init__(self):
        GeneralBoundingLineAnalyzer.__init__(self,doFiles=False)

##        TimeLineLineAnalyzer.__init__(self)
##        self.exp=re.compile(boundingRegExp)

##    def doAnalysis(self,line):
##        m=self.exp.match(line)
##        if m!=None:
##            name=m.groups()[0]
##            rest=m.groups()[1:]

##            self.lines.setValue(name+"_min",rest[0])
##            self.lines.setValue(name+"_max",rest[1])
##            self.lines.setValue(name+"_avg",rest[2])


# Should work with Python3 and Python2
