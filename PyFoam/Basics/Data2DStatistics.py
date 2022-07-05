#  ICE Revision: $Id$
"""Data structure to do some calculations on the results from
SpreadSheetData-methods metrics and compare that are organized in 2
dimensions"""

import sys

from PyFoam.Basics.TableData import TableData
from PyFoam.Error import error

from math import *
import collections

class Data2DStatistics(object):
    """Oranize statistics about data in 2D-Tables and do basic
    calculations on it"""

    def __init__(self,metrics,
                 compare=None,
                 small=1e-10,
                 noStrings=False,
                 failureValue=None):
        """
	:param metrics: metrics of the data
        :param compare: metrics of the comparsion with another data-set
        :param small: the value that is considered to be close to 0
        :param noStrings: only put numbers into the tables
        :param failureValue: the value to use if an evaluation fails
	"""
        self.__metrics=metrics
        self.__compare=compare
        self.small=small
        self.noStrings=noStrings
        self.failureValue=failureValue

    def _getLabels(self):
        """Return a tuple with the names of the rows and the
        columns. Assumes that the names for the first data-set are
        valid for all"""
        colNames=list(self.__metrics.keys())
        rowNames=list(self.__metrics[colNames[0]].keys())

        return rowNames,colNames

    def _makeEmptyTable(self):
        """Create an empty table to fill the data in"""
        r,c=self._getLabels()
        return TableData(r,c)

    def _extractTable(self,name,data=None):
        """Extract data and fill it into a data-table
        :param name: name of the entry that should be got
        :param data: the dataset. If unset then self.__metrics is used"""
        if data==None:
            data=self.__metrics

        tab=self._makeEmptyTable()
        row,col=self._getLabels()
        for r in row:
            for c in col:
                tab[(r,c)]=data[c][r][name]

        return tab

    def names(self):
        "Valid data names"
        row,col=self._getLabels()
        return list(self.__metrics[col[0]][row[0]].keys())

    def compare(self):
        """Get a separate Data2DStatistics with the compare-data (if
        present)"""
        if self.__compare==None:
            error("No compare data present")
        return Data2DStatistics(self.__compare)

    def __getitem__(self,name):
        return self._extractTable(name)

    def func(self,func,val):
        """Evaluate a function on the data
        :param func: either a callable function or a string that evaluates to a callable
        :param val: name of the data value to use"""
        if isinstance(func, collections.Callable):
            f=func
        elif type(func)==str:
            f=eval(func)
            if not isinstance(f, collections.Callable):
                error(func,"does not evaluate to a callable")
        else:
            error(func,"is neither callable nor a string")

        tab=self._makeEmptyTable()

        row,col=self._getLabels()
        data=self[val]

        for r in row:
            for c in col:
                tab[(r,c)]=f(data[(r,c)])

        return tab

    def range(self):
        """Return a table with the ranges of the data"""
        minD=self._extractTable("min")
        maxD=self._extractTable("max")
        tab=self._makeEmptyTable()

        row,col=self._getLabels()
        for r in row:
            for c in col:
                tab[(r,c)]=(minD[(r,c)],maxD[(r,c)])

        return tab

    def __relativeErrorInternal(self,name):
        """Return a table with the relative error
        :param name: spcifies the name under which the error is found in the data"""
        dataRange=self.range()
        if self.__compare==None:
            error("Need comparison data for relative error")

        maxError=self._extractTable(name,self.__compare)
        rErr=self._makeEmptyTable()

        row,col=self._getLabels()
        for r in row:
            for c in col:
                rng=(lambda r:r[1]-r[0])(dataRange[(r,c)])
                mx=maxError[(r,c)]
                if rng>self.small:
                    try:
                        rErr[(r,c)]=mx/rng
                    except TypeError:
                        e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                        rErr[(r,c)]=self.failureValue
                        if self.failureValue==None:
                            raise e
                elif mx>self.small:
                    if self.noStrings:
                        rErr[(r,c)]=0.
                    else:
                        rErr[(r,c)]="constant (%g)" % mx
                else:
                    if self.noStrings:
                        rErr[(r,c)]=0.
                    else:
                        rErr[(r,c)]="constant =="

        return rErr

    def relativeError(self):
        """Return a table with the relative error"""
        return self.__relativeErrorInternal("max")

    def relativeAverageError(self):
        """Return a table with the relative average error"""
        return self.__relativeErrorInternal("wAverage")

# Should work with Python3 and Python2
