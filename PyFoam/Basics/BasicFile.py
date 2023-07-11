#  ICE Revision: $Id$
"""Basic file output"""

class BasicFile(object):
    """File for data output

    The format of the file is: one data-set per line
    Values are separated by tabs

    The file is created the first time it is written"""

    def __init__(self,name):
        """name - name of the file"""
        self.name=name
        self.isOpen=False
        self.handle=None
        self.append=False

    def outputAtStart(self):
        """A hook for outputting stuff at the beginning of the file"""
        pass

    def outputAtEnd(self):
        """A hook for outputting stuff at the end of the file"""
        pass

    def outputAtLineEnd(self):
        """A hook for outputting stuff at the end of each line"""
        pass

    def outputAtLineStart(self):
        """A hook for outputting stuff at the start of each line"""
        pass

    def callAtOpen(self):
        """A hook that gets called when the file is opened"""
        pass

    def callAtClose(self):
        """A hook that gets called when the file is closed"""
        pass

    def getHandle(self):
        """get the file-handle. File is created and opened if it
        wasn't opened before"""
        if not self.isOpen:
            mode="w"
            if self.append:
                mode="a"
            self.handle=open(self.name,mode)
            self.isOpen=True
            if not self.append:
                self.outputAtStart()
            self.callAtOpen()

        return self.handle

    def writeLine(self,data):
        """write a data set

        data - a tuple with the data-set"""
        fh=self.getHandle()
        self.outputAtLineStart()
        first=True
        for d in data:
            if not first:
                fh.write(" \t")
            else:
                first=False
            fh.write(str(d))
        self.outputAtLineEnd()
        fh.write("\n")
        fh.flush()

    def close(self,temporary=False):
        """close the file
        :param temporary: only close the file temporary (to be appended on later)"""
        #        print "Closing file\n"
        if self.handle!=None:
            self.callAtClose()
            if not temporary:
                self.outputAtEnd()
            else:
                self.append=True
            self.handle.close()
            self.handle=None
            self.isOpen=False

# Should work with Python3 and Python2
