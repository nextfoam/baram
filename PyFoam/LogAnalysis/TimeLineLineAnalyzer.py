#  ICE Revision: $Id$
"""Line analyzer that collects datga in arrays"""

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class TimeLineLineAnalyzer(GeneralLineAnalyzer):
    """Base class for analyzers that collect data in arrays

    Just a stub to enable legacy code"""
    def __init__(self):
        GeneralLineAnalyzer.__init__(self,doTimelines=True)

# Should work with Python3 and Python2
