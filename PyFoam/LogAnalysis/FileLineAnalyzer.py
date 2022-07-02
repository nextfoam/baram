#  ICE Revision: $Id$
"""Line analyzer with output"""

from .GeneralLineAnalyzer import GeneralLineAnalyzer

class FileLineAnalyzer(GeneralLineAnalyzer):
    """Base class for analyzers that write data to files

    Just a stub to enable legacy code"""

    def __init__(self,titles=[]):
        """
        :param titles: The titles of the data elements
        """
        GeneralLineAnalyzer.__init__(self,doFiles=True,titles=titles)

# Should work with Python3 and Python2
