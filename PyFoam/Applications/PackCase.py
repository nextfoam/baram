"""
Application-class that implements pyFoamPackCase.py
"""

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from os import path
from optparse import OptionGroup

class PackCase(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Packs a case into a tar-file copying the system, constant and
0-directories.  Excludes all .svn-direcotries and all files ending
with ~. Symbolic links are replaced with the actual files
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <case>",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=1,
                                   **kwargs)

    def addOptions(self):
        what=OptionGroup(self.parser,
                         "What",
                         "Define what should be packed")
        self.parser.add_option_group(what)

        what.add_option("--last",
                        action="store_true",
                        dest="last",
                        default=False,
                        help="Also add the last time-step")
        what.add_option("--pyfoam",
                        action="store_true",
                        dest="pyfoam",
                        default=False,
                        help="Add all files starting with PyFoam to the tarfile")
        what.add_option("--chemkin",
                        action="store_true",
                        dest="chemkin",
                        default=False,
                        help="Also add the Chemkin-directory")
        what.add_option("--add",
                        action="append",
                        dest="additional",
                        default=[],
                        help="Add all files and directories in the case directory that fit a glob-pattern to the tar (can be used more than once)")
        what.add_option("--exclude",
                         action="append",
                         dest="exclude",
                         default=[],
                         help="Exclude all files and directories that fit this glob pattern from being added, no matter at level (can be used more than once)")
        what.add_option("--no-polyMesh",
                         action="store_true",
                         dest="noPloyMesh",
                         help="Exclude the polyMesh-directory")
        what.add_option("--parallel",
                        action="store_true",
                        dest="parallel",
                        default=False,
                        help="Store processor directories instead of serial")

        where=OptionGroup(self.parser,
                         "Where",
                         "Define where it should be packaged to")
        self.parser.add_option_group(where)
        where.add_option("--tarname",
                         action="store",
                         dest="tarname",
                         default=None,
                         help='Name of the tarfile. If unset the name of the case plus ".tgz" will be used')
        where.add_option("--base-name",
                         action="store",
                         dest="basename",
                         default=None,
                         help='Name of the case inside the tar-file. If not set the actual basename of the case is used')
        how=OptionGroup(self.parser,
                         "How",
                         "How should it be done")
        self.parser.add_option_group(how)
        how.add_option("--verbose",
                        action="store_true",
                        dest="verbose",
                        default=False,
                        help="Report every file that is added")

    def run(self):
        sName=self.parser.getArgs()[0]
        if sName[-1]==path.sep:
            sName=sName[:-1]

        if self.parser.getOptions().tarname!=None:
            dName=self.parser.getOptions().tarname
        else:
            if sName==path.curdir:
                dName=path.basename(path.abspath(sName))
            else:
                dName=sName
            dName+=".tgz"
        if self.parser.getOptions().pyfoam:
            self.parser.getOptions().additional.append("PyFoam*")

        sol=SolutionDirectory(sName,
                              archive=None,
                              parallel=self.parser.getOptions().parallel,
                              addLocalConfig=True,
                              paraviewLink=False)
        if not sol.isValid():
            self.error(sName,"does not look like real OpenFOAM-case because",sol.missingFiles(),"are missing or of the wrong type")

        if self.parser.getOptions().chemkin:
            sol.addToClone("chemkin")

        if self.opts.noPloyMesh:
            self.parser.getOptions().exclude.append("polyMesh")

        sol.packCase(dName,
                     last=self.parser.getOptions().last,
                     additional=self.parser.getOptions().additional,
                     exclude=self.parser.getOptions().exclude,
                     verbose=self.parser.getOptions().verbose,
                     base=self.parser.getOptions().basename)

# Should work with Python3 and Python2
