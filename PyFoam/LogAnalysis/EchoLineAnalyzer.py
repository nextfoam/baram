#  ICE Revision: $Id$
"""Echos a line"""

from .LogLineAnalyzer import LogLineAnalyzer

from PyFoam.ThirdParty.six import print_

class EchoLineAnalyzer(LogLineAnalyzer):
    """Test implementation. Simply echos every line it gets"""

    def __init__(self):
        LogLineAnalyzer.__init__(self)

    def doAnalysis(self,line):
        print_("<"+self.parent.getTime()+">"+line+"<")

# Should work with Python3 and Python2
