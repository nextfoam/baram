#  ICE Revision: $Id$
"""Analyze Line for an expression and execute a list of functions"""

import re

from .LogLineAnalyzer import LogLineAnalyzer
from .TimeChanger import TimeChanger

from PyFoam import configuration as conf

class TriggerLineAnalyzer(LogLineAnalyzer):
    """Parses the line for a regular expression and when it occurs it executes a
    list of functions"""

    def __init__(self,expr):
        """
        Constructs the analyzer
        """
        LogLineAnalyzer.__init__(self)

        self.exp=re.compile(expr)
        self.registerRegexp(self.exp)

        self._funcs = []

    def addFunction(self,f):
        self._funcs.append(f)

    def doAnalysis(self,line):
        m=self.exp.match(line.strip())
        if m!=None:
            for f in self._funcs:
                f()

# Should work with Python3 and Python2
