#  ICE Revision: $Id$
"""
Class that implements pyFoamPVLoadState
"""

from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.Paraview.ServermanagerWrapper import ServermanagerWrapper as SM
from PyFoam.Paraview.StateFile import StateFile

from os import path,unlink,system

from PyFoam import configuration as config

class PVLoadState(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Starts paraview with an OpenFOAM-case and a predefined
paraview-State-File modifieing the state-File in such a way that it is
usable with the case

The state-file can be generated using a different case (the script
adjusts it before using) but the original case has to have a similar
structure to the current one. Also exactly one PV3Reader has to be
used in the state-file (this requirement is fullfilled if the
StateFile was generated using paraFoam)
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <case>",
                                   interspersed=True,
                                   nr=1,
                                   **kwargs)

    def addOptions(self):
        paraview=OptionGroup(self.parser,
                           "Paraview specifications",
                           "Options concerning paraview")
        paraview.add_option("--state-file",
                            dest="state",
                            default=None,
                            help="The pvsm-file that should be used. If none is specified the file 'default.pvsm' in the case-directory is used")

        paraview.add_option("--paraview-command",
                            dest="paraview",
                            default=config().get("Paths","paraview"),
                            help="The paraview-version that should be called. Default: %default (set in the configuration 'Paths'/'paraview')")
        decoChoices=["keep","decomposed","reconstructed","auto"]
        paraview.add_option("--decompose-mode",
                            dest="decomposeMode",
                            type="choice",
                            default="auto",
                            choices=decoChoices,
                            help="Whether the decomposed or the reconstructed data should be used. Possible values are"+", ".join(decoChoices)+" with default value %default. 'auto' means that the data set where more time-steps are present is used. 'keep' doesn't change the mode in the state-file. Default: %default")

        self.parser.add_option_group(paraview)

    def run(self):
        case=path.abspath(self.parser.getArgs()[0])
        short=path.basename(case)

        if self.opts.state==None:
            self.opts.state=path.join(case,"default.pvsm")

        if not path.exists(self.opts.state):
            self.error("The state file",self.opts.state,"does not exist")

        sol=SolutionDirectory(case,paraviewLink=False,archive=None)

        dataFile=path.join(case,short+".OpenFOAM")

        createdDataFile=False
        if not path.exists(dataFile):
            createdDataFile=True
            f=open(dataFile,"w")
            f.close()

        sf=StateFile(self.opts.state)
        sf.setCase(dataFile)

        decoResult=None
        if self.opts.decomposeMode=="keep":
            pass
        elif self.opts.decomposeMode=="decomposed":
            decoResult=sf.setDecomposed(True)
        elif self.opts.decomposeMode=="reconstructed":
            decoResult=sf.setDecomposed(False)
        elif self.opts.decomposeMode=="auto":
            nrTimes=len(sol.getTimes())
            nrParTimes=len(sol.getParallelTimes())
            self.warning("Decomposed timesteps: {}. Reconstructed timesteps: {}".format(nrParTimes,nrTimes))
            if nrTimes>nrParTimes:
                decoResult=sf.setDecomposed(False)
            else:
                decoResult=sf.setDecomposed(True)
        else:
            self.error("Setting decompose mode",self.opts.decomposeMode,"is not implemented")
        if decoResult:
            self.warning("Setting decomposed type to",self.opts.decomposeMode,":",decoResult)

        newState=sf.writeTemp()

        system(self.opts.paraview+" --state="+newState)

        if createdDataFile:
            self.warning("Removing pseudo-data-file",dataFile)
            unlink(dataFile)
