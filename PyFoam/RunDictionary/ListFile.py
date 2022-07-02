#  ICE Revision: $Id$
"""File that contains only a list (for instance points)"""

from PyFoam.Basics.LineReader import LineReader
from PyFoam.RunDictionary.SolutionFile import SolutionFile

from PyFoam.ThirdParty.six import PY3

if PY3:
    long=int

class ListFile(SolutionFile):
    """Represents a OpenFOAM file with only a list"""

    def __init__(self,place,name):
        """:param place: directory of the file
        :param name: The name of the list file"""

        SolutionFile.__init__(self,place,name)

    def getSize(self):
        """:return: the size of the list"""

        size=-1 # should be long

        l=LineReader()
        self.openFile()

        while l.read(self.fh):
            try:
                size=long(l.line)
                break
            except ValueError:
                pass

        self.closeFile()

        return size

# Should work with Python3 and Python2
