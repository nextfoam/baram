#  ICE Revision: $Id$
"""Do analysis for a line with values"""

from .FileLineAnalyzer import FileLineAnalyzer
from .NameFinderLineAnalyzer import NameFinderLineAnalyzer

class ValueLineAnalyzer(FileLineAnalyzer):
    """Parses lines for numeric values

    The line starts with a predefined string"""

    def __init__(self,name,pre,titles=[]):
        """
        :param name: name of the expression (needed for output)
        :param pre: the string that starts the line
        """
        FileLineAnalyzer.__init__(self,titles)

        self.name=name
        self.pre=pre

    def doAnalysis(self,line):
        """Analyzes line and writes the data"""
        tm=self.parent.getTime()
        if tm=="":
            return

        m=line.find(self.pre)
        if m>=0:
            rest=line[m+len(self.pre):]
            fdata=()
            for teil in rest.split():
                try:
                    val=float(teil)
                    fdata+=(val,)
                except ValueError:
                    pass

            self.files.write(self.name,tm,fdata)

class ValueNameFinderLineAnalyzer(NameFinderLineAnalyzer):
    """Finds the names and notifies it's ValueLineAnalyzer"""

    def __init__(self,trigger,analyze,val,idNr=1,nr=1):
        """
        :param trigger: The regular expression that has to match before data is collected
        :param nr: The number of lines after the match that data is collected
        :param analyze: The regular expression that is used for analysis
        :param idNr: The id of the group that is used for analysis
        :param val: The ValueLineAnalyzer that needs the names
        """

        NameFinderLineAnalyzer.__init__(self,trigger,analyze,idNr=idNr,nr=nr)

        self.val=val

    def callOnChange(self):
        self.val.setTitles(self.names)

# Should work with Python3 and Python2
