#  ICE Revision: $Id$
"""Basic log analyer with boundedness"""

from .StandardLogAnalyzer import StandardLogAnalyzer

from .BoundingLineAnalyzer import GeneralBoundingLineAnalyzer
from .SimpleLineAnalyzer import GeneralSimpleLineAnalyzer

from PyFoam.FoamInformation import foamVersionNumber

class BoundingLogAnalyzer(StandardLogAnalyzer):
    """
    This analyzer also checks for bounded solutions
    """
    def __init__(self,
                 progress=False,
                 doTimelines=False,
                 doFiles=True,
                 singleFile=False,
                 startTime=None,
                 endTime=None):
        """
        :param progress: Print time progress on console?
        """
        StandardLogAnalyzer.__init__(self,
                                     progress=progress,
                                     doTimelines=doTimelines,
                                     doFiles=doFiles,
                                     singleFile=singleFile,
                                     startTime=startTime,
                                     endTime=endTime)

        self.addAnalyzer("Bounding",
                         GeneralBoundingLineAnalyzer(doTimelines=doTimelines,
                                                     doFiles=doFiles,
                                                     singleFile=singleFile,
                                                     startTime=startTime,
                                                     endTime=endTime))

        if foamVersionNumber(useConfigurationIfNoInstallation=True)<(1,4):
            courantExpression="^Mean and max Courant Numbers = (.+) (.+)$"
        else:
            courantExpression="^Courant Number mean: (.+) max: (\S+).*$"

        self.addAnalyzer("Courant",
                         GeneralSimpleLineAnalyzer("courant",
                                                   courantExpression,
                                                   titles=["mean","max"],
                                                   doTimelines=doTimelines,
                                                   doFiles=doFiles,
                                                   singleFile=singleFile,
                                                   startTime=startTime,
                                                   endTime=endTime))

class BoundingPlotLogAnalyzer(BoundingLogAnalyzer):
    """
    This analyzer also checks for bounded solutions
    """
    def __init__(self):
        BoundingLogAnalyzer.__init__(self,
                                     progress=True,
                                     doTimelines=True,
                                     doFiles=False)

##        self.addAnalyzer("Bounding",GeneralBoundingLineAnalyzer())
##        self.addAnalyzer("Courant",TimeLineSimpleLineAnalyzer("courant","^Mean and max Courant Numbers = (.+) (.+)$",titles=["mean","max"]))

# Should work with Python3 and Python2
