"""
Application-class that implements pyFoamDumpRunDatabaseToCSV.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.RunDatabase import RunDatabase

from PyFoam.ThirdParty.six import print_

from os import path

class DumpRunDatabaseToCSV(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Dump the contents of a SQLite database that holds run information to
a CSV-file
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <database.db> <dump.csv>",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=2,
                                   exactNr=True,
                                   **kwargs)

    def addOptions(self):
        how=OptionGroup(self.parser,
                        "Behavior",
                        "How the application should behave")
        self.parser.add_option_group(how)

        how.add_option("--verbose",
                       action="store_true",
                       dest="verbose",
                       default=False,
                       help="Tell about the data dumped")
        how.add_option("--pandas-print",
                       action="store_true",
                       dest="pandas",
                       default=False,
                       help="Print the pandas-dataframe that is collected")
        how.add_option("--excel-file",
                       action="store_true",
                       dest="excel",
                       default=False,
                       help="Write to Excel-file instead of plain CSV. Onle works with the python-libraries pandas and xlwt")
        how.add_option("--no-write",
                       action="store_true",
                       dest="noWrite",
                       default=False,
                       help="Do not write the CSV-file (just do terminal-output)")
        how.add_option("--use-numpy-instead-of-pandas",
                       action="store_false",
                       dest="usePandasFormat",
                       default=True,
                       help="For internal passing of data use numpy instead of pandas")

        what=OptionGroup(self.parser,
                         "What",
                         "Which information should be dumped")
        self.parser.add_option_group(what)

        what.add_option("--selection",
                       action="append",
                       dest="selection",
                       default=[],
                       help="""Regular expression (more than one can be
                       specified) to select data with (all the basic
                       run-data will be dumped anyway)""")

        what.add_option("--disable-run-data",
                       action="append",
                       dest="disableRunData",
                       default=[],
                       help="""Regular expression (more than one can be
                       specified) to select fields from the standard run-data
                       which should be disabled (use with care)""")



    def run(self):
        source=self.parser.getArgs()[0]
        dest=self.parser.getArgs()[1]
        if self.opts.noWrite:
            dest=None

        db=RunDatabase(source,
                       verbose=self.opts.verbose)

        selections=[]
        if self.opts.selection:
            selections=self.opts.selection

        dump=db.dumpToCSV(dest,
                          selection=selections,
                          disableRunData=self.opts.disableRunData,
                          pandasFormat=self.opts.usePandasFormat,
                          excel=self.opts.excel)

        if self.opts.pandas:
            if dump is None:
                print_("No data. Seems that pandas is not installed")
            else:
                print_("Pandas data:\n",dump)

        self.setData({
             "database" : path.abspath(source),
             "dump"     : dump
        })

# Should work with Python3 and Python2
