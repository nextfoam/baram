#  ICE Revision: $Id$ 
"""Compare files with Gnuplot"""

from glob import glob
from os import path

class GnuplotCompare(object):
    """Class that compares a number of files with gnuplot"""
    
    def __init__(self,files,col=2):
        """
        :param files: a list of tuples: (filename,name [,col])
        :param col: the default column to use
        """

        self.files=[]
        for f in files:
            if len(f)==3:
                self.files.append(f)
            else:
                self.files.append(f+(col,))

    def writePlotFile(self,name):
        """
        :param name: Name of the file
        """
        
        fh=open(name,'w')
        
        fh.write("plot ")
        first=True

        for f in self.files:
            if first:
                first=False
            else:
                fh.write(" , ")

            fh.write(" \"%s\" using 1:%d title \"%s\" with lines " % (f[0],f[2],f[1]))

        fh.write("\n")
        fh.close()
        
class GlobGnuplotCompare(GnuplotCompare):
    """
    Wrapper to Gnuplot Compare to compare files with similar names
    """
    
    def __init__(self,pattern,col=2,common=None):
        """
        :param pattern: The pattern for which to look
        :param col: The colum that is to be compared
        :param common: String that is to be removed from the filename before using it as a name
        """

        files=[]

        for f in glob(pattern):
            nm=path.basename(f)
            if common!=None:
                nm=nm[len(common):]
            files.append((f,nm,col))

        GnuplotCompare.__init__(self,files)
        
