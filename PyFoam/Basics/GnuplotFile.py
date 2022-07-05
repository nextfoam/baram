#  ICE Revision: $Id$
"""Analyze a file with GNUPLOT-Data"""

import re

class GnuplotFile(object):
    def __init__(self,fname):
        """
        :param fname: The filename
        """
        self.fname=fname

        self.titles=[]
        self.analyze()

    def analyze(self):
        """
        Find out how many columns there are and what their names are

        There are two cases:

          1. the first line is not a comment. In this case the column
          names are 'time' and 'value0x'
          depending on how many values are in the first line

          2. the first line is a comment line (it starts with a #).
          In this case the rest of the line
          is analyzed and used as names
        """
        fh=open(self.fname)
        line=fh.readline()
        fh.close()
        line=line.strip()

        if line[0]=='#':
            line=line[1:]
            exp=re.compile("^\s*((\"[^\"]+\")|(\S+))(.*)$")
            while exp.match(line)!=None:
                m=exp.match(line)
                fnd=m.group(1)
                line=m.group(4).strip()
                if fnd[0]=='\"':
                    fnd=fnd[1:-1]
                self.titles.append(fnd)
        else:
            self.titles=["time"]
            els=line.split()
            for i in range(1,len(els)):
                self.titles.append("value%02d" % i )

    def writePlotFile(self,name):
        """
        Writes a file that can be used by Gnuplot

        :param name: name of the file
        """
        fh=open(name,'w')

        fh.write("plot ")
        first=True

        for i in range(1,len(self.titles)):
            if first:
                first=False
            else:
                fh.write(" , ")

            fh.write(" \"%s\" using 1:%d title \"%s\" with lines " % (self.fname,i+1,self.titles[i]))

        fh.write("\n")
        fh.close()
