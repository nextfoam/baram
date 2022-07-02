#  ICE Revision: $Id$
"""
Base class for pyFoam-applications that have a QT4-GUI
"""

from .PyFoamApplication import PyFoamApplication
from PyQt4 import QtGui,QtCore
import PyFoam

import sys
from os import path

class PyFoamApplicationQt4(PyFoamApplication):
    def __init__(self,
                 args=None,
                 description=None,
                 usage=None,
                 interspersed=False,
                 nr=None,
                 changeVersion=True,
                 exactNr=True):
        """
        :param description: description of the command
        :param usage: Usage
        :param interspersed: Is the command line allowed to be interspersed (options after the arguments)
        :param args: Command line arguments when using the Application as a 'class' from a script
        :param nr: Number of required arguments
        :param changeVersion: May this application change the version of OF used?
        :param exactNr: Must not have more than the required number of arguments
        """
        super(PyFoamApplicationQt4,self).__init__(args=args,
                                                  description=description,
                                                  usage=usage,
                                                  interspersed=interspersed,
                                                  nr=nr,
                                                  changeVersion=changeVersion,
                                                  exactNr=exactNr)
        self.app=None

    def setupGUI(self):
        """
        Set up the graphical user interface
        """
        error("Not a valid QT application")


    def run(self):
        """
        Setup user interface and start QT
        """
        app=QtGui.QApplication(self.parser.getArgs())
        app.setApplicationName(path.basename(sys.argv[0]))
        try:
            app.setApplicationVersion(PyFoam.versionString())
        except AttributeError:
            # Old PyQt
            pass
        app.setOrganizationName("PyFoam")
        self.setupGUI()

        sys.exit(app.exec_())

# Should work with Python3 and Python2
