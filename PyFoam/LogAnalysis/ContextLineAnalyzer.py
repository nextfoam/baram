#  ICE Revision: $Id$
"""Line analyzer that finds data n lines after a matching line"""

import re

from .LogLineAnalyzer import LogLineAnalyzer

class ContextLineAnalyzer(LogLineAnalyzer):
    """Base class for analyzers that work with a context"""

    def __init__(self,trigger,nr=1):
        """
        :param trigger: The regular expression that has to match before data is collected
        :param nr: The number of lines after the match that data is collected
        """
        LogLineAnalyzer.__init__(self)

        self.trigger=re.compile(trigger)
        self.registerRegexp(self.trigger)
        self.nr=nr

        self.cnt=0

    def doAnalysis(self,line):
        if self.cnt>0:
            self.cnt-=1
            if self.cnt==0:
                self.doActualAnalysis(line)
        else:
            m=self.trigger.match(line)
            if m!=None:
                self.cnt=self.nr
                self.callOnMatch(m)

    def doActualAnalysis(self,line):
        """
        Called nr lines after the match

        :param line: The line that should be analyzed
        """
        pass

    def callOnMatch(self,m):
        """
        Called if the line matches

        :param m: The match-object
        """
        pass

# Should work with Python3 and Python2
