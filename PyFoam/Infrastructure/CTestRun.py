#  ICE Revision: $Id$
"""A wrapper to run a solver as a CTest"""

import sys
import os
from os import path
import subprocess
import shutil
import traceback
import inspect

from PyFoam.ThirdParty.six.moves import cPickle as pickle

import time

from PyFoam.Applications.CloneCase import CloneCase
from PyFoam.Applications.Runner import Runner
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Applications.SamplePlot import SamplePlot
from PyFoam.Applications.TimelinePlot import TimelinePlot
from PyFoam.Applications.Decomposer import Decomposer
from PyFoam.Basics.Data2DStatistics import Data2DStatistics
from PyFoam.FoamInformation import shellExecutionPrefix

from PyFoam.ThirdParty.six import print_,PY3,iteritems

callbackMethods=[]

def isCallback(f):
    callbackMethods.append(f.__name__)
    return f

class CTestRun(object):
    """This class runs a solver on a test case, examines the results
    and fails if they don't live up the expectations"""

    def __init__(self):
        pass

    def __new__(cls,*args,**kwargs):
        obj=super(CTestRun,cls).__new__(cls,*args,**kwargs)

        obj.__parameters={}
        obj.__parametersClosedForWriting=False

        obj.setParameters(sizeClass="unknown",
                          parallel=False,
                          autoDecompose=True,
                          doReconstruct=True,
                          nrCpus=None,
                          originalCaseBasis=None)

        obj.__addToClone=[]

        called=[]
        obj.__recursiveInit(obj.__class__,called)
        obj.__setParameterAsUsed(["nrCpus","autoDecompose","doReconstruct"])

        obj.__parametersClosedForWriting=True

        return obj

    def __recursiveInit(self,theClass,called):
        """Automatically call the 'init'-method of the whole tree"""
        #        print_(theClass)
        for b in theClass.__bases__:
            if b not in [object,CTestRun]:
                self.__recursiveInit(b,called)

        # subclass overwrites superclasses
        if "init" in dir(theClass):
            # make sure this is only called once
            if PY3:
                toCall=theClass.init.__call__
            else:
                toCall=theClass.init.im_func
            if not toCall in called:
                theClass.init(self)
                called.append(toCall)
                #                print_("Calling init for",theClass)

    def addToClone(self,*args):
        for a in args:
            self.__addToClone.append(a)

    def setParameters(self,**kwargs):
        """Update the parameters with a set of keyword-arguments"""

        if self.__parametersClosedForWriting:
            self.warn("Tried to modify parameters after the initialization phase",
                      kwargs)

        caller=inspect.stack()[1]
        setter="Set by %s in %s line %d" % (caller[3],caller[1],caller[2])

        for k,v in iteritems(kwargs):
            self.__parameters[k]={"value":v,
                                  "setter":setter,
                                  "used":False}

    def parameterValues(self):
        vals={}

        for k,v in iteritems(self.__parameters):
            vals[k]=v["value"]

        return vals

    def __setParameterAsUsed(self,keys):
        for k in keys:
            if k in self.__parameters:
                self.__parameters[k]["used"]=True

    def __getitem__(self,key):
        """Get a parameter"""
        try:
            parameter=self.__parameters[key]
        except KeyError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'

            print_("Unknown parameter",key,"(Parameters:",list(self.__parameters.keys()),")")
            raise e

        parameter["used"]=True

        return parameter["value"]

    def shortTestName(self):
        return type(self).__name__

    def testName(self):
        """Return the full test name with which this test is identified"""
        result=self.shortTestName()+"_"+self["solver"]
        if self["parallel"]:
            result+="_parallel_"+str(self["nrCpus"])+"Cpus"
        else:
            result+="_serial"
        result+="_"+self["sizeClass"]
        return result

    timeoutDefinitions=[
        ("unknown",60),
        ("tiny",60),          # a minute
        ("small",300),        # 5 minutes
        ("medium",1800),      # half an hour
        ("big",7200),         # 2 hours
        ("huge",43200),       # 12 hours
        ("monster",172800),   # 2 days
        ("unlimited",2592000)  # 30 days
        ]

    def sizeClassString(self):
        return ", ".join(["%s = %ds"% t for t in CTestRun.timeoutDefinitions])

    def setTimeout(self,quiet=False):
        if self["sizeClass"]=="unknown":
            if not quiet:
                self.warn("The parameter 'sizeClass' has not been set yet. Assuming 'tiny'")

        self.toSmallTimeout=0
        self.proposedSizeClass="unknown"

        try:
            self.timeout=dict(CTestRun.timeoutDefinitions)[self["sizeClass"]]
            index=-1
            for i,v in enumerate(CTestRun.timeoutDefinitions):
                if v[0]==self["sizeClass"]:
                    index=i
                    break
            if index>2:
                self.proposedSizeClass,self.toSmallTimeout=CTestRun.timeoutDefinitions[index-2]
        except KeyError:
            self.fatalFail("sizeClass is specified as",self["sizeClass"],
                           ". Valid values are with their timeout values",
                           self.sizeClassString())
            self.timeout=dict(CTestRun.timeoutDefinitions["unknown"]) # just in case that we continue

    def __doInit(self,
                 solver,
                 originalCase,
                 minimumRunTime=None,
                 referenceData=None,
                 tailLength=50,
                 headLength=50,
                 **kwargs):
        """Initialzation method to be called before running the actual
        test (purpose of this method is to avoid cascaded of
        constructor-calls

        :param solver: name of the solver to test
        :param originalCase: location of the original case files (they
        will be copied)
        :param minimumRuntime: the solver has to run at least to this time
        to be considered "ran successful"
        :param referenceData: directory with data that is used for testing
        :param tailLength: output that many lines from the end of the solver output
        :param headLength: output that many lines from the beginning of the solver output
        """
        print_("Creating test",self.testName())

        self.__setParameterAsUsed(["solver","originalCase","minimumRunTime",
                                   "referenceData","tailLength","headLength"])

        self.__failed=False
        self.__failMessage=""
        self.__runInfo=None

        self.__tailLength=tailLength
        self.__headLength=headLength

        self.setTimeout()

        self.solver=self.which(solver)
        if not self.solver:
            self.fatalFail("Solver",solver,"not in PATH")
        print_("Using solver",self.solver)

        if self["originalCaseBasis"]:
            originalCase=path.join(self["originalCaseBasis"],originalCase)
            print_("Expanding original case path with",self["originalCaseBasis"])

        self.originalCase=path.expandvars(originalCase)
        if not path.exists(self.originalCase):
            self.fatalFail("Original case",self.originalCase,"does not exist")
        print_("Original case",self.originalCase)

        self.caseDir=path.join(self.workDir(),self.testName()+"_runDir")
        print_("Running case in",self.caseDir)
        if path.exists(self.caseDir):
            if self.removeOldCase:
                self.warn("Removing old case",self.caseDir)
                shutil.rmtree(self.caseDir)
            elif self.doClone:
                self.fatalFail(self.caseDir,"already existing")
            else:
                self.fail(self.caseDir,"already existing")

        if referenceData:
            self.referenceData=path.join(self.dataDir(),referenceData)
            if not path.exists(self.referenceData):
                self.fatalFail("Data directory",self.referenceData,"does not exist")
            print_("Using reference data from")
        else:
            self.referenceData=None
            print_("No reference data specified")

        if self.doReadRunInfo:
            print_("Attempting to read the runInfo-file")
            self.readRunInfo()

        self.minimumRunTime=minimumRunTime
        print_()

    def readRunInfo(self):
        """read the runInfo from a file"""
        pick=pickle.Unpickler(open(path.join(self.caseDir,"runInfo.pickle"),"rb"))
        self.__runInfo=pick.load()

    def writeRunInfo(self):
        """read the runInfo from a file"""
        pick=pickle.Pickler(open(path.join(self.caseDir,"runInfo.pickle"),"wb"))
        pick.dump(self.__runInfo)

    def wrapACallback(self,name):
        """Has to be a separate method because the loop in
        wrapCallbacks didn't work"""
        original=getattr(self,name)
        if PY3:
            original_callable=getattr(original,'__func__')
        else:
            original_callable=getattr(original,'im_func')
        def wrapped(*args,**kwargs):
            #            print_("Wrapping",name,args,kwargs,original_callable)
            return self.runAndCatchExceptions(original_callable,self,*args,**kwargs)
        setattr(self,name,wrapped)

    def wrapCallbacks(self):
        """Wrap the callback methods with a Python exception handler.
        This is not done here so that methoids that the child classes
        overwrote will be wrapped to"""

        # not yet working

        for m in callbackMethods:
            print_("Wrapping method",m)
            #            setattr(self,m,original)
            self.wrapACallback(m)

    def processOptions(self):
        """Select which phase of the test should be run"""

        from optparse import OptionParser,OptionGroup

        parser = OptionParser(usage="%prog: [options]")
        phases=OptionGroup(parser,
                           "Phase",
                           "Select which phases to run")
        parser.add_option_group(phases)
        phases.add_option("--no-clone",
                          action="store_false",
                          dest="doClone",
                          default=True,
                          help="Skip cloning phase")
        phases.add_option("--no-preparation",
                          action="store_false",
                          dest="doPreparation",
                          default=True,
                          help="Skip preparation phase")
        phases.add_option("--no-serial-pre-tests",
                          action="store_false",
                          dest="doSerialPreTests",
                          default=True,
                          help="Skip pre-run test phase")
        phases.add_option("--no-decompose",
                          action="store_false",
                          dest="doDecompose",
                          default=True,
                          help="Skip decomposition phase")
        phases.add_option("--no-parallel-preparation",
                          action="store_false",
                          dest="doParallelPreparation",
                          default=True,
                          help="Skip the parallel preparation phase")
        phases.add_option("--no-pre-tests",
                          action="store_false",
                          dest="doPreTests",
                          default=True,
                          help="Skip pre-run test phase")
        phases.add_option("--no-simulation",
                          action="store_false",
                          dest="doSimulation",
                          default=True,
                          help="Skip simulation phase")
        phases.add_option("--no-postprocessing",
                          action="store_false",
                          dest="doPostprocessing",
                          default=True,
                          help="Skip postprocessing phase")
        phases.add_option("--no-post-tests",
                          action="store_false",
                          dest="doPostTests",
                          default=True,
                          help="Skip post-run test phase")
        phases.add_option("--no-reconstruction",
                          action="store_false",
                          dest="doReconstruction",
                          default=True,
                          help="Skip reconstruction phase")
        phases.add_option("--no-serial-post-tests",
                          action="store_false",
                          dest="doSerialPostTests",
                          default=True,
                          help="Skip serial post-run test phase")
        phases.add_option("--jump-to-tests",
                          action="store_true",
                          dest="jumpToTests",
                          default=False,
                          help="Skip everything except the final tests")

        behave=OptionGroup(parser,
                           "Behaviour",
                           "Determine the behaviour")
        parser.add_option_group(behave)
        behave.add_option("--fatal-not-fatal",
                          action="store_true",
                          dest="fatalIsNotFatal",
                          default=False,
                          help="Continue running the tests although a fatal error occured")
        behave.add_option("--remove-old-case",
                          action="store_true",
                          dest="removeOldCase",
                          default=False,
                          help="Remove the case directory if it exists")

        info=OptionGroup(parser,
                         "Info",
                         "Information about the test (all these options print to the screen and stop the test before doing anything)")
        parser.add_option_group(info)
        info.add_option("--parameter-value",
                        action="store",
                        dest="parameterValue",
                        default=None,
                        help="Just print the value of a parameter. Nothing if the parameter does not exist")
        info.add_option("--dump-parameters",
                        action="store_true",
                        dest="dumpParameters",
                        default=False,
                        help="Dump all the parameter values")
        info.add_option("--verbose-dump-parameters",
                        action="store_true",
                        dest="verboseDumpParameters",
                        default=False,
                        help="Dump all the parameter values plus the information where they were set")
        data=OptionGroup(parser,
                         "Data",
                         "Reading and writing data that allows rerunning cases")
        parser.add_option_group(data)
        data.add_option("--read-run-info",
                          action="store_true",
                          dest="readRunInfo",
                          default=False,
                          help="Read the runInfo-File if it exists in the runDirectory (mostly used to test tests without running the solver)")
        data.add_option("--print-run-info",
                          action="store_true",
                          dest="printRunInfo",
                          default=False,
                          help="Print the runInfo when it becomes available")

        script=OptionGroup(parser,
                           "Script parameters",
                           "Information about the test (all these options print to the screen and stop the test before doing anything and can be used as input in scripts)")
        parser.add_option_group(script)
        script.add_option("--print-test-name",
                          action="store_true",
                          dest="printTestName",
                          default=False,
                          help="Print the test name under which this test will be known to the world")
        script.add_option("--timeout",
                        action="store_true",
                        dest="timeout",
                        default=False,
                        help="Print the timeout for this test")

        (options, args) = parser.parse_args()

        if options.parameterValue:
            try:
                print_(self[options.parameterValue])
                sys.exit(0)
            except KeyError:
                sys.exit(1)

        if options.printTestName:
            print_(self.testName())
            sys.exit(0)

        if options.timeout:
            self.setTimeout(quiet=True)
            print_(self.timeout)
            sys.exit(0)

        if options.dumpParameters or options.verboseDumpParameters:
            keys=list(self.__parameters.keys())
            keys.sort()
            maxLen=max([len(n) for n in keys])
            for k in keys:
                print_(k," "*(maxLen-len(k)),":",self[k])
                if options.verboseDumpParameters:
                    print_("   ",self.__parameters[k]["setter"])
                    print_()

            sys.exit(0)

        self.doReadRunInfo=options.readRunInfo
        self.doPrintRunInfo=options.printRunInfo

        self.doClone=options.doClone
        self.doPreparation=options.doPreparation
        self.doSerialPreTests=options.doSerialPreTests
        self.doDecompose=options.doDecompose
        self.doParallelPreparation=options.doParallelPreparation
        self.doPreTests=options.doPreTests
        self.doSimulation=options.doSimulation
        self.doPostprocessing=options.doPostprocessing
        self.doPostTests=options.doPostTests
        self.doReconstruction=options.doReconstruction
        self.doSerialPostTests=options.doSerialPostTests

        if options.jumpToTests:
            self.doClone=False
            self.doPreparation=False
            self.doSerialPreTests=False
            self.doDecompose=False
            self.doParallelPreparation=False
            self.doPreTests=False
            self.doSimulation=False
            self.doPostprocessing=False

        self.fatalIsNotFatal=options.fatalIsNotFatal
        self.removeOldCase=options.removeOldCase

    def run(self):
        """Run the actual test"""

        startTime=time.time()

        self.processOptions()

        self.__doInit(**self.parameterValues())

        self.wrapCallbacks()

        self.__runParallel=False

        if self.doClone:
            self.status("Cloning case")

            clone=CloneCase([self.originalCase,self.caseDir]+
                            ["--add="+a for a in self.__addToClone])
        else:
            self.status("Skipping cloning")

        if self.doPreparation:
            if self.referenceData:
                if path.exists(path.join(self.referenceData,"copyToCase")):
                    self.status("Copying reference data")
                    self.cloneData(path.join(self.referenceData,"copyToCase"),
                                   self.caseDir)
                else:
                    self.status("No reference data - No 'copyToCase' in",self.referenceData)

                if path.exists(path.join(self.referenceData,"additionalFunctionObjects")):
                    self.status("Adding function objects")
                    self.addFunctionObjects(path.join(self.referenceData,"additionalFunctionObjects"))
                else:
                    self.status("No additional function objects - No 'additionalFunctionObjects' in",self.referenceData)

            self.status("Preparing mesh")
            self.meshPrepare()

            self.status("Preparing case")
            self.casePrepare()
        else:
            self.status("Skipping case preparation")

        if self.doSerialPreTests:
            self.status("Running serial pre-run tests")
            self.runTests("serialPreRunTest",warnSerial=True)
        else:
            self.status("Skipping the serial pre-tests")

        if self["parallel"]:
            if self.doDecompose:
                self.status("Decomposing the case")
                if self["autoDecompose"]:
                    self.autoDecompose()
                else:
                    self.decompose()
            else:
                self.status("Skipping the decomposition")

        self.__runParallel=self["parallel"]

        if self["parallel"]:
            if self.doParallelPreparation:
                self.status("Parallel preparation of the case")
                self.parallelPrepare()
            else:
                self.status("Skipping parallel preparation")

        if self.doPreTests:
            self.status("Running pre-run tests")
            self.runTests("preRunTest")
        else:
            self.status("Skipping the pre-tests")

        if self.doSimulation:
            self.status("Run solver")
            self.__runInfo=dict(self.execute(self.solver).getData())
            self.writeRunInfo()
            print_()
            if not self.runInfo()["OK"]:
                self.fail("Solver",self.solver,"ended with an error")
            else:
                try:
                    self.status("Solver ran until time",self.runInfo()["time"])
                except KeyError:
                    self.fail("No information how long the solver ran")
        else:
            self.status("Skipping running of the simulation")

        if self.doPrintRunInfo:
            print_()
            print_("runInfo used in further tests")
            import pprint

            printer=pprint.PrettyPrinter()
            printer.pprint(self.__runInfo)

        if self.doPostprocessing:
            self.status("Running postprocessing tools")
            self.postprocess()
        else:
            self.status("Skipping the postprocessing tools")

        if self.doPostTests:
            self.status("Running post-run tests")
            self.runTests("postRunTest")
        else:
            self.status("Skipping the post-run tests")

        self.__runParallel=False

        if self["parallel"]:
            if self.doReconstruction and self["doReconstruct"]:
                self.status("Reconstructing the case")
                if self["autoDecompose"]:
                    self.autoReconstruct()
                else:
                    self.reconstruct()
            else:
                self.status("Skipping the reconstruction")

        if self.doSerialPostTests:
            self.status("Running serial post-run tests")
            self.runTests("serialPostRunTest",warnSerial=True)
        else:
            self.status("Skipping the serial post-tests")

        if self.minimumRunTime:
            try:
                if float(self.runInfo()["time"])<self.minimumRunTime:
                    self.fail("Solver only ran to",self.runInfo()["time"],
                              "but should at least run to",self.minimumRunTime)
            except KeyError:
                self.fail("No information about run-time. Should have run to",
                          self.minimumRunTime)
            except TypeError:
                self.warn("Silently ignoring missing runInfo()")

        runTime=time.time()-startTime
        self.status("Total running time",runTime,"seconds")
        if runTime>self.timeout:
            self.warn("Running time",runTime,"bigger than assigned timeout",
                      self.timeout,". Consider other sizeclass than",
                      self["sizeClass"],"from sizeclasses",self.sizeClassString())
        elif runTime<self.toSmallTimeout:
            self.warn("Running time",runTime,"much smaller than assigned timeout",
                      self.timeout,". Consider other sizeclass than",
                      self["sizeClass"],"from sizeclasses",
                      self.sizeClassString(),"for instance",self.proposedSizeClass)
        return self.endTest()

    # make configuration-dependent
    def workDir(self):
        try:
            return os.environ["PYFOAM_CTESTRUN_WORKDIR"]
        except KeyError:
            if not hasattr(self,"__checkWorkDir"):
                self.__checkWorkDir=None
                self.warn("No environment variable PYFOAM_CTESTRUN_WORKDIR defined. Using current directory")
            return path.curdir

    # make configuration-dependent
    def dataDir(self):
        try:
            return os.environ["PYFOAM_CTESTRUN_DATADIR"]
        except KeyError:
            if not hasattr(self,"__checkDataDir"):
                self.__checkDataDir=None
                self.warn("No environment variable PYFOAM_CTESTRUN_DATADIR defined. Using current directory")
            return path.curdir

    def addFunctionObjects(self,templateFile):
        """Add entries for libraries and functionObjects to the controlDict
        (if they don't exist
        :param templateFile: file withe the data that should be added
        """
        tf=ParsedParameterFile(templateFile)
        cd=self.controlDict()
        touchedCD=False
        if "libs" in tf:
            touchedCD=True
            if not "libs" in cd:
                cd["libs"]=[]
            for l in tf["libs"]:
                if l in cd["libs"]:
                    self.warn(l,"already in 'libs' in the controlDict")
                else:
                    cd["libs"].append(l)
        if "functions" in tf:
            touchedCD=True
            if not "functions" in cd:
                cd["functions"]={}
            for k,v in iteritems(tf["functions"]):
                if k in cd["functions"]:
                    self.warn("Overwriting function object",k)
                cd["functions"][k]=v

        if touchedCD:
            cd.writeFile()

    def cloneData(self,src,dst):
        """Copy files recurivly into a case
        :param src: the source directory the files come fro
        :param dst: the destination directory the files go to"""

        for f in os.listdir(src):
            if f[0]=='.':
                self.warn("Ignoring dot-file",path.join(src,f))
                continue
            if path.isdir(path.join(src,f)):
                if not path.exists(path.join(dst,f)):
                    os.mkdir(path.join(dst,f))
                self.cloneData(path.join(src,f),path.join(dst,f))
            else:
                if path.exists(path.join(dst,f)):
                    self.warn("File",path.join(dst,f),"exists already in case. Overwritten")
                shutil.copy(path.join(src,f),path.join(dst,f))

    def runCommand(self,*args):
        """Run a command and let it directly write to the output"""
        p=subprocess.Popen(shellExecutionPrefix()+" ".join([str(a) for a in args]),
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

        print_(p.communicate()[0])
        sts=p.returncode

        if sts!=0:
            self.fail("Command"," ".join(args),"ended with status",sts)

    def shell(self,
              *args):
        """Run a command in the case directory and let it directly
        write to the output
        :param workingDirectory: change to this directory"""

        workingDirectory=None
        if not workingDirectory:
            workingDirectory=self.caseDir
        cmd=" ".join([str(a) for a in args])
        self.status("Executing",cmd,"in",workingDirectory)
        oldDir=os.getcwd()
        os.chdir(workingDirectory)

        p=subprocess.Popen(shellExecutionPrefix()+cmd,
                           shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

        self.status("Output of the command")
        self.line()
        print_(p.communicate()[0])
        self.line()

        sts=p.returncode

        if sts!=0:
            self.fail("Command",cmd,"ended with status",sts)
        else:
            self.status(cmd,"ran OK")

        os.chdir(oldDir)

    def execute(self,*args,**kwargs):
        """Execute the passed arguments on the case and check if
        everything went alright
        :param regexps: a list of regular expressions that the output should be scanned for"""

        try:
            regexps=kwargs["regexps"]
            if type(regexps)!=list:
                self.fail(regexps,"is not a list of strings")
                raise KeyError
        except KeyError:
            regexps=None

        if len(args)==1 and type(args[0])==str:
            args=[a.replace("%case%",self.solution().name) for a in args[0].split()]

        pyArgs=["--silent","--no-server-process"]
        if self.__runParallel:
            pyArgs+=["--procnr=%d" % self["nrCpus"]]

        argList=list(args)+\
                 ["-case",self.caseDir]
        self.status("Executing"," ".join(argList))
        if regexps:
            self.status("Also looking for the expressions",'"'+('" "'.join(regexps))+'"')
            pyArgs+=[r'--custom-regexp=%s' % r for r in regexps]

        runner=Runner(args=pyArgs+argList)
        self.status("Execution ended")

        if not runner["OK"]:
            self.fail("Running "," ".join(argList),"failed")
        else:
            self.status("Execution was OK")
        if "warnings" in runner:
            self.status(runner["warnings"],"during execution")
        print_()
        self.status("Output of"," ".join(argList),":")
        if runner["lines"]>(self.__tailLength+self.__headLength):
            self.status("The first",self.__headLength,"lines of the output.",
                        "Of a total of",runner["lines"])
            self.line()
            self.runCommand("head","-n",self.__headLength,runner["logfile"])
            self.line()
            print_()
            self.status("The last",self.__tailLength,"lines of the output.",
                        "Of a total of",runner["lines"])
            self.line()
            self.runCommand("tail","-n",self.__tailLength,runner["logfile"])
            self.line()
        else:
            self.line()
            self.runCommand("cat",runner["logfile"])
            self.line()

        self.status("End of output")
        print_()

        return runner

    def runInfo(self):
        """return the run information. If the solver was actually run"""
        if self.__runInfo==None:
            self.fatalFail("runInfo() called although solver was not yet run")
        else:
            return self.__runInfo

    def solution(self):
        """Access to a SolutionDirectory-object that represents the
        current solution"""
        if not hasattr(self,"_solution"):
            self._solution=SolutionDirectory(self.caseDir,
                                              archive=None)
        return self._solution

    def controlDict(self):
        """Access a representation of the controlDict of the case"""
        if not hasattr(self,"_controlDict"):
            self._controlDict=ParsedParameterFile(self.solution().controlDict())
        return self._controlDict

    def line(self):
        self.status("/\\"*int((78-len("TEST "+self.shortTestName()+" :"))/2))

    def status(self,*args):
        """print a status message about the test"""
        print_("TEST",self.shortTestName(),":",end="")
        for a in args:
            print_(a,end="")
        print_()

    def messageGeneral(self,prefix,say,*args):
        """Everything that passes through this method will be repeated
        in the end
        :param args: arbitrary number of arguments that build the
        fail-message
        :param prefix: General classification of the message
        """
        msg=prefix.upper()+": "+str(args[0])
        for a in args[1:]:
            msg+=" "+str(a)

        print_()
        print_(say,msg)
        print_()

        self.__failMessage+=msg+"\n"

    def failGeneral(self,prefix,*args):
        """:param args: arbitrary number of arguments that build the
        fail-message
        :param prefix: General classification of the failure
        """
        self.__failed=True
        self.messageGeneral(prefix,"Test failed:",*args)

    def warn(self,*args):
        """:param args: arbitrary number of arguments that build the
        warning-message"""
        self.messageGeneral("warning","",*args)

    def fail(self,*args):
        """To be called if the test failed but other tests should be tried
        :param args: arbitrary number of arguments that build the
        fail-message"""

        self.failGeneral("failure",*args)

    def fatalFail(self,*args):
        """:param args: arbitrary number of arguments that build the
        fail-message"""

        self.failGeneral("fatal failure",*args)
        if not self.fatalIsNotFatal:
            self.endTest()

    def endTest(self):
        unused=[]
        for k,v in iteritems(self.__parameters):
            if not v["used"]:
                unused.append(k)
        if len(unused)>0:
            self.warn("Unused parameters (possible typo):",unused)

        print_()
        if self.__failed:
            print_("Test failed.")
            print_()
            print_("Summary of failures")
            print_(self.__failMessage)
            print_()

            sys.exit(1)
        else:
            print_("Test successful")
            print_()
            if len(self.__failMessage)>0:
                print_("Summary of warnings")
                print_(self.__failMessage)
                print_()

            sys.exit(0)

    def which(self,command):
        """Like the regular which command - return the full path to an
        executable"""
        for d in os.environ["PATH"].split(os.pathsep):
            if path.exists(path.join(d,command)):
                return path.join(d,command)

        return None

    def runAndCatchExceptions(self,func,*args,**kwargs):
        """Run a callable and catch Python-exceptions if they occur
        :param func: The actual thing to be run"""
        try:
            func(*args,**kwargs)
            return True
        except SystemExit:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.fail("sys.exit() called somewhere while executing",
                      func.__name__,":",e)
            traceback.print_exc()
            raise e
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.fail("Python problem during execution of",
                      func.__name__,":",e)
            traceback.print_exc()
            return False

    def runTests(self,namePrefix,warnSerial=False):
        """Run all methods that fit a certain name prefix"""
        self.status("Looking for tests that fit the prefix",namePrefix)
        cnt=0
        for n in dir(self):
            if n.find(namePrefix)==0:
                meth=getattr(self,n)
                if not inspect.ismethod(meth):
                    self.fail("Found attribute",n,
                              "that fits the prefix",namePrefix,
                              "in test class but it is not a method")
                else:
                    self.status("Running the test",n)
                    if not self["parallel"] and warnSerial:
                        self.warn("This is a serial test. No need to have special serial tests like",n)
                    self.runAndCatchExceptions(meth)
                    cnt+=1
        if cnt>0:
            self.status(cnt,"tests with prefix",namePrefix,"run")
        else:
            self.status("No test fit the prefix",namePrefix)

    def generalTest(self,
                    testFunction,
                    args,
                    *message):
        if not testFunction(*args):
            self.fail(*message)

    def compareSamples(self,
                       data,
                       reference,
                       fields,
                       time=None,
                       line=None,
                       scaleData=1,
                       offsetData=0,
                       scaleX=1,
                       offsetX=0,
                       useReferenceForComparison=False):
        """Compare sample data and return the statistics
        :param data: the name of the data directory
        :param reference:the name of the directory with the reference data
        :param fields: list of the fields to compare
        :param time: the time to compare for. If empty the latest time is used"""
        timeOpt=["--latest-time"]
        if time:
            timeOpt=["--time="+str(time)]
        if line:
            timeOpt+=["--line=%s" % line]
        addOpt=[]
        if useReferenceForComparison:
            addOpt.append("--use-reference-for-comparison")

        sample=SamplePlot(args=[self.caseDir,
                                "--silent",
                                "--dir="+data,
                                "--reference-dir="+reference,
                                "--tolerant-reference-time",
                                "--compare",
                                "--index-tolerant-compare",
                                "--common-range-compare",
                                "--metrics",
                                "--scale-data=%f" % scaleData,
                                "--scale-x=%f" % scaleX,
                                "--offset-data=%f" % offsetData,
                                "--offset-x=%f" % offsetX
                            ]+
                          timeOpt+
                          addOpt+
                          ["--field="+f for f in fields])
        return Data2DStatistics(metrics=sample["metrics"],
                                compare=sample["compare"],
                                noStrings=True,
                                failureValue=0)

    def compareTimelines(self,
                       data,
                       reference,
                       fields):
        """Compare timeline data and return the statistics
        :param data: the name of the data directory
        :param reference:the name of the directory with the reference data
        :param fields: list of the fields to compare"""
        sample=TimelinePlot(args=[self.caseDir,
                                "--silent",
                                "--dir="+data,
                                "--reference-dir="+reference,
                                "--compare",
                                "--basic-mode=lines",
                                "--metrics"]+
                          ["--field="+f for f in fields])
        return Data2DStatistics(metrics=sample["metrics"],
                                compare=sample["compare"],
                                noStrings=True,
                                failureValue=0)


    def isNotEqual(self,value,target=0,tolerance=1e-10,message=""):
        self.generalTest(
            lambda x,y:abs(x-y)>tolerance,
            (value,target),
            message,"( value",value,"within tolerance",tolerance,
            "of target",target,")")

    def isEqual(self,value,target=0,tolerance=1e-10,message=""):
        self.generalTest(
            lambda x,y:abs(x-y)<tolerance,
            (value,target),
            message,"( value",value," not within tolerance",tolerance,
            "of target",target,")")

    def isBigger(self,value,threshold=0,message=""):
        self.generalTest(
            lambda x:x>threshold,
            (value),
            message,"( value",value," not bigger than",threshold)

    def isSmaller(self,value,threshold=0,message=""):
        self.generalTest(
            lambda x:x<threshold,
            (value),
            message,"( value",value," not smaller than",threshold)

    def preRunTestCheckMesh(self):
        """This test is always run. If this is not desirable it has to
        be overridden in a child-class"""
        self.execute("checkMesh")

    def autoDecompose(self):
        """Decomposition used if no callback is specified"""
        deco=Decomposer(args=[self.caseDir,
                              str(self["nrCpus"]),
                              "--all-regions"])

    def autoReconstruct(self):
        """Reconstruction used if no callback is specified"""
        self.execute("reconstructPar","-latestTime")

    @isCallback
    def meshPrepare(self):
        """Callback to prepare the mesh for the case. Default
        behaviour is to run blockMesh on the case"""
        result=self.execute("blockMesh")
        if not result["OK"]:
            self.fatalFail("blockMesh was not able to create a mesh")

    @isCallback
    def casePrepare(self):
        """Callback to prepare the case. Default behaviour is to do
        nothing"""
        pass

    @isCallback
    def parallelPrepare(self):
        """Callback to prepare the case in parallel (after it was decomposed).
        Default behaviour is to do nothing"""
        pass

    @isCallback
    def postprocess(self):
        """Callback to run after the solver has finished. Default
        behaviour is to do nothing"""
        pass

    @isCallback
    def decompose(self):
        """Callback to do the decomposition (if automatic is not sufficient)"""
        self.fatalFail("Manual decomposition specified but no callback for manual decomposition specified")

    @isCallback
    def reconstruct(self):
        """Callback to do the reconstruction (if automatic is not sufficient)"""
        self.warn("Manual decomposition specified, but no callback 'reconstruct' implemented. Using the automatic reconstruction")
        self.autoReconstruct()

# Should work with Python3 and Python2
