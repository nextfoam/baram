#  ICE Revision: $Id$
"""Encapsulates all necessary things for a cluster-job, like setting
up, running, restarting"""

import os,sys,subprocess
from os import path,unlink
from threading import Thread,Lock,Timer

from PyFoam.Applications.Decomposer import Decomposer
from PyFoam.Applications.Runner import Runner
from PyFoam.Applications.SteadyRunner import SteadyRunner
from PyFoam.Applications.CloneCase import CloneCase
from PyFoam.Applications.FromTemplate import FromTemplate
from PyFoam.Applications.PrepareCase import PrepareCase
from PyFoam.Applications.RunParameterVariation import RunParameterVariation

from PyFoam.FoamInformation import changeFoamVersion
from PyFoam.FoamInformation import foamVersion as getFoamVersion
from PyFoam.Error import error,warning
from PyFoam import configuration as config
from PyFoam.FoamInformation import oldAppConvention as oldApp
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from PyFoam.ThirdParty.six import print_,iteritems

def checkForMessageFromAbove(job):
    if not job.listenToTimer:
        return

    if path.exists(job.stopFile()):
        job.stopJob()
        return

    if path.exists(job.checkpointFile()):
        job.writeCheckpoint()

    job.timer=Timer(1.,checkForMessageFromAbove,args=[job])
    job.timer.start()


