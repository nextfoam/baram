"""
Application-class that implements pyFoamJoinCSV.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from .CommonReadWriteCSV import CommonReadWriteCSV

from PyFoam.Basics.SpreadsheetData import SpreadsheetData

from os import path

class JoinCSV(PyFoamApplication,
              CommonReadWriteCSV):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Join together two or more CSV-files. Data is resampled to fit the
timescale of the the first CSV-file.

Deprecated: all the functionality of this utility is now present in
pyFoamConvertToCSV.py. This utility will therefore be removed in later
version of PyFoam
"""
        CommonReadWriteCSV.__init__(self)
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <source1.csv> <source2.csv> ... <dest.csv>",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=3,
                                   exactNr=False,
                                   **kwargs)

    def addOptions(self):
        self.depreciationWarning("all functionality of this utility now also implemented in pyFoamConvertToCSV.py")

        CommonReadWriteCSV.addOptions(self)

        how=OptionGroup(self.parser,
                         "How",
                         "How the data should be joined")
        self.parser.add_option_group(how)

        how.add_option("--force",
                       action="store_true",
                       dest="force",
                       default=False,
                       help="Overwrite the destination csv if it already exists")
        how.add_option("--extend-data",
                       action="store_true",
                       dest="extendData",
                       default=False,
                       help="Extend the time range if other files exceed the range of the first file")
        how.add_option("--add-times",
                       action="store_true",
                       dest="addTimes",
                       default=False,
                       help="Actually add the times from the second file instead of interpolating")
        how.add_option("--interpolate-new-times",
                       action="store_true",
                       dest="interpolateNewTime",
                       default=False,
                       help="Interpolate data if new times are added")
        how.add_option("--new-data-no-interpolate",
                       action="store_false",
                       dest="newDataInterpolate",
                       default=True,
                       help="Don't interpolate new data fields to the existing times")

    def run(self):
        dest=self.parser.getArgs()[-1]
        if path.exists(dest) and not self.opts.force:
            self.error("CSV-file",dest,"exists already. Use --force to overwrite")
        sources=self.parser.getArgs()[0:-1]

        data=SpreadsheetData(title=path.splitext(path.basename(sources[0]))[0],
                             validData=self.opts.columns,
                             validMatchRegexp=self.opts.columnsRegexp,
                             **self.dataFormatOptions(sources[0]))
        self.printColumns(sources[0],data)
        self.recalcColumns(data)
        self.rawAddColumns(data)

        if self.opts.time==None:
            self.opts.time=data.names()[0]

        for s in sources[1:]:
            addition=path.splitext(path.basename(s))[0]

            sData=SpreadsheetData(validData=self.opts.columns,
                                  validMatchRegexp=self.opts.columnsRegexp,
                                  **self.dataFormatOptions(s))
            self.printColumns(s,sData)
            self.recalcColumns(sData)
            self.rawAddColumns(sData)

            if self.opts.addTimes:
                data.addTimes(time=self.opts.time,
                               times=sData.data[self.opts.time],
                               interpolate=self.opts.interpolateNewTime)
            for n in sData.names():
                if n!=self.opts.time:
                    d=data.resample(sData,
                                    n,
                                    time=self.opts.time,
                                    extendData=self.opts.extendData,
                                    noInterpolation=not self.opts.newDataInterpolate)
                    data.append(addition+" "+n,
                                d,
                                allowDuplicates=True)

        self.joinedAddColumns(data)

        if len(sources)>1:
            self.printColumns("written data",data)

        if self.opts.writeExcel:
            data.getData().to_excel(dest)
        else:
            data.writeCSV(dest,
                          delimiter=self.opts.delimiter)

# Should work with Python3 and Python2
