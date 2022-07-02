"""
Application-class that implements pyFoamAddCaseDataToDatabase.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.RunDatabase import RunDatabase

from os import path

from PyFoam.ThirdParty.six.moves import cPickle as pickle
from PyFoam.ThirdParty.six import print_

import sys

class AddCaseDataToDatabase(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Adds the content of a number of pickledData-files to a sqlite database
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <database.db> <pickleData1> ... <pickleData2>",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=2,
                                   exactNr=False,
                                   **kwargs)

    def addOptions(self):
        how=OptionGroup(self.parser,
                         "Behavior",
                         "How the application should behave")
        self.parser.add_option_group(how)

        how.add_option("--create",
                       action="store_true",
                       dest="create",
                       default=False,
                       help="Create a new database file. Fail if it already exists")
        how.add_option("--verbose",
                       action="store_true",
                       dest="verbose",
                       default=False,
                       help="Tell about the data added")

        how.add_option("--skip-missing",
                       action="store_true",
                       dest="skipMissing",
                       default=False,
                       help="Skip files that are missing or unreadable")
        how.add_option("--update",
                       action="store_true",
                       dest="update",
                       default=False,
                       help="Update the data if a run with the same unique id already exists in the database")


    def run(self):
        dest=self.parser.getArgs()[0]
        if path.exists(dest) and self.opts.create:
            self.error("database-file",dest,"exists already.")
        sources=self.parser.getArgs()[1:]

        db=RunDatabase(dest,
                       create=self.opts.create,
                       verbose=self.opts.verbose)

        for s in sources:
            if self.opts.verbose:
                print_("\nProcessing file",s)
            try:
                data=pickle.Unpickler(open(s,"rb")).load()
            except (IOError,pickle.UnpicklingError):
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                if self.opts.skipMissing:
                    self.warning("File",s,"missing")
                    continue
                else:
                    self.error("There was a problem reading file",s,
                               ":",e)
            try:
                db.add(data,
                       update_existing=self.opts.update)
            except KeyError as e:
                print("Data from file {} already in database: {}".format(s, e))
