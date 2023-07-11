"""
Class that implements the common functionality for the ChangeBoundary-utilities
"""
from optparse import OptionGroup
from os import path
from glob import glob

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from PyFoam.ThirdParty.six import print_

class CommonChangeBoundary(object):
    """ The class that defines options for ChangeBoundary-utilities
    """

    def addOptions(self):
        input=OptionGroup(self.parser,
                        "Input",
                        "Defines Whether processor directories should be handled")

        input.add_option("--region",
                       action="store",
                       dest="region",
                       default="",
                       help="Region to use. If unset the default mesh is used")
        input.add_option("--time-directory",
                         action="store",
                         default="constant",
                         dest="time",
                         help="Time to use. If unset the mesh in '%default' is used")

        self.parser.add_option_group(input)

        output=OptionGroup(self.parser,
                        "Output",
                        "How the changes are output")
        output.add_option("--test",
                          action="store_true",
                          default=False,
                          dest="test",
                          help="Only print the new boundary file")

        self.parser.add_option_group(output)

        grp=OptionGroup(self.parser,
                        "Processor",
                        "Defines Whether processor directories should be handled")

        grp.add_option("--no-processor",
                       action="store_false",
                       dest="doProcessors",
                       default=True,
                       help="Do not process processorX-directories even if they are found")
        grp.add_option("--no-single",
                       action="store_false",
                       dest="doSingle",
                       default=True,
                       help="Do not process the boundary files of the non-decomposed directories")

        self.parser.add_option_group(grp)

    def processBoundaryFiles(self,func,case):
        """
        :param func: the function that transforms the actual boundary file
        """
        changed=False
        if self.opts.doSingle:
            bFileName=path.join(".",case,self.opts.time,self.opts.region)
            changed=self.processABoundaryFile(func,
                                              bFileName)
            if not changed:
                self.warning(bFileName,"not changed")
        if self.opts.doProcessors:
            changedAll=True
            hasProc=False
            for p in glob(path.join(".",case,"processor*")):
                hasProc=True
                c=self.processABoundaryFile(func,
                                            path.join(p,self.opts.time,self.opts.region))
                changedAll=changedAll and c
                changed=changed or c
            if not changedAll and hasProc:
                self.warning("Not all processor directories in",case,
                             "correctly processed")
                changed=False
        if not changed:
            self.error("Problem processing boundary file(s) in",case)

    def processABoundaryFile(self,func,targetDir):
        """
        :param func: the function that transforms the actual boundary file
        """
        boundaryPath=path.join(targetDir,"polyMesh","boundary")
        try:
            boundary=ParsedParameterFile(boundaryPath,
                                         debug=False,
                                         boundaryDict=True,
                                         treatBinaryAsASCII=True)
        except IOError:
            self.warning("Problem opening boundary file",boundaryPath)
            return False

        bnd=boundary.content

        if type(bnd)!=list:
            self.warning("Problem with boundary file (not a list)")
            return False

        boundary.content=func(bnd,targetDir)

        if boundary.content:
            if self.opts.test:
                print_(boundary)
            else:
                boundary.writeFile()
                # self.addToCaseLog(boundaryPath)
            return True
        else:
            self.warning(boundaryPath,"unchanged")
            return False