class ClusterJob(object):
    """ All Cluster-jobs are to be derived from this base-class

    The actual jobs are implemented by overriding methods

    There is a number of variables in this class that are used to
    'communicate' information between the various stages"""

    def __init__(self,
                 basename,
                 arrayJob=False,
                 hardRestart=False,
                 autoParallel=True,
                 doAutoReconstruct=None,
                 foamVersion=None,
                 compileOption=None,
                 useFoamMPI=False,
                 multiRegion=False,
                 parameters={},
                 isDecomposed=False):
        """Initializes the Job
        :param basename: Basis name of the job
        :param arrayJob: this job is a parameter variation. The tasks
        are identified by their task-id
        :param hardRestart: treat the job as restarted
        :param autoParallel: Parallelization is handled by the base-class
        :param doAutoReconstruct: Automatically reconstruct the case if
        autoParalellel is set. If the value is None then it is looked up from
        the configuration
        :param foamVersion: The foam-Version that is to be used
        :param compileOption: Forces compile-option (usually 'Opt' or 'Debug')
        :param useFoamMPI: Use the OpenMPI supplied with OpenFOAM
        :param multiRegion: This job consists of multiple regions
        :param parameters: Dictionary with parameters that are being passed to the Runner
        :param isDecomposed: Assume that the job is already decomposed"""

        #        print_(os.environ)

        if not "JOB_ID" in os.environ:
            error("Not an SGE-job. Environment variable JOB_ID is missing")
        self.jobID=int(os.environ["JOB_ID"])
        self.jobName=os.environ["JOB_NAME"]

        self.basename=path.join(path.abspath(path.curdir),basename)

        sgeRestarted=False
        if "RESTARTED" in os.environ:
            sgeRestarted=(int(os.environ["RESTARTED"])!=0)

        if sgeRestarted or hardRestart:
            self.restarted=True
        else:
            self.restarted=False

        if foamVersion==None:
            foamVersion=config().get("OpenFOAM","Version")

        changeFoamVersion(foamVersion,compileOption=compileOption)

        if not "WM_PROJECT_VERSION" in os.environ:
            error("No OpenFOAM-Version seems to be configured. Set the foamVersion-parameter")

        self.autoParallel=autoParallel

        self.doAutoReconstruct=doAutoReconstruct
        if self.doAutoReconstruct==None:
            self.doAutoReconstruct=config().getboolean("ClusterJob","doAutoReconstruct")

        self.multiRegion=multiRegion

        self.parameters=parameters

        self.hostfile=None
        self.nproc=1

        if "NSLOTS" in os.environ:
            self.nproc=int(os.environ["NSLOTS"])
            self.message("Running on",self.nproc,"CPUs")
            if self.nproc>1:
                # self.hostfile=os.environ["PE_HOSTFILE"]
                self.hostfile=path.join(os.environ["TMP"],"machines")
                if config().getboolean("ClusterJob","useMachineFile"):
                    self.message("Using the machinefile",self.hostfile)
                    self.message("Contents of the machinefile:",open(self.hostfile).readlines())
                else:
                    self.message("No machinefile used because switched off with 'useMachineFile'")

        self.ordinaryEnd=True
        self.listenToTimer=False

        self.taskID=None
        self.arrayJob=arrayJob

        if self.arrayJob:
            self.taskID=int(os.environ["SGE_TASK_ID"])

        if not useFoamMPI and not foamVersion in eval(config().get("ClusterJob","useFoamMPI",default='[]')):
        ## prepend special paths for the cluster
            self.message("Adding Cluster-specific paths")
            os.environ["PATH"]=config().get("ClusterJob","path")+":"+os.environ["PATH"]
            os.environ["LD_LIBRARY_PATH"]=config().get("ClusterJob","ldpath")+":"+os.environ["LD_LIBRARY_PATH"]

        self.isDecomposed=isDecomposed

    def fullJobId(self):
        """Return a string with the full job-ID"""
        result=str(self.jobID)
        if self.arrayJob:
            result+=":"+str(self.taskID)
        return result

    def message(self,*txt):
        print_("=== CLUSTERJOB: ",end="")
        for t in txt:
            print_(t,end=" ")
        print_(" ===")
        sys.stdout.flush()

    def setState(self,txt):
        self.message("Setting Job state to",txt)
        fName=path.join(self.casedir(),"ClusterJobState")
        f=open(fName,"w")
        f.write(txt+"\n")
        f.close()

    def jobFile(self):
        """The file with the job information"""
        jobfile="%s.%d" % (self.jobName,self.jobID)
        if self.arrayJob:
            jobfile+=".%d" % self.taskID
        jobfile+=".pyFoam.clusterjob"
        jobfile=path.join(path.dirname(self.basename),jobfile)

        return jobfile

    def checkpointFile(self):
        """The file that makes the job write a checkpoint"""
        return self.jobFile()+".checkpoint"

    def stopFile(self):
        """The file that makes the job write a checkpoint and end"""
        return self.jobFile()+".stop"

    def doIt(self):
        """The central logic. Runs the job, sets it up etc"""

        f=open(self.jobFile(),"w")
        f.write(path.basename(self.basename)+"\n")
        f.close()

        self.message()
        self.message("Running on directory",self.casename())
        self.message()
        self.setState("Starting up")

        if self.arrayJob:
            for k,v in list(self.taskParameters(self.taskID).items()):
                self.parameters[k]=v

        self.parameters.update(self.additionalParameters())

        self.message("Parameters:",self.parameters)
        if not self.restarted:
            self.setState("Setting up")
            self.setup(self.parameters)
            if self.autoParallel and self.nproc>1 and not self.isDecomposed:
                self.setState("Decomposing")
                self.autoDecompose()

            self.isDecomposed=True

            self.setState("Setting up 2")
            self.postDecomposeSetup(self.parameters)
        else:
            self.setState("Restarting")

        self.isDecomposed=True

        self.setState("Running")
        self.listenToTimer=True
        self.timer=Timer(1.,checkForMessageFromAbove,args=[self])
        self.timer.start()

        self.run(self.parameters)
        self.listenToTimer=False

        if path.exists(self.jobFile()):
            unlink(self.jobFile())

        if self.ordinaryEnd:
            self.setState("Post Running")
            self.preReconstructCleanup(self.parameters)

            if self.autoParallel and self.nproc>1:
                self.setState("Reconstructing")
                self.autoReconstruct()

            if self.nproc>0:
                self.additionalReconstruct(self.parameters)

            self.setState("Cleaning")
            self.cleanup(self.parameters)
            self.setState("Finished")
        else:
            self.setState("Suspended")

        if path.exists(self.stopFile()):
            unlink(self.stopFile())
        if path.exists(self.checkpointFile()):
            unlink(self.checkpointFile())

    def casedir(self):
        """Returns the actual directory of the case
        To be overridden if appropriate"""
        if self.arrayJob:
            return "%s.%05d" % (self.basename,self.taskID)
        else:
            return self.basename

    def casename(self):
        """Returns just the name of the case"""
        return path.basename(self.casedir())

    def execute(self,cmd):
        """Execute a shell command in the case directory. No checking done
        :param cmd: the command as a string"""
        oldDir=os.getcwd()
        self.message("Changing directory to",self.casedir())
        os.chdir(self.casedir())
        self.message("Executing",cmd)
        try:
            retcode = subprocess.call(cmd,shell=True)
            if retcode < 0:
                self.message(cmd,"was terminated by signal", -retcode)
            else:
                self.message(cmd,"returned", retcode)
        except OSError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.message(cmd,"Execution failed:", e)

        self.message("Executiong of",cmd,"ended")
        self.message("Changing directory back to",oldDir)
        os.chdir(oldDir)

    def templateFile(self,fileName):
        """Looks for a template file and evaluates the template using
        the usual parameters
        :param fileName: the name of the file that will be
        constructed. The template file is the same plus the extension '.template'"""

        self.message("Building file",fileName,"from template with parameters",
                     self.parameters)

        argList=["--output-file=%s" % path.join(self.casedir(),fileName),
                 "--dump-used-values"
        ]

        tmpl=FromTemplate(args=argList,
                          parameters=self.parameters)

    def foamRun(self,application,
                args=[],
                foamArgs=[],
                steady=False,
                multiRegion=True,
                progress=False,
                compress=False,
                noLog=False):
        """Runs a foam utility on the case.
        If it is a parallel job and the grid has
        already been decomposed (and not yet reconstructed) it is run in
        parallel
        :param application: the Foam-Application that is to be run
        :param foamArgs: A list if with the additional arguments for the
        Foam-Application
        :param compress: Compress the log-file
        :param args: A list with additional arguments for the Runner-object
        :param steady: Use the steady-runner
        :param multiRegion: Run this on multiple regions (if None: I don't have an opinion on this)
        :param progress: Only output the time and nothing else
        :param noLog: Do not generate a logfile"""

        arglist=args[:]
        arglist+=["--job-id=%s" % self.fullJobId()]
        for k,v in iteritems(self.parameters):
            arglist+=["--parameter=%s:%s" % (str(k),str(v))]

        if self.isDecomposed and self.nproc>1:
            arglist+=["--procnr=%d" % self.nproc]
            if config().getboolean("ClusterJob","useMachineFile"):
                arglist+=["--machinefile=%s" % self.hostfile]

        arglist+=["--echo-command-prefix='=== Executing'"]

        if progress:
            arglist+=["--progress"]
        if noLog:
            arglist+=["--no-log"]
        if compress:
            arglist+=["--compress"]

        if self.multiRegion:
            if multiRegion:
                arglist+=["--all-regions"]
        elif multiRegion:
            warning("This is not a multi-region case, so trying to run stuff multi-region won't do any good")

        if self.restarted:
            arglist+=["--restart"]

        arglist+=[application]
        if oldApp():
            arglist+=[".",self.casename()]
        else:
            arglist+=["-case",self.casename()]

        arglist+=foamArgs

        self.message("Executing",arglist)

        if steady:
            self.message("Running Steady")
            runner=SteadyRunner(args=arglist)
        else:
            runner=Runner(args=arglist)

    def autoDecompose(self):
        """Automatically decomposes the grid with a metis-algorithm"""

        if path.isdir(path.join(self.casedir(),"processor0")):
            warning("A processor directory already exists. There might be a problem")

        defaultMethod="metis"

        if getFoamVersion()>=(1,6):
            defaultMethod="scotch"

        args=["--method="+defaultMethod,
              "--clear",
              self.casename(),
              self.nproc,
              "--job-id=%s" % self.fullJobId()]

        if self.multiRegion:
            args.append("--all-regions")

        deco=Decomposer(args=args)

    def autoReconstruct(self):
        """Default reconstruction of a parallel run"""

        if self.doAutoReconstruct:
            self.isDecomposed=False

            self.foamRun("reconstructPar",
                         args=["--logname=ReconstructPar"])
        else:
            self.message("No reconstruction (because asked to)")

    def setup(self,parameters):
        """Set up the job. Called in the beginning if the
        job has not been restarted

        Usual tasks include grid conversion/setup, mesh decomposition etc

        :param parameters: a dictionary with parameters"""

        pass

    def postDecomposeSetup(self,parameters):
        """Additional setup, to be executed when the grid is already decomposed

        Usually for tasks that can be done on a decomposed grid

        :param parameters: a dictionary with parameters"""

        pass

    def run(self,parameters):
        """Run the actual job. Usually the solver.
        :param parameters: a dictionary with parameters"""

        pass

    def preReconstructCleanup(self,parameters):
        """Additional cleanup, to be executed when the grid is still decomposed

        Usually for tasks that can be done on a decomposed grid

        :param parameters: a dictionary with parameters"""

        pass

    def cleanup(self,parameters):
        """Clean up after a job
        :param parameters: a dictionary with parameters"""

        pass

    def additionalReconstruct(self,parameters):
        """Additional reconstruction of parallel runs (Stuff that the
        OpenFOAM-reconstructPar doesn't do
        :param parameters: a dictionary with parameters"""

        pass

    def taskParameters(self,id):
        """Parameters for a specific task
        :param id: the id of the task
        :return: a dictionary with parameters for this task"""

        error("taskParameter not implemented. Not a parameterized job")

        return {}

    def additionalParameters(self):
        """Additional parameters
        :return: a dictionary with parameters for this task"""

        warning("Method 'additionalParameters' not implemented. Not a problem. Just saying")

        return {}

    def writeCheckpoint(self):
        if self.listenToTimer:
            f=open(path.join(self.basename,"write"),"w")
            f.write("Jetzt will ich's wissen")
            f.close()
            unlink(self.checkpointFile())
        else:
            warning("I'm not listening to your callbacks")

        self.timer=Timer(1.,checkForMessageFromAbove,args=[self])

    def stopJob(self):
        if self.listenToTimer:
            self.ordinaryEnd=False
            f=open(path.join(self.basename,"stop"),"w")
            f.write("Geh z'haus")
            f.close()
            unlink(self.stopFile())
        else:
            warning("I'm not listening to your callbacks")

