#  ICE Revision: $Id: $
"""
Collects data and writes it to a CSV-file. Optionally return a pandas-data-frame
"""

import csv

from PyFoam.Error import warning

from PyFoam.ThirdParty.six import string_types

class CSVCollection(object):
    """
    Collects data like a dictionary. Writes it to a line in a CSV-file.
    If the dictionary is extended the whole file is rewritten
    """
    def __init__(self,name=None):
        """:param name: name of the file. If unset no file will be written (only data collected)"""
        self.name=name
        self.headers=[]
        self.headerDict={}
        self.data=[self.headerDict]
        self.current={}
        self.file=None
        self.writer=None
        self.renew=True

    def __setitem__(self,key,value):
        """Sets a value in the current dataset
        :param key: the key
        :param value: and it's value"""

        if not key in self.headers:
            self.headers.append(key)
            self.renew=True
            self.headerDict[key]=key

        self.current[key]=value

    def write(self):
        """Writes a line to disk and starts a new one"""

        self.data.append(self.current)
        if self.name:
            if self.renew:
                if self.file!=None:
                    self.file.close()
                self.file=open(self.name,"w")
                self.writer=csv.DictWriter(self.file,self.headers)
                self.writer.writerows(self.data)
                self.renew=False
            else:
                self.writer.writerow(self.current)
            self.file.flush()
        self.current={}

    def clear(self):
        """Resets the last line"""
        self.current={}

    def __call__(self,usePandas=True):
        """Return the data as a pandas-Dataframe
        :param usePandas: whether data should be returned in pandas-format.
        Otherwise numpy"""
        if usePandas:
            try:
                from PyFoam.Wrappers.Pandas import PyFoamDataFrame

                data={}
                for k in self.headers:
                    vals=[]
                    for d in self.data[1:]:
                        try:
                            v=d[k]
                        except KeyError:
                            v=None

                        vals.append(self.__makeSimple(v))
                    data[k]=vals
                return PyFoamDataFrame(data)
            except ImportError:
                warning("pandas-library not installed. Returning 'None'")
                return None
        else:
            try:
                try:
                    import numpy
                except ImportError:
                    # assume this is pypy and retry
                    import numpypy
                    import numpy
                data={}
                for k in self.headers:
                    vals=[]
                    for d in self.data[1:]:
                        try:
                            v=d[k]
                        except KeyError:
                            v=None

                        vals.append(self.__makeSimple(v))
                    data[k]=numpy.array(vals)
                return data
            except ImportError:
                warning("numpy-library not installed. Returning 'None'")
                return None

    def __makeSimple(self,v):
        if isinstance(v,string_types):
            try:
                return int(v)
            except ValueError:
                try:
                    return float(v)
                except:
                    return v
        return v
