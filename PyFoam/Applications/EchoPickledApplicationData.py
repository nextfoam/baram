#  ICE Revision: $Id$
"""
Application class that implements pyFoamEchoPickledApplicationData
"""

from .PyFoamApplication import PyFoamApplication

from .CommonPickledDataInput import CommonPickledDataInput

class EchoPickledApplicationData(PyFoamApplication,
                     CommonPickledDataInput):
    def __init__(self,
                 args=None,
                 inputApp=None,
                 **kwargs):
        description="""\ Reads a file with pickled application data
and if asked for prints it. Mainly used for testing the exchange of
data via pickled data
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options]",
                                   nr=0,
                                   changeVersion=False,
                                   interspersed=True,
                                   inputApp=inputApp,
                                   **kwargs)

    def addOptions(self):
        CommonPickledDataInput.addOptions(self)

    def run(self):
        self.setData(self.readPickledData())

# Should work with Python3 and Python2