class SolverJob(ClusterJob):
    """A Cluster-Job that executes a solver. It implements the run-function.
    If a template-case is specified, the case is copied"""

    def __init__(self,basename,solver,
                 template=None,
                 cloneParameters=[],
                 arrayJob=False,
                 hardRestart=False,
                 autoParallel=True,
                 doAutoReconstruct=None,
                 foamVersion=None,
                 compileOption=None,
                 useFoamMPI=False,
                 steady=False,
                 multiRegion=False,
                 parameters={},
                 progress=False,
                 solverArgs=[],
                 solverProgress=False,
                 solverNoLog=False,
                 solverLogCompress=False,
                 isDecomposed=False):
        """:param template: Name of the template-case. It is assumed that
        it resides in the same directory as the actual case
        :param cloneParameters: a list with additional parameters for the
        CloneCase-object that copies the template
        :param solverProgress: Only writes the current time of the solver"""

        ClusterJob.__init__(self,basename,
                            arrayJob=arrayJob,
                            hardRestart=hardRestart,
                            autoParallel=autoParallel,
                            doAutoReconstruct=doAutoReconstruct,
                            foamVersion=foamVersion,
                            compileOption=compileOption,
                            useFoamMPI=useFoamMPI,
                            multiRegion=multiRegion,
                            parameters=parameters,
                            isDecomposed=isDecomposed)
        self.solver=solver
        self.steady=steady
        if template!=None and not self.restarted:
            template=path.join(path.dirname(self.casedir()),template)
            if path.abspath(basename)==path.abspath(template):
                error("The basename",basename,"and the template",template,"are the same directory")
            if isDecomposed:
                cloneParameters+=["--parallel"]
            self.message("Cloning from template",template)
            clone=CloneCase(
                args=cloneParameters+[template,self.casedir(),"--follow-symlinks"])
        self.solverProgress=solverProgress
        self.solverNoLog=solverNoLog
        self.solverLogCompress=solverLogCompress
        self.solverArgs=solverArgs

    def run(self,parameters):
        self.foamRun(self.solver,
                     steady=self.steady,
                     foamArgs=self.solverArgs,
                     multiRegion=False,
                     progress=self.solverProgress,
                     noLog=self.solverNoLog,
                     compress=self.solverLogCompress)

