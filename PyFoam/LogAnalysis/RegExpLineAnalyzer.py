#  ICE Revision: $Id$
"""Analyzes lines with regular expressions"""

import re
import sys

# for the eval
from math import *

from .GeneralLineAnalyzer import GeneralLineAnalyzer
from PyFoam.Error import warning
from PyFoam.ThirdParty.six import integer_types,print_

class RegExpLineAnalyzer(GeneralLineAnalyzer):
    """Parses lines for an arbitrary regular expression

    Only one data-set is stored per time-step

    One pattern group of the RegExp can be used as a unique
    identifier, so that more than one data-sets can be stored per
    time-step

    The string %f% in the regular expression is replaced with the
    regular expression for a floating point number
    """

    def __init__(self,
                 name,
                 exp,
                 idNr=None,
                 dataTransformations=None,
                 stringValues=None,
                 titles=[],
                 doTimelines=False,
                 doFiles=True,
                 accumulation=None,
                 progressTemplate=None,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        """
        :param name: name of the expression (needed for output
        :param exp: the regular expression, %f% will be replaced with the
        regular expression for a float
        :param idNr: number of the pattern group that is used as an identifier
        :param titles: titles of the columns
        :param dataTransformations: List of expression strings with replacement
        values of the form "$1", "$2" which are replaced with the groups of the
        regular expression. If this is set the original data is discarded and
        the values when inserting them to the replacements are used
        :param accumulation: How multiple values should be accumulated
        """
        GeneralLineAnalyzer.__init__(self,
                                     titles=titles,
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     accumulation=accumulation,
                                     progressTemplate=progressTemplate,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)

        self.name=name
        self.idNr=idNr
        if isinstance(self.idNr,integer_types):
            self.idNr=[self.idNr]

        self.stringValues=stringValues if stringValues is not None else []
        self.stringValues.sort()

        if self.idNr is not None:
            for iNr in self.idNr:
                if iNr in self.stringValues:
                    self.stringValues.remove(iNr)
            stringValues=[]
            for v in self.stringValues:
                sm=sum(1 for i in self.idNr if i<v)
                stringValues.append(v-sm)
            self.stringValues=stringValues

        self.multiLine=False
        self.linesToMatch=None

        exp=exp.replace("%f%",self.floatRegExp)

        self.strExp=exp
        reFlags=0

        if self.strExp.find(r"\n")>-1:
            self.multiLine=True
            from collections import deque

            self.linesToMatch=deque([],maxlen=1+self.strExp.count(r'\n'))
            reFlags=re.MULTILINE

        try:
            self.exp=re.compile(self.strExp,reFlags)
        except:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            e.args=e.args+("While compiling regular expression '{}'".format(self.strExp),)
            raise e

        self.registerRegexp(self.exp)

        self.data={}
        self.dataTransformations=dataTransformations

    def stringToMatch(self,line):
        """Returns string to match. To be overriden for multi-line expressions"""
        if self.multiLine:
            self.linesToMatch.append(line)

            return "\n".join(self.linesToMatch)
        else:
            return line.strip()

    def startAnalysis(self,match):
        self.tm=self.parent.getTime()
        if self.tm=="":
            self.tm="-1e10"

    def processProgressTemplate(self,data):
        if self.progressTemplate.count("{")>0 and self.progressTemplate.count("{")==self.progressTemplate.count("}"):
            vals=[]
            for v in data.groups():
                try:
                    vals.append(float(v))
                except ValueErro:
                    vals.append(v)
            return self.progressTemplate.format(*vals)
        myProgress=self.progressTemplate
        for i,g in enumerate(data.groups()):
            myProgress=myProgress.replace("$%d" % i,g)
        return myProgress

    def makeID(self,match):
        return "_".join(match.group(i) for i in self.idNr)

    def filterIdFromData(self,fdata):
        return tuple([fdata[i] for i in range(len(fdata)) if i+1 not in self.idNr])

    def transformData(self,d):
        # create in revers order so that $10 is replaced before $1
        replacements=[]
        for i in range(len(d),0,-1):
            replacements.append(("$%d" % i,d[i-1]))

        vals=[]

        for tVal in self.dataTransformations:
            for o,n in replacements:
                tVal=tVal.replace(o,n)
            try:
                vals.append(eval(tVal))
            except:
                vals.append(0.)
                warning("Problem evaluating",tVal)

        # print(d,"to",vals)

        return tuple(vals)

    def addToFiles(self,match):
        name=self.fName(self.name)
        fdata=match.groups()
        if self.dataTransformations:
            tdata=self.transformData(fdata)

        if self.idNr is not None:
            ID=self.makeID(match)
            name+="_"+ID
            fdata=self.filterIdFromData(fdata)
        else:
            ID=""

        if self.dataTransformations:
            fdata=tdata

        self.sub(ID)[float(self.tm)]=fdata
        if ID!="":
            self.sub("")[float(self.tm)]=match.groups()

        self.files.write(name,self.tm,fdata)

    def addToTimelines(self,match):
        name=self.fName(self.name)
        fdata=match.groups()

        if self.dataTransformations:
            tdata=self.transformData(fdata)

        prefix=""
        if self.idNr is not None:
            ID=self.makeID(match)
            prefix=ID+"_"
            fdata=self.filterIdFromData(fdata)

        if self.dataTransformations:
            fdata=tdata

        for i in range(len(fdata)):
            if i in self.stringValues:
                val=fdata[i]
            else:
                val=float(fdata[i])
            name=prefix+"value %d" % i
            if i<len(self.titles):
                if self.idNr is not None and self.titles[i].find("%s")>=0:
                    name=self.titles[i] % ID
                else:
                    name=prefix+str(self.titles[i])

            if i not in self.stringValues:
                self.lines.setValue(self.fName(name),val)

    def sub(self,ID):
        """ get the data set for the identifier ID"""
        if ID not in self.data:
            self.data[ID]={}
        return self.data[ID]

    def getTimes(self,ID=None):
        """get the available time for the identifier ID"""
        if ID==None:
            ID=""
        return list(self.sub(ID).keys())

    def getIDs(self):
        """get a list of the available IDs"""
        ids=list(self.data.keys())
        if "" in ids:
            ids.remove("")
        return ids

    def getLast(self,ID=None):
        """get the last time for the identifier ID"""
        times=self.getTimes(ID)
        if len(times)>0:
            return max(times)
        else:
            return None

    def getData(self,time=None,ID=None):
        """get a data value at a specific time for a specific ID"""
        if ID==None:
            ID=""

        if time==None:
            time=self.getLast(ID)
        else:
            time=float(time)

        data=self.sub(ID)

        if time in data:
            return data[time]
        else:
            return None

    def getCurrentData(self,structured=False):
        tData=GeneralLineAnalyzer.getCurrentData(self,structured=structured)
        if structured and self.idNr:
            from collections import defaultdict
            vals=defaultdict(dict)
            for k in tData.keys():
                pos=len(k)
                for i in self.idNr:
                    pos=k.rfind("_",0,pos)
                vals[k[:pos]][k[(pos+1):]]=tData[k]
            return vals
        else:
            return tData

class RegExpTimeLineLineAnalyzer(RegExpLineAnalyzer):
    """Class that stores results as timelines, too"""

    def __init__(self,
                 name,
                 exp,
                 titles=[],
                 startTime=None,
                 endTime=None):
        """
        :param name: name of the expression (needed for output
        :param exp: the regular expression, %f% will be replaced with the
        regular expression for a float
        :param titles: titles of the columns
        """
        RegExpLineAnalyzer.__init__(self,
                                    name,
                                    exp,
                                    idNr=None,
                                    titles=titles,
                                    doTimelines=True,
                                    doFiles=False,
                                    startTime=startTime,
                                    endTime=endTime)

# Should work with Python3 and Python2
