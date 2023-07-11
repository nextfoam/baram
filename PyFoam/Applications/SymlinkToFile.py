"""
Application-class that implements pyFoamSymlinkToFile.py
"""

from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.Utilities import copytree,remove

from os import path,rename

class SymlinkToFile(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""Takes a list of files. If they are symlinks
then replace them with the file/directory they are pointing too.

Used to convert single files after using 'pyFoamCloneCase.py' ii
--symlink-mode
        """
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <file1> ...",
                                   changeVersion=False,
                                   interspersed=True,
                                   exactNr=False,
                                   nr=1,
                                   **kwargs)

    def addOptions(self):
        behave=OptionGroup(self.parser,
                           "Behaviour")
        self.parser.add_option_group(behave)
        behave.add_option("--follow-symlinks",
                          action="store_true",
                          dest="followSymlinks",
                          default=False,
                          help="Follow symlinks instead of just copying them")

    def run(self):
        files=self.parser.getArgs()

        for f in files:
            if not path.exists(f):
                self.error("File",f,"does not exists")
            if not path.islink(f):
                self.warning("File",f,"is not a symbolic link")
                continue
            real=path.realpath(f)
            while path.islink(real) and self.opts.followSymlinks:
                real=path.realpath(real)
            bakName=f+".backupfileForSymlink"
            copytree(real,bakName)
            remove(f)
            rename(bakName,f)

# Should work with Python3 and Python2