class PrepareCaseJob(SolverJob):
    """Assumes that the case is prepared to be set up with
    =pyFoamPrepareCase.py= and automatically sets it up with
    this. Needs one parameterfile to be specified and then a list of
    name/value-pairs
    """

    def __init__(self,basename,solver,
                 parameterfile,
                 arguments,
                 parameters={},
                 noMeshCreate=False,
                 **kwargs):
        self.__parameterfile=parameterfile
        self.__noMeshCreate=noMeshCreate

        para={}
        if type(arguments)==list:
            if len(arguments) % 2 !=0:
                error("Length of arguments should be an even number. Is",len(arguments),
                      ":",arguments)

            # make all string arguments that could be boolean boolean values
            from PyFoam.Basics.DataStructures import BoolProxy

            for k,v in dict(zip(arguments[::2],arguments[1::2])).items():
                try:
                    try:
                        para[k]=BoolProxy(textual=v).val
                    except TypeError:
                        para[k]=int(v)
                except ValueError:
                    try:
                        para[k]=float(v)
                    except ValueError:
                        try:
                            para[k]=eval(v)
                        except (SyntaxError,NameError):
                            para[k]="'"+v+"'"
        elif type(arguments)==dict:
            para=arguments
        else:
            error("Type of arguments is ",type(arguments),"Should be 'dict' or 'list':",arguments)

        self.__parametervalues=para

        parameters.update(self.__parametervalues)

        print_("Parameter file",self.__parameterfile)
        print_("Parameter values",self.__parametervalues)

        SolverJob.__init__(self,basename,solver,
                           parameters=parameters,
                           **kwargs)

    def setup(self,parameters):
        parameterString=",".join(["'%s':%s"%i for i in parameters.items()])
        PrepareCase(args=[self.casedir(),
                          "--allow-exec",
                          "--parameter="+path.join(self.casedir(),self.__parameterfile),
                          "--number-of-processors=%d" % self.nproc,
                          "--values={"+parameterString+"}"]+
                          (["--no-mesh-create"] if self.__noMeshCreate else []))

