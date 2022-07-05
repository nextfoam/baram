#  ICE Revision: $Id$
"""Read a file line by line"""

from PyFoam.Infrastructure.Logging import foamLogger
from PyFoam.ThirdParty.six import print_

import sys

from PyFoam.ThirdParty.six import PY3

class LineReader(object):
    """Read a line from a file

    The line is stripped of whitespaces at the start and the end of
    the line and stored in a variable self.line"""

    def __init__(self,stripAllSpaces=True):
        """:param stripAllSpaces: remove all spaces from the line (instead of
        only those on the left side)"""
        self.stripAll=stripAllSpaces
        self.line=""
        self.goOn=True
        self.wasInterupted=False
        self.keyboardInterupted=False
        self.reset()

    def bytesRead(self):
        """:return: number of bytes that were already read"""
        return self.bytes

    def reset(self):
        """Reset the reader"""
        self.bytes=0

    def userSaidStop(self):
        """:return: whether the reader caught a Keyboard-interrupt"""
        return self.wasInterupted

    def read(self,fh):
        """reads the next line

        fh - filehandle to read from

        Return value: False if the end of the file was reached. True
        otherwise"""

        if not self.goOn:
            return False

        try:
            self.line=fh.readline()
            if PY3:
                if type(self.line) is bytes:
                    self.line=self.line.decode()
            self.bytes+=len(self.line)
        except KeyboardInterrupt:
            e=sys.exc_info()[1]
            foamLogger().warning("Keyboard Interrupt")
            print_(" Interrupted by the Keyboard")
            self.wasInterupted=True
            self.keyboardInterupted=True
            self.goOn=False
            self.line=""
            return False

        if len(self.line)>0:
            status=True
        else:
            status=False
        if self.stripAll:
            self.line=self.line.strip()
        else:
            self.line=self.line.rstrip()

        return status

# Should work with Python3 and Python2
