#  ICE Revision: $Id$
"""Watches output and analyzes it"""

from .BasicWatcher import BasicWatcher
from .AnalyzedCommon import AnalyzedCommon

class AnalyzedWatcher(BasicWatcher,AnalyzedCommon):
    def __init__(self,filename,analyzer,silent=False,tailLength=1000,sleep=0.1):
        """:param analyzer: analyzer
        :param filename: name of the logfile to watch
        :param silent: if True no output is sent to stdout
        :param tailLength: number of bytes at the end of the fail that should be output.
        Because data is output on a per-line-basis
        :param sleep: interval to sleep if no line is returned"""

        BasicWatcher.__init__(self,filename,silent=silent,tailLength=tailLength,sleep=sleep)
        AnalyzedCommon.__init__(self,self.filename,analyzer)

# Should work with Python3 and Python2
