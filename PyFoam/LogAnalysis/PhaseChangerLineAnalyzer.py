#  ICE Revision: $Id$
"""Analyzes lines with regular expressions and changes the phase if it fits"""

import re

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class PhaseChangerLineAnalyzer(GeneralLineAnalyzer):
    """Parses lines for an arbitrary regular expression
    and sets the phase if it fits
    """


    def __init__(self,
                 exp,
                 idNr=None):
        """
        :param name: name of the expression (needed for output
        :param exp: that holds the phase name
        :param idNr: number of the pattern group that is used as the phase name
        """
        GeneralLineAnalyzer.__init__(self,
                                     doTimelines=False,
                                     doFiles=False)

        self.idNr=idNr
        self.exp=re.compile(exp)
        self.registerRegexp(self.exp)

    def doAnalysis(self,line):
        """Look for the pattern. If it matches set the phase name"""

        m=self.exp.match(line.strip())
        if m!=None:
            self.setPhase(m.group(self.idNr))

# Should work with Python3 and Python2
