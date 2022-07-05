#  ICE Revision: $Id$
"""
Class that implements pyFoamDecompose
"""

from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator
from PyFoam.Error import error
from PyFoam.Basics.Utilities import writeDictionaryHeader,rmtree
from PyFoam.Execution.UtilityRunner import UtilityRunner
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.RegionCases import RegionCases
from PyFoam.RunDictionary.ParsedParameterFile import FoamStringParser
from PyFoam.FoamInformation import oldAppConvention as oldApp
from PyFoam.FoamInformation import foamVersion
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from .CommonMultiRegion import CommonMultiRegion
from .CommonStandardOutput import CommonStandardOutput
from .CommonServer import CommonServer
from .CommonVCSCommit import CommonVCSCommit

from PyFoam.ThirdParty.six import print_

from os import path,listdir,symlink
from glob import glob

import string

class Decomposer(PyFoamApplication,
                 CommonStandardOutput,
                 CommonServer,
                 CommonMultiRegion,
                 CommonVCSCommit):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Generates a decomposeParDict for a case and runs the decompose-Utility
on that case
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <case> <procnr>",
                                   interspersed=True,
                                   nr=2,
                                   **kwargs)

    decomposeChoices=["metis","simple","hierarchical","manual"]
    defaultMethod="metis"

    def addOptions(self):
        if foamVersion()>=(1,6):
            self.defaultMethod="scotch"
            self.decomposeChoices+=[self.defaultMethod]
            self.decomposeChoices+=["parMetis"]

        spec=OptionGroup(self.parser,
                         "Decomposition Specification",
                         "How the case should be decomposed")
        spec.add_option("--method",
                        type="choice",
                        default=self.defaultMethod,
                        dest="method",
                        action="store",
                        choices=self.decomposeChoices,
                        help="The method used for decomposing (Choices: "+", ".join(self.decomposeChoices)+") Default: %default")

        spec.add_option("--n",
                        dest="n",
                        action="store",
                        default=None,
                        help="Number of subdivisions in coordinate directions. A python list or tuple (for simple and hierarchical)")

        spec.add_option("--delta",
                        dest="delta",
                        action="store",
                        type="float",
                        default=None,
                        help="Cell skew factor (for simple and hierarchical)")

        spec.add_option("--order",
                        dest="order",
                        action="store",
                        default=None,
                        help="Order of decomposition (for hierarchical)")

        spec.add_option("--processorWeights",
                        dest="processorWeights",
                        action="store",
                        default=None,
                        help="The weights of the processors. A python list. Used for metis, scotch and parMetis")

        spec.add_option("--globalFaceZones",
                        dest="globalFaceZones",
                        action="store",
                        default=None,
                        help="""Global face zones. A string with a python list or an OpenFOAM-list of words. Used for the GGI interface. Ex: '["GGI_Z1","GGI_Z2"]' or '(GGI_Z1 GGI_Z2)'""")

        spec.add_option("--dataFile",
                        dest="dataFile",
                        action="store",
                        default=None,
                        help="File with the allocations. (for manual)")

        spec.add_option("--template-dict",
                        dest="templateDict",
                        action="store",
                        default=None,
                        help="File with 'template' dictionary. The utility uses this as default values and overwrites everything specified (can be used for 'complex' parameters)")


        self.parser.add_option_group(spec)

        behave=OptionGroup(self.parser,
                           "Decomposition behaviour",
                           "How the program should behave during decomposition")
        behave.add_option("--test",
                          dest="test",
                          action="store_true",
                          default=False,
                          help="Just print the resulting dictionary")

        behave.add_option("--clear",
                          dest="clear",
                          action="store_true",
                          default=False,
                          help="Clear the case of previous processor directories")

        behave.add_option("--no-decompose",
                          dest="doDecompose",
                          action="store_false",
                          default=True,
                          help="Don't run the decomposer (only writes the dictionary")

        behave.add_option("--do-function-objects",
                          dest="doFunctionObjects",
                          action="store_true",
                          default=False,
                          help="Allow the execution of function objects (default behaviour is switching them off)")

        behave.add_option("--decomposer",
                               dest="decomposer",
                               action="store",
                               default="decomposePar",
                               help="The decompose Utility that should be used")
        self.parser.add_option_group(behave)

        work=OptionGroup(self.parser,
                           "Additional work",
                           "What else should be done in addition to decomposing")
        work.add_option("--constant-link",
                        dest="doConstantLinks",
                        action="store_true",
                        default=False,
                        help="Add links to the contents of the constant directory to the constant directories of the processor-directories")
        self.parser.add_option_group(work)

        CommonMultiRegion.addOptions(self)
        CommonStandardOutput.addOptions(self)
        CommonServer.addOptions(self,False)
        CommonVCSCommit.addOptions(self)

    def run(self):
        decomposeParWithRegion=(foamVersion()>=(1,6))

        if self.opts.keeppseudo and (not self.opts.regions and self.opts.region==None):
            warning("Option --keep-pseudocases only makes sense for multi-region-cases")

        if decomposeParWithRegion and self.opts.keeppseudo:
            warning("Option --keep-pseudocases doesn't make sense since OpenFOAM 1.6 because decomposePar supports regions")

        nr=int(self.parser.getArgs()[1])
        if nr<2:
            error("Number of processors",nr,"too small (at least 2)")

        case=path.abspath(self.parser.getArgs()[0])
        method=self.opts.method

        if self.opts.templateDict:
            result=ParsedParameterFile(self.opts.templateDict).content
        else:
            result={}
        result["numberOfSubdomains"]=nr
        result["method"]=method

        coeff={}
        result[method+"Coeffs"]=coeff

        if self.opts.globalFaceZones!=None:
            try:
                fZones=eval(self.opts.globalFaceZones)
            except SyntaxError:
                fZones=FoamStringParser(
                    self.opts.globalFaceZones,
                    listDict=True
                ).data

            result["globalFaceZones"]=fZones

        if method in ["metis","scotch","parMetis"]:
            if self.opts.processorWeights!=None:
                weigh=eval(self.opts.processorWeights)
                if nr!=len(weigh):
                    error("Number of processors",nr,"and length of",weigh,"differ")
                coeff["processorWeights"]=weigh
        elif method=="manual":
            if self.opts.dataFile==None:
                error("Missing required option dataFile")
            else:
                coeff["dataFile"]="\""+self.opts.dataFile+"\""
        elif method=="simple" or method=="hierarchical":
            if self.opts.n==None or self.opts.delta==None:
                error("Missing required option n or delta")
            n=eval(self.opts.n)
            if len(n)!=3:
                error("Needs to be three elements, not",n)
            if nr!=n[0]*n[1]*n[2]:
                error("Subdomains",n,"inconsistent with processor number",nr)
            coeff["n"]="(%d %d %d)" % (n[0],n[1],n[2])

            coeff["delta"]=float(self.opts.delta)
            if method=="hierarchical":
                if self.opts.order==None:
                    error("Missing reuired option order")
                if len(self.opts.order)!=3:
                    error("Order needs to be three characters")
                coeff["order"]=self.opts.order
        else:
            error("Method",method,"not yet implementes")

        gen=FoamFileGenerator(result)

        if self.opts.test:
            print_(str(gen))
            return -1
        else:
            f=open(path.join(case,"system","decomposeParDict"),"w")
            writeDictionaryHeader(f)
            f.write(str(gen))
            f.close()

        if self.opts.clear:
            print_("Clearing processors")
            for p in glob(path.join(case,"processor*")):
                print_("Removing",p)
                rmtree(p,ignore_errors=True)

        self.checkAndCommit(SolutionDirectory(case,archive=None))

        if self.opts.doDecompose:
            if self.opts.region:
                regionNames=self.opts.region[:]
                while True:
                    try:
                        i=regionNames.index("region0")
                        regionNames[i]=None
                    except ValueError:
                        break
            else:
                regionNames=[None]

            regions=None

            sol=SolutionDirectory(case)
            if not decomposeParWithRegion:
                if self.opts.regions or self.opts.region!=None:
                    print_("Building Pseudocases")
                    regions=RegionCases(sol,clean=True,processorDirs=False)

            if self.opts.regions:
                regionNames=sol.getRegions(defaultRegion=True)

            for theRegion in regionNames:
                theCase=path.normpath(case)
                if theRegion!=None and not decomposeParWithRegion:
                    theCase+="."+theRegion

                if oldApp():
                    argv=[self.opts.decomposer,".",theCase]
                else:
                    argv=[self.opts.decomposer,"-case",theCase]
                    if foamVersion()>=(2,0) and not self.opts.doFunctionObjects:
                        argv+=["-noFunctionObjects"]
                    if theRegion!=None and decomposeParWithRegion:
                        argv+=["-region",theRegion]

                        f=open(path.join(case,"system",theRegion,"decomposeParDict"),"w")
                        writeDictionaryHeader(f)
                        f.write(str(gen))
                        f.close()

                self.setLogname(default="Decomposer",useApplication=False)

                run=UtilityRunner(argv=argv,
                                  silent=self.opts.progress or self.opts.silent,
                                  logname=self.opts.logname,
                                  compressLog=self.opts.compress,
                                  server=self.opts.server,
                                  noLog=self.opts.noLog,
                                  logTail=self.opts.logTail,
                                  echoCommandLine=self.opts.echoCommandPrefix,
                                  jobId=self.opts.jobId)
                run.start()

                if theRegion!=None and not decomposeParWithRegion:
                    print_("Syncing into master case")
                    regions.resync(theRegion)

            if regions!=None and not decomposeParWithRegion:
                if not self.opts.keeppseudo:
                    print_("Removing pseudo-regions")
                    regions.cleanAll()
                else:
                    for r in sol.getRegions():
                        if r not in regionNames:
                            regions.clean(r)

            if self.opts.doConstantLinks:
                print_("Adding symlinks in the constant directories")
                constPath=path.join(case,"constant")
                for f in listdir(constPath):
                    srcExpr=path.join(path.pardir,path.pardir,"constant",f)
                    for p in range(nr):
                        dest=path.join(case,"processor%d"%p,"constant",f)
                        if not path.exists(dest):
                            symlink(srcExpr,dest)

            self.addToCaseLog(case)

# Should work with Python3 and Python2
