#  ICE Revision: $Id$
"""
Application class that implements pyFoamRunAtMultipleTimes
"""

from .PyFoamApplication import PyFoamApplication
from .CommonSelectTimesteps import CommonSelectTimesteps
from .CommonReportUsage import CommonReportUsage
from .CommonReportRunnerData import CommonReportRunnerData
from .CommonStandardOutput import CommonStandardOutput
from .CommonServer import CommonServer
from .CommonParallel import CommonParallel

from PyFoam.Execution.UtilityRunner import UtilityRunner
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from PyFoam.ThirdParty.six import print_

class RunAtMultipleTimes(PyFoamApplication,
                         CommonReportUsage,
                         CommonReportRunnerData,
                         CommonSelectTimesteps,
                         CommonParallel,
                         CommonServer,
                         CommonStandardOutput):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Runs a OpenFoam Utility that only supports being run for one or all
times to be run at multiple selected times
        """
        PyFoamApplication.__init__(self,
                                   exactNr=False,
                                   args=args,
                                   description=description,
                                   **kwargs)

    def addOptions(self):
        CommonStandardOutput.addOptions(self,logname="RunAtMultipleTimes")
        CommonParallel.addOptions(self)
        CommonServer.addOptions(self)
        CommonSelectTimesteps.addOptions(self,defaultUnique=True)
        CommonReportUsage.addOptions(self)
        CommonReportRunnerData.addOptions(self)

    def run(self):
        cName=self.parser.casePath()

        times=self.processTimestepOptions(SolutionDirectory(cName,archive=None))
        if len(times)<1:
            self.warning("Can't continue without time-steps")
            return

        lam=self.getParallel(SolutionDirectory(cName,archive=None))

        data=[]

        for i,t in enumerate(times):
            print_(" Running for t=",t)
            run=UtilityRunner(argv=self.parser.getArgs()+["-time",t],
                              silent=self.opts.progress or self.opts.silent,
                              server=self.opts.server,
                              logname="%s.%s.t=%s" % (self.opts.logname,self.parser.getApplication(),t),
                              compressLog=self.opts.compress,
                              logTail=self.opts.logTail,
                              noLog=self.opts.noLog,
                              echoCommandLine=self.opts.echoCommandPrefix,
                              lam=lam)

            self.addToCaseLog(cName,"Starting for t=%s",t)

            run.start()

            self.setData({t:run.data})

            self.addToCaseLog(cName,"Ending")

            self.reportUsage(run)
            self.reportRunnerData(run)

            data.append(run.data)

        return data

# Should work with Python3 and Python2
