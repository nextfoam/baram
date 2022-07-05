"""Output of progress"""

class ProgressOutput(object):
    """This class generates output for recording the progress"""

    def __init__(self,oFile=None):
        """:param oFile: file-type object that gets the progress output"""
        self.oFile=oFile
        self.oLen=0
        self.storedLen=0
        self._lastProgress=""
        self._currentProgress=""

    def reset(self):
        """reset for the next time"""
        if self.storedLen>self.oLen and self.oFile:
            # clear residual fro mprevious outputs
            self.oFile.write(" "*(self.storedLen-self.oLen))

        self._lastProgress=self._currentProgress
        self._currentProgress=""

        if self.oFile:
            self.oFile.write("\r")
            self.oFile.flush()

        self.storedLen=self.oLen
        self.oLen=0

    def lastProgress(self):
        return self._lastProgress

    def __call__(self,msg):
        """Add to the progress message
        :param msg: the text to add"""
        self._currentProgress+=" "+msg
        if self.oFile:
            self.oFile.write(" "+msg)
            self.oFile.flush()
        self.oLen+=len(msg)+1
