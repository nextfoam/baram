#  ICE Revision: $Id$
"""Doesn't really analyze the lines but returns values from a data file"""

from .GeneralLineAnalyzer import GeneralLineAnalyzer
from PyFoam.Basics.SpreadsheetData import SpreadsheetData

class ReplayDataFileAnalyzer(GeneralLineAnalyzer):
    """Reads Data into a SpreadsheetData-object and then every time a
    new time value comes up returns the data from that file"""

    def __init__(self,
                 timeName=None,
                 validData=None,
                 validMatchRegexp=False,
                 csvName=None,
                 txtName=None,
                 excelName=None,
                 namePrefix=None,
                 skip_header=0,
                 stripCharacters=None,
                 progressTemplate=None,
                 replaceFirstLine=None,
                 startTime=None,
                 endTime=None):
        self.__data=SpreadsheetData(timeName=timeName,
                                    validData=validData,
                                    validMatchRegexp=validMatchRegexp,
                                    csvName=csvName,
                                    txtName=txtName,
                                    excelName=excelName,
                                    skip_header=skip_header,
                                    stripCharacters=stripCharacters,
                                    replaceFirstLine=replaceFirstLine)
        self.namePrefix=namePrefix
        GeneralLineAnalyzer.__init__(self,
                                     titles=[self.makeName(n) for n in self.__data.names(withTime=False)],
                                     doTimelines=True,
                                     doFiles=False,
                                     progressTemplate=progressTemplate,
                                     startTime=startTime,
                                     endTime=endTime)
        self.timeNew=False
        self.tRange=self.__data.tRange()

    def makeName(self,name):
        if self.namePrefix is None:
            return name
        else:
            return self.namePrefix+name

    def timeChanged(self):
        time=float(self.getTime())
        if time<self.tRange[0] or time>self.tRange[1]:
            return
        self.timeNew=True
        self.lines.setTime(time)

    def doMatch(self,line):
        if self.timeNew:
            time=float(self.getTime())
            if time<self.tRange[0] or time>self.tRange[1]:
                return None
            data=self.__data(time,invalidExtend=True)
            self.timeNew=False
            return {self.makeName(k):v for k,v in data.items()}
        else:
            return None

    def addToTimelines(self,data):
        for t in self.titles:
            self.lines.setValue(self.fName(t),data[t])

    def processProgressTemplate(self,data):
        ldata={k[len(self.namePrefix):]:data[k] for k in data}
        myProgress=self.progressTemplate.format(**ldata)
        return myProgress
