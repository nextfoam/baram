#  ICE Revision: $Id$
"""Plots a collection of timelines"""

from PyFoam.Error import warning,error

from .MatplotlibTimelines import MatplotlibTimelines

class XkcdMatplotlibTimelines(MatplotlibTimelines):
    """This class opens a matplotlib window, modifies it to XKCD-mode and plots a timelines-collection in it"""

    def __init__(self,
                 timelines,
                 custom,
                 showWindow=True,
                 registry=None):
        """:param timelines: The timelines object
        :type timelines: TimeLineCollection
        :param custom: A CustomplotInfo-object. Values in this object usually override the
        other options
        """

        MatplotlibTimelines.__init__(self,
                                     timelines,
                                     custom,
                                     showWindow=showWindow,
                                     registry=registry
        )

        from matplotlib import pyplot
        try:
            pyplot.xkcd()
        except AttributeError:
            from matplotlib import __version__
            warning("Installed version",__version__,
                    " of Matplotlib does not support XKCD-mode (this is supported starting with version 1.3). Falling back to normal operations")
# Should work with Python3 and Python2
