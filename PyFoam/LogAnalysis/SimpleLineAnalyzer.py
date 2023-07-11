#  ICE Revision: $Id$
"""Do analysis for simple expressions"""

import re

# from FileLineAnalyzer import FileLineAnalyzer
# from TimeLineLineAnalyzer import TimeLineLineAnalyzer

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class GeneralSimpleLineAnalyzer(GeneralLineAnalyzer):
    """Parses lines for an arbitrary regular expression

    Differs from RegExpLineAnalyzer because it doesn't store its data"""

    def __init__(self,
                 name,
                 exp,
                 idNr=None,
                 idList=None,
                 titles=[],
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        """
        :param name: name of the expression (needed for output)
        :param exp: the regular expression
        :param idNr: number of the pattern group that is used as an identifier
        :param idList: numbers of the pattern group that are used from the expression
        :param titles: titles for the data items"""
        GeneralLineAnalyzer.__init__(self,
                                     titles=titles,
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)

        self.name=name
        self.idNr=idNr
        self.idList=idList
        self.strExp=exp
        self.exp=re.compile(self.strExp)
        self.registerRegexp(self.exp)

    def addToFiles(self,match):
        tm=self.parent.getTime()
        if tm=="":
            return

        name=self.fName(self.name)
        fdata=match.groups()
        if self.idNr!=None:
            ID=match.group(self.idNr)
            name+="_"+ID
            fdata=fdata[:self.idNr-1]+fdata[self.idNr:]

        self.files.write(name,tm,fdata)

    def addToTimelines(self,match):
        tm=self.parent.getTime()
        if tm=="":
            return

        mLen=len(match.groups())
        ids=self.idList
        if ids==None:
            ids=list(range(mLen))
        for i in range(len(ids)):
            ID=ids[i]
            if ID>=mLen:
                continue
            name=self.fName("%s_%d" % (self.name,ID))
            if i<len(self.titles):
                name=self.titles[i]
            data=match.groups()[ID]
            self.lines.setValue(name,data)

class SimpleLineAnalyzer(GeneralSimpleLineAnalyzer):
    """Parses lines for an arbitrary regular expression

    Differs from RegExpLineAnalyzer because it doesn't store its data"""

    def __init__(self,name,exp,idNr=None,titles=[]):
        """
        :param name: name of the expression (needed for output)
        :param exp: the regular expression
        :param idNr: number of the pattern group that is used as an identifier
        :param titles: titles for the data items"""
        GeneralSimpleLineAnalyzer.__init__(self,name,exp,idNr=idNr,titles=titles,doTimelines=False)

class TimeLineSimpleLineAnalyzer(GeneralSimpleLineAnalyzer):
    """Parses lines for an arbitrary regular expression"""

    def __init__(self,name,exp,idList=None,titles=[]):
        """:param  name: name of the expression (needed for output)
        :param exp: the regular expression
        :param idList: numbers of the pattern group that are used from the expression
        :param titles: titles for the data items"""

        GeneralSimpleLineAnalyzer.__init__(self,name,exp,idNr=idList,titles=titles,doFiles=False)

# Should work with Python3 and Python2
