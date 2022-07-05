#  ICE Revision: $Id$
"""Analyze Line for an expression"""

import re

from .LogLineAnalyzer import LogLineAnalyzer
from .TimeChanger import TimeChanger

from PyFoam import configuration as conf

class CountLineAnalyzer(LogLineAnalyzer,TimeChanger):
    """Parses the line for a regular expression and counts how often it occurs.
    The purpose of this class is to be a stand-in for the TimeLineAnalyzer
    in instances where there is no time"""

    def __init__(self,expr):
        """
        Constructs the analyzer
        """
        LogLineAnalyzer.__init__(self)
        TimeChanger.__init__(self)

        self.exp=re.compile(expr)
        self.registerRegexp(self.exp)

        self._nr = 0

    def notifyNewTime(self,nr):
        try:
            self.notify(float(nr))
            if self.parent is not None and type(self.parent.time)==float:
                # self.writeProgress("t = %10g" % self.parent.time)
                pass

        except ValueError:
            pass

        self.sendTime()

    def doAnalysis(self,line):
        m=self.exp.match(line.strip())
        if m!=None:
            self._nr += 1
            self.notifyNewTime(self._nr)

    def reset(self):
        self._nr = 0

    def getTime(self):
        return self._nr

# Should work with Python3 and Python2