class VariationCaseJob(SolverJob):
    """Assumes that the case is prepared to be set up with
    =pyFoamRunParameterVariation.py= and automatically sets it up with
    this. Needs one parameterfile and a variation-file
    """

    def __init__(self,basename,
                 parameterfile,
                 variationfile,
                 template=None,
                 **kwargs):
        self.__parameterfile=parameterfile
        self.__variationfile=variationfile

        print_("Parameter file",self.__parameterfile)
        print_("Variation file",self.__variationfile)

        data=RunParameterVariation(args=[template,
                                         path.join(template,self.__variationfile),
                                         "--parameter="+path.join(template,self.__parameterfile),
                                         "--list-variations"]).getData()
        taskID=int(os.environ["SGE_TASK_ID"])-1
        if "solver" in data["variations"][taskID]:
            solver=data["variations"][taskID]["solver"]
        else:
            solver=data["fixed"]["solver"]

        SolverJob.__init__(self,basename,solver,
                           arrayJob=True,
                           template=template,
                           **kwargs)

    def taskParameters(self,id):
        return {}

    def setup(self,parameters):
        RunParameterVariation(args=[self.casedir(),
                                    path.join(self.casedir(),self.__variationfile),
                                    "--allow-exec",
                                    "--parameter-file="+path.join(self.casedir(),self.__parameterfile),
                                    "--single-variation=%d" % (self.taskID-1),
                                    "--no-execute-solver",
                                    "--auto-create-database",
                                    "--no-database-write",
                                    "--inplace-execution"])

# Should work with Python3 and Python2
