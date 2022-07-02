#  ICE Revision: $Id$
"""Look for the name of the executable"""

from .LogLineAnalyzer import LogLineAnalyzer

from PyFoam.ThirdParty.six import print_

class ExecNameLineAnalyzer(LogLineAnalyzer):
    """Looks for the name of the executable"""

    def __init__(self):
        LogLineAnalyzer.__init__(self)

        self.execName=None
        self.caseName=None

    def doAnalysis(self,line):
        tmp=line.split()
        if len(tmp)>=3:
            if self.execName is None and tmp[0]=="Exec" and tmp[1]==":":
                self.execName=tmp[2]
                self.notify(self.execName)
            if self.caseName is None and tmp[0]=="Case" and tmp[1]==":":
                self.caseName=tmp[2]
                # self.notify(self.caseName)

# Should work with Python3 and Python2
