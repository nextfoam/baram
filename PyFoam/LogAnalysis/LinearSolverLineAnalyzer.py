#  ICE Revision: $Id$
"""Analyze information from the linear solver"""

import re

linearRegExp="^(.+):  Solving for (.+), Initial residual = (.+), Final residual = (.+), No Iterations ([0-9]+).*$"

# from FileLineAnalyzer import FileLineAnalyzer
# from TimeLineLineAnalyzer import TimeLineLineAnalyzer

from .GeneralLineAnalyzer import GeneralLineAnalyzer

from PyFoam.ThirdParty.six import iteritems

class GeneralLinearSolverLineAnalyzer(GeneralLineAnalyzer):
    """Parses for information about the linear solver

    Files of the form linear_<var> are written, where <var> is the
    variable for which the solver was used"""

    def __init__(self,
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        GeneralLineAnalyzer.__init__(self,
                                     titles=["Initial","Final","Iterations"],
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)
        self.exp=re.compile(linearRegExp)
        self.registerRegexp(self.exp)

        if self.doTimelines:
            self.lines.setDefault(1.)
            self.lines.setExtend(True)

    def addToFiles(self,match):
        solver=match.groups()[0]
        name=self.fName(match.groups()[1])
        rest=match.groups()[2:]
        self.files.write("linear_"+name,self.getTime(),rest)

    def addToTimelines(self,match):
        name=self.fName(match.groups()[1])
        resid=match.groups()[2]
        final=match.groups()[3]
        iter=match.groups()[4]
        if resid[0]!="(":
            # regular linear solver
            self.lines.setValue(name,resid)

            self.lines.setAccumulator(name+"_final","last")
            self.lines.setValue(name+"_final",final)
        else:
            # 1.6-ext block-coupled solver
            resids=resid[1:-1].split()
            finals=resid[1:-1].split()
            for i in range(len(resids)):
                nm="%s[%d]" % (name,i)
                self.lines.setValue(nm,resids[i])

                self.lines.setAccumulator(nm+"_final","last")
                self.lines.setValue(nm+"_final",finals[i])

        self.lines.setAccumulator(name+"_iterations","sum")
        self.lines.setValue(name+"_iterations",iter)

    def getCurrentData(self,structured=False):
        tData=GeneralLineAnalyzer.getCurrentData(self,structured=structured)
        if structured:
            from collections import defaultdict
            vals=defaultdict(dict)
            for k,v in iteritems(tData):
                pos=k.rfind("_")
                if pos>0:
                    vals[k[:pos]][k[(pos+1):]]=v
                else:
                    vals[k]["residual"]=v
            return vals
        else:
            return tData

class GeneralLinearSolverIterationsLineAnalyzer(GeneralLinearSolverLineAnalyzer):
    """Parses information about the linear solver and collects the iterations"""

    def __init__(self,
                 doTimelines=True,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        GeneralLinearSolverLineAnalyzer.__init__(self,
                                                 doTimelines=doTimelines,
                                                 doFiles=doFiles,
                                                 singleFile=singleFile,
                                                 startTime=startTime,
                                                 endTime=endTime)

    def addToFiles(self,match):
        pass

    def addToTimelines(self,match):
        name=self.fName(match.groups()[1])
        iter=match.groups()[4]

        self.lines.setAccumulator(name,"sum")
        self.lines.setValue(name,iter)

    def getCurrentData(self,structured=False):
        return GeneralLineAnalyzer.getCurrentData(self,structured=structured)

class LinearSolverLineAnalyzer(GeneralLinearSolverLineAnalyzer):
    """Parses for information about the linear solver

    Files of the form linear_<var> are written, where <var> is the
    variable for which the solver was used"""

    def __init__(self):
        GeneralLinearSolverLineAnalyzer.__init__(self,doTimelines=False)

class TimeLineLinearSolverLineAnalyzer(GeneralLinearSolverLineAnalyzer):
    """Parses for imformation about the linear solver and collects the residuals in timelines"""

    def __init__(self):
        GeneralLinearSolverLineAnalyzer.__init__(self,doFiles=False)

class TimeLineLinearIterationsSolverLineAnalyzer(GeneralLinearSolverIterationsLineAnalyzer):
    """Parses for information about the linear solver and collects the iterations in timelines"""

    def __init__(self):
        GeneralLinearSolverIterationsLineAnalyzer.__init__(self,doFiles=False)

# Should work with Python3 and Python2
