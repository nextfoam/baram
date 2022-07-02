#  ICE Revision: $Id$
"""Analyze OpenFOAM logs"""

from .TimeLineAnalyzer import TimeLineAnalyzer
from .CountLineAnalyzer import CountLineAnalyzer
from PyFoam.Basics.LineReader import LineReader
from PyFoam.Error import error

from PyFoam.ThirdParty.six import iteritems

from PyFoam.Basics.ProgressOutput import ProgressOutput
from PyFoam import configuration as config

from sys import stdout

from copy import deepcopy

import re

class FoamLogAnalyzer(object):
    """Base class for all analyzers

    Administrates and calls a number of LogLineAnlayzers for each
    line"""

    def __init__(self,progress=False):
        """
        :param progress: Print time progress on console?
        """
        self.analyzers={}
        self.time=""
        self.oDir=""
        self.line=LineReader(config().getboolean("SolverOutput","stripSpaces"))
        self.timeListeners=[]
        self.timeTriggers=[]
        self.resetFileTriggers=[]

        self.customExpr=re.compile("Custom([0-9]+)_(.+)")

        if progress:
            self.progressOut=ProgressOutput(stdout)
        else:
            self.progressOut=ProgressOutput()

        # tm=CountLineAnalyzer()
        tm=TimeLineAnalyzer()
        self.addAnalyzer("Time",tm)
        tm.addListener(self.setTime)

        self.analyzedLines = 0

    def tearDown(self):
        """Remove reference to self in children (hoping to remove
        circular dependencies)"""

        for a in list(self.analyzers.values()):
            a.tearDown()
            a.setParent(None)

    def collectData(self,structured=False):
        """Collect dictionaries of collected data (current state)
        from the analyzers
        :return: the dictionary"""

        result={}

        for nm in self.analyzers:
            data=self.analyzers[nm].getCurrentData(structured=structured)
            if len(data)>0:
                m=self.customExpr.match(nm)
                if m:
                    if not "Custom" in result:
                        result["Custom"]={}
                    nr,name=m.groups()
                    result["Custom"][name]=data

                # this will store custom data twice. But we'll keep it
                    # for backward-compatibility
                result[nm]=data

        return result

    def summarizeData(self,col=80):
        """Get a summary of the data"""
        result="="*col
        result+="\nt = {:20}\n".format(self.getTime())

        data=self.collectData(structured=True)

        for k,v in iteritems(data):
            if k.find("Custom")==0 and len(k)>9 and k[8]=="_":
                kk=k[9:]
            elif k in  ["Custom"]:
                continue
            else:
                kk=k

            if isinstance(v,(dict,)):
                result+=kk+" "+"-"*(col-len(kk)-1)+"\n"
                isDicts=True
                for k1,v1 in iteritems(v):
                    if not isinstance(v1,(dict,)):
                        isDicts=False
                        break
                if not isDicts:
                    maxLen=max([len(k1) for k1 in v.keys()])
                    wFormat="{:%d} : {:8g}" % maxLen
                    chunks=[wFormat.format(k1,v[k1]) for k1 in sorted(v.keys())]
                    maxLen=max([len(c) for c in chunks])
                    chunks=[c if len(c)>=maxLen else c+" "*(maxLen-len(c)) for c in chunks]
                    nrChunks=col // (max([len(e) for e in chunks])+3)
                    for i in range(0,len(chunks),nrChunks):
                        result+=" | ".join(chunks[i:(i+nrChunks)])+"\n"
                else:
                    maxLen=0

                    for k1,v1 in iteritems(v):
                        maxLen=max(maxLen,max([len(k1)+2-8]+[len(k2) for k2 in v1.keys()]))

                    wFormat="{:%d} : {:8g}" % maxLen
                    chunks={}
                    chunkLen=0
                    for k1,v1 in iteritems(v):
                        chunks[k1]=[wFormat.format(k2,v1[k2]) for k2 in sorted(v1.keys())]
                        chunkLen=max(chunkLen,
                                     max([len(e) for e in chunks[k1]]))

                    for k1 in sorted(v.keys()):
                        chunks[k1]=[k1+" "+"_"*(chunkLen-len(k1)-1)]+chunks[k1]
                        chunks[k1]=[c if len(c)>=chunkLen else c+" "*(chunkLen-len(c)) for c in chunks[k1]]
                        nrChunks=col // (chunkLen+3)
                        for i in range(0,len(chunks[k1]),nrChunks):
                            result+=" | ".join(chunks[k1][i:(i+nrChunks)])+"\n"
            else:
                result+=kk+": "+v+" "+"-"*(col-len(k)-len(v)-3)+"\n"
        return result;

    def setTime(self,time):
        """Sets the time and alert all the LineAnalyzers that the time has changed
        :param time: the new value of the time
        """
        if time!=self.time:
            self.progressOut.reset()

            self.time=time
            for listener in self.timeListeners:
                listener.timeChanged()
            for nm in self.analyzers:
                self.analyzers[nm].timeChanged()
            self.checkTriggers()

            data=self.collectData()
            for listener in self.timeListeners:
                try:
                    # make sure everyone gets a separate copy
                    listener.setDataSet(deepcopy(data))
                except AttributeError:
                    # seems that the listener doesn't want the data
                    pass

    def resetFile(self):
        """Propagate a reset to the actual analyzers"""
        for nm in self.analyzers:
            self.analyzers[nm].resetFile()

        for f in self.resetFileTriggers:
            f()

    def writeProgress(self,msg):
        """Write a message to the progress output"""
        self.progressOut(msg)

    def addTimeListener(self,listener):
        """:param listener: An object that is notified when the time changes. Has to
        implement a timeChanged method"""
        if not 'timeChanged' in dir(listener):
            error("Error. Object has no timeChanged-method:"+str(listener))
        else:
            self.timeListeners.append(listener)

    def addResetFileTrigger(self,f):
        self.resetFileTriggers.append(f)

    def listAnalyzers(self):
        """:returns: A list with the names of the Analyzers"""
        return list(self.analyzers.keys())

    def hasAnalyzer(self,name):
        """Is this LogLineAnalyzer name there"""
        return name in self.analyzers

    def getAnalyzer(self,name):
        """Get the LogLineAnalyzer name"""
        if name in self.analyzers:
            return self.analyzers[name]
        else:
            return None

    def addAnalyzer(self,name,obj):
        """Adds an analyzer

        obj - A LogLineAnalyzer
        name - the name of the analyzer"""

        obj.setParent(self)
        self.analyzers[name]=obj

    def analyzeLine(self,line):
        """Calls all the anlyzers for a line"""
        self.analyzedLines+=1

        for nm in self.analyzers:
            self.analyzers[nm].doAnalysis(line)

    def analyze(self,fh):
        """Analyzes a file (one line at a time)

        fh - handle of the file"""
        while(self.line.read(fh)):
            self.analyzeLine(self.line.line)

    def goOn(self):
        """Checks with all the analyzers

        If one analyzer returns False it returns False"""
        result=True

        for nm in self.analyzers:
            #            print nm,self.analyzers[nm].goOn()
            result=result and self.analyzers[nm].goOn()

        return result

    def getTime(self):
        """Gets the current time"""
        return str(self.time)

    def isPastTime(self,check):
        """Are we past a given Time?"""
        if check is None:
            return False
        try:
            t=float(self.getTime())
            return t>check
        except ValueError:
            return False

    def setDirectory(self,d):
        """Sets the output directory for all the analyzers"""
        self.oDir=d
        for nm in self.analyzers:
            self.analyzers[nm].setDirectory(self.oDir)

    def getDirectory(self):
        """Gets the output directory"""
        return self.oDir

    def addTrigger(self,time,func,once=True,until=None):
        """Adds a trigger function that is to be called as soon as
        the simulation time exceeds a certain value
        :param time: the time at which the function should be triggered
        :param func: the trigger function
        :param once: Should this function be called once or at every time-step
        :param until: The time until which the trigger should be called"""

        data={}
        data["time"]=float(time)
        data["func"]=func
        if until!=None:
            data["until"]=float(until)
            once=False
        data["once"]=once

        self.timeTriggers.append(data)

    def checkTriggers(self):
        """Check for and execute the triggered functions"""

        remove=[]
        for i in range(len(self.timeTriggers)):
            t=self.timeTriggers[i]
            if t["time"]<=self.time:
                t["func"]()
                if t["once"]:
                    remove.append(i)
                elif "until" in t:
                    if t["until"]<=self.time:
                        remove.append(i)

        remove.reverse()

        for i in remove:
            self.timeTriggers.pop(i)

# Should work with Python3 and Python2
