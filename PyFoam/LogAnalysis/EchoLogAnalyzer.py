#  ICE Revision: $Id$
"""Echos a log"""

from .FoamLogAnalyzer import FoamLogAnalyzer

from .EchoLineAnalyzer import EchoLineAnalyzer

class EchoLogAnalyzer(FoamLogAnalyzer):
    """
    Trivial analyzer. It echos the Log-File
    """
    def __init__(self):
        FoamLogAnalyzer.__init__(self,progress=False)

        self.addAnalyzer("Echo",EchoLineAnalyzer())

# Should work with Python3 and Python2
