#  ICE Revision: $Id$
"""Command is run and output is analyzed"""

from PyFoam.Execution.BasicRunner import BasicRunner
from PyFoam.Execution.StepAnalyzedCommon import StepAnalyzedCommon

class AnalyzedRunner(StepAnalyzedCommon,BasicRunner):
    """The output of a command is analyzed while being run

    Side effects (files written etc) depend on the analyzer"""

    def __init__(self,analyzer,
                 argv=None,
                 silent=False,
                 logname="PyFoamSolve",
                 splitThres=2048,
                 split_fraction_unchanged=0.2,
                 server=False,
                 lam=None,
                 compressLog=False,
                 restart=False,
                 noLog=False,
                 logTail=None,
                 remark=None,
                 parameters=None,
                 jobId=None,
                 smallestFreq=60.,
                 echoCommandLine=None):
        """ :param analyzer: the analyzer for the output
        argv, silent, logname, server, lam, noLog - see BasicRunner"""
        BasicRunner.__init__(self,argv,silent,logname,
                             server=server,
                             lam=lam,
                             restart=restart,
                             compressLog=compressLog,
                             noLog=noLog,
                             logTail=logTail,
                             remark=remark,
                             parameters=parameters,
                             echoCommandLine=echoCommandLine,
                             jobId=jobId)
        StepAnalyzedCommon.__init__(self,
                                    logname,
                                    analyzer,
                                    splitThres=splitThres,
                                    split_fraction_unchanged=split_fraction_unchanged,
                                    smallestFreq=smallestFreq)

        self.writeToStateFile("LogDir",self.logDir)

    def lineHandle(self,line):
        """Not to be called: calls the analyzer for the current line"""
        StepAnalyzedCommon.lineHandle(self,line)
        BasicRunner.lineHandle(self,line)

    def lastTime(self):
        return self.getTime()

    def firstCpuTime(self):
        exe=self.getAnalyzer("Execution")
        if exe==None:
            return None
        else:
            return exe.timeFirst()

    def firstClockTime(self):
        exe=self.getAnalyzer("Execution")
        if exe==None:
            return None
        else:
            return exe.clockFirst()

    def totalCpuTime(self):
        exe=self.getAnalyzer("Execution")
        if exe==None:
            return None
        else:
            return exe.timeTotal()

    def totalClockTime(self):
        exe=self.getAnalyzer("Execution")
        if exe==None:
            return None
        else:
            return exe.clockTotal()

    def stopHandle(self):
        BasicRunner.stopHandle(self)
        StepAnalyzedCommon.stopHandle(self)

        self.tearDown()
