#  ICE Revision: $Id$
"""Output of time-dependent data"""

from .BasicFile import BasicFile
from os import path

class OutputFile(BasicFile):
    """output of time dependent data"""

    def __init__(self,name,titles=[],parent=None):
        """
        :param name: name of the file
        :param titles: Titles of the columns
        :param parent: A parent collection that knows about opened and
        closed files
        """
        BasicFile.__init__(self,name)

        self.parent=parent
        self.setTitles(titles)

#    def __del__(self):
#            print "Deleting File",self.name

    def setTitles(self,titles):
        """
        Sets the titles anew. Only has an effect if the file hasn't been opened yet

        :param titles: The new titles
        """
        self.titles=titles

    def outputAtStart(self):
        """
        Write column titles if present
        """
        if len(self.titles)>0:
            fh=self.getHandle()
            fh.write("# time")
            for c in self.titles:
                fh.write(" \t"+c)
            fh.write("\n")

    def write(self,time,data):
        """write data set

        :param time: the current time
        :param data: tuple with data"""
        self.writeLine( (time,)+data)

    def callAtOpen(self):
        """A hook that gets called when the file is opened"""
        if self.parent:
            self.parent.addToOpenList(path.basename(self.name))

    def callAtClose(self):
        """A hook that gets called when the file is closed"""
        if self.parent:
            self.parent.removeFromOpenList(path.basename(self.name))

    def __repr__(self):
        """Output for debugging"""

        result="Outfile:"+self.name
        if self.isOpen:
            result+=" OPEN"
        if self.append:
            result+=" APPEND"
        if self.handle:
            result+=" HANDLE"
        return result

# Should work with Python3 and Python2
