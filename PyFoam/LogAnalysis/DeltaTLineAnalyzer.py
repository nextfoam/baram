#  ICE Revision: $Id$
"""Check lines for timestep information"""

import re

continutityRegExp="^deltaT = (.+)$"

# from FileLineAnalyzer import FileLineAnalyzer
# from TimeLineLineAnalyzer import TimeLineLineAnalyzer

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class GeneralDeltaTLineAnalyzer(GeneralLineAnalyzer):
    """Parses line for continuity information"""

    def __init__(self,
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        GeneralLineAnalyzer.__init__(self,
                                     titles=["deltaT"],
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)
        self.exp=re.compile(continutityRegExp)
        self.registerRegexp(self.exp)

    def addToFiles(self,match):
        self.files.write("deltaT",self.parent.getTime(),match.groups())

    def addToTimelines(self,match):
        self.lines.setValue("deltaT",match.groups()[0])

class DeltaTLineAnalyzer(GeneralDeltaTLineAnalyzer):
    """Parses line for continuity information"""

    def __init__(self):
        GeneralDeltaTLineAnalyzer.__init__(self,doTimelines=False)



class TimeLineDeltaTLineAnalyzer(GeneralDeltaTLineAnalyzer):
    """Parses line for continuity information"""

    def __init__(self):
        GeneralDeltaTLineAnalyzer.__init__(self,doFiles=False)

# Should work with Python3 and Python2
