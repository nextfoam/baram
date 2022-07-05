#  ICE Revision: $Id$
"""A simple object for table data where data is accessed with a tuple
(rowLabel,colLabel)"""

from PyFoam.Basics.RestructuredTextHelper import ReSTTable

class TableData(object):
    """A simple table. Current limitiation is that column and row
    labels have to be known at creation time"""

    def __init__(self,rowLabels,columnLabels):
        """
	:param rowLables: the names of the rows
        :param columnLabels: the names of the columns
	"""
        self.__rowLabels=rowLabels
        self.__columnLabels=columnLabels

        self.__data=[[None]*len(self.__columnLabels) for i in range(len(self.__rowLabels))]

    def getIndex(self,labels):
        """Return the numeric indizes for these labels"""
        rowName,colName=labels

        try:
            row=self.__rowLabels.index(rowName)
            col=self.__columnLabels.index(colName)
        except ValueError:
            raise IndexError("Labels",labels,"not in valid labels.",
                             "Rows:",self.__rowLabels,
                             "Col:",self.__columnLabels)

        return (row,col)

    def apply(self,func):
        """Return the table with a function applied to it
        :param func: the function to apply to each element"""
        tab=TableData(self.__rowLabels,self.__columnLabels)
        for r in self.__rowLabels:
            for c in self.__columnLabels:
                tab[(r,c)]=func(self[(r,c)])
        return tab

    def __getitem__(self,labels):
        """:param labels: tuple of the form (row,col)"""
        row,col=self.getIndex(labels)

        return self.__data[row][col]

    def __setitem__(self,labels,val):
        """:param labels: tuple of the form (row,col)"""
        row,col=self.getIndex(labels)

        self.__data[row][col]=val

    def __str__(self):
        """The table as a restructured text object"""

        tab=ReSTTable()
        tab[0]=[""]+self.__columnLabels
        tab.addLine(head=True)
        for i,l in enumerate(self.__data):
            tab[i+1]=[self.__rowLabels[i]]+l

        return str(tab)

    def min(self):
        """Return the minimum of the data in the table"""
        return min([min(d) for d in self.__data])

    def max(self):
        """Return the maximum of the data in the table"""
        return max([max(d) for d in self.__data])

    def columns(self):
        """Iterate over the column names"""
        for c in self.__columnLabels:
            yield c

    def rows(self):
        """Iterate over the row names"""
        for c in self.__rowLabels:
            yield c

# Should work with Python3 and Python2
