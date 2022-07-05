#  ICE Revision: $Id$
"""Extended version of the Pandas-Dataframe
"""

from pandas import DataFrame, Series
from numpy import hstack, unique
from math import isnan

from PyFoam.Error import error, warning, PyFoamException

from PyFoam.ThirdParty.six import string_types, text_type, u

import pandas.api.types as pdtypes
import numpy as np
import pandas as pd

class PyFoamDataFrame(DataFrame):
    """This class adds some convenience functions to the regular Datafram class"""

    validOtherTypes = (DataFrame, Series)

    def __init__(self, *args, **kwargs):
        """Adds no data. Just passes the arguments to the super-class"""
        super(PyFoamDataFrame, self).__init__(*args, **kwargs)
        if not self.__allStrings():
            raise PandasWrapperPyFoamException("Columns must be strings")

        if self.shape == (0, 0):
            return
        if not pdtypes.is_numeric_dtype(self.index.dtype):
            raise TypeError(
                "Index '{}' is of type {} which is not a numberic type".format(
                    self.index.name, self.index.dtype
                )
            )

        if not self.index.is_monotonic_increasing:
            raise TypeError(
                "Index '{}' should be monothinc increasing. It is not".format(
                    self.index.name
                )
            )

    def __allStrings(self, keys=None):
        if keys is None:
            keys = self.keys()
        if isinstance(keys,pd.MultiIndex):
            for key in keys:
                for k in key:
                    if not isinstance(k,string_types):
                        return False
            return True
        else:
            return keys.map(lambda k: isinstance(k, string_types)).all()

    def addData(
        self,
        other,
        sameIndex=True,
        mergeIndex=False,
        prefix=None,
        suffix=None,
        allowExtrapolate=False,
        interpolationMethod="values",
    ):
        """Add data from another DataFrame or Series
        :param other: data as Pandas-DataFrame or Series
        :param sameIndex: assum both have the same indices. If False the other data will be interpolated to the current indices
        :param mergeIndex: make the result indices a mixture of the indices"""
        if not sameIndex and mergeIndex:
            raise PandasWrapperPyFoamException(
                "Can't specify sameIndex=False and mergeIndex=True at the same time"
            )
        if not isinstance(other, self.validOtherTypes):
            raise PandasWrapperPyFoamException(
                "Other data is of type",
                type(other),
                "should be one of",
                self.validOtherTypes,
            )
        if isinstance(other, DataFrame):
            o = other
        else:
            o = DataFrame(other)

        k = o.keys()
        if not self.__allStrings(k):
            raise PandasWrapperPyFoamException("Added data with non-string columns")
        v = k.copy()
        if prefix:
            v = [prefix + n for n in v]
        if suffix:
            v = [n + suffix for n in v]
        if len(set(v) & set(self.keys())) > 0:
            raise PandasWrapperPyFoamException(
                "Keys of this",
                self.keys(),
                "and other",
                v,
                "intersect",
                set(v) & set(self.keys()),
            )
        keys = dict(zip(k, v))
        interpolate = False  # only interpolate if necessary
        if len(self.index) != len(o.index) or (self.index != o.index).any():
            if sameIndex and not mergeIndex:
                raise PandasWrapperPyFoamException(
                    "Other data has different index. Specify sameIndex=False or mergeIndex=True"
                )
            ni = unique(hstack([self.index, o.index]))
            interpolate = True
            if mergeIndex:
                minOld = min(self.index)
                maxOld = max(self.index)

                result = self.reindex(index=ni, copy=True).interpolate(
                    method=interpolationMethod, limit=1
                )

                if not allowExtrapolate:
                    for s in result:
                        result[s][result.index < minOld] = float("NaN")
                        result[s][result.index > maxOld] = float("NaN")
            else:
                # make sure we have values at the current position
                #                  o=o.reindex_axis(ni,axis='index').interpolate(method=interpolationMethod)
                o = o.reindex(index=ni, columns=o.columns).interpolate(
                    method=interpolationMethod
                )
                # ,takeable=True
                result = self.copy()
        else:
            result = self.copy()

        minOld = min(o.index)
        maxOld = max(o.index)
        for k, v in keys.items():
            result[v] = o[k]
            if interpolate:
                result[v] = result[v].interpolate(method=interpolationMethod, limit=1)
                if not allowExtrapolate:
                    result[v][result.index < minOld] = float("NaN")
                    result[v][result.index > maxOld] = float("NaN")

        return PyFoamDataFrame(result)

    def integrate(self, columns=None):
        """Integrate by using the trapezoid rule. Return a dictionary with values.
        :param values: list of column names. If unset all are integrated"""
        return self.__integrateInternal(columns)[0]

    def validLength(self, columns=None):
        """Length were the values are valid (not NaN) Return a dictionary with values.
        :param values: list of column names. If unset all are integrated"""
        return self.__integrateInternal(columns)[1]

    def weightedAverage(self, columns=None):
        """Weighted average. Return a dictionary with values.
        :param values: list of column names. If unset all are integrated"""
        integral, length = self.__integrateInternal(columns)
        result = {}
        for k in integral:
            if length[k] > 0 and not isnan(length[k]):
                result[k] = integral[k] / length[k]
            else:
                result[k] = float("NaN")
        return result

    def __integrateInternal(self, columns):
        if columns is None:
            columns = self.keys()
        integrals = {}
        lengths = {}
        ind = self.index

        for k in columns:
            integrals[k] = 0
            lengths[k] = 0
            if len(ind) < 2:  # no weighting possible
                integrals[k] = float("NaN")
                continue
            val = self[k].values
            for i in range(len(ind)):
                if not isnan(val[i]):
                    w = 0
                    if i > 0:
                        w += 0.5 * (ind[i] - ind[i - 1])
                    if i + 1 < len(ind):
                        w += 0.5 * (ind[i + 1] - ind[i])
                    lengths[k] += w
                    integrals[k] += w * val[i]
            if lengths[k] == 0:
                integrals[k] = float("NaN")

        return integrals, lengths

    def describe(self, *args, **kwargs):
        """Adds our own statistics to the regular describe"""
        d = super(PyFoamDataFrame, self).describe(*args, **kwargs)
        integral, length = self.__integrateInternal(self.keys())
        d = d.append(DataFrame(data=integral, index=["integral"]))
        d = d.append(DataFrame(data=length, index=["valid length"]))
        a = {}
        for k in integral:
            if length[k] > 0 and not isnan(length[k]):
                a[k] = integral[k] / length[k]
            else:
                a[k] = float("NaN")
        d = d.append(DataFrame(data=a, index=["weighted average"]))
        return d

    def __getitem__(self, key):
        """If this gets a number as the key it tries to get the row that is
        nearest to this number. If it is something list-like and the elements
        of the lists are numbers then all the elements of the list are looked
        up, sorted and mad unique. Afterwards it gets the rows that are nearest
        to the numbers. Otherwise it defaults to the []-operator of the
        DataFram-class but converts the result to a PyFoamDataFrame

        """
        idx = None
        if isinstance(key, (float, int)):
            idx = [Series(abs(self.index - key)).idxmin()]
        elif pdtypes.is_list_like(key):
            try:
                k = np.array(key)
                if pdtypes.is_numeric_dtype(k) and not pdtypes.is_bool_dtype(k):
                    idx = []
                    for i in k:
                        nx = Series(abs(self.index - i)).idxmin()
                        if nx not in idx:
                            idx.append(nx)
                        idx.sort()
            except TypeError:
                pass

        if idx is not None:
            return PyFoamDataFrame(self.iloc[idx])

        val = DataFrame.__getitem__(self, key)
        if isinstance(val, DataFrame):
            return PyFoamDataFrame(val)
        else:
            return val

class PandasWrapperPyFoamException(PyFoamException):
    """The PyFoam-exception that does not expect to be caught"""

    def __init__(self, *text):
        descr = "Problem in wrapper to pandas-library"
        #          super(FatalErrorPyFoamException,self).__init__(descr,*text) # does not work with Python 2.4
        PyFoamException.__init__(self, descr, *text)
