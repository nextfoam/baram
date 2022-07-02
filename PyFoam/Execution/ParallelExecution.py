#  ICE Revision: $Id$
"""Things that are needed for convenient parallel Execution"""

from PyFoam.Basics.Utilities import Utilities
from PyFoam.FoamInformation import foamMPI,oldAppConvention
from PyFoam.Error import error,warning,debug
from PyFoam import configuration as config

from os import path,environ,system

import subprocess

class LAMMachine(Utilities):
    """Wrapper class for starting an stopping a LAM-Machine"""
    def __init__(self,machines=None,nr=None):
        """:param machines: Name of the file with the machine information
        :param nr: Number of processes"""

        Utilities.__init__(self)

        self.stop()

        if machines=="":
            machines=None

        if machines==None and foamMPI()=="LAM":
            error("Machinefile must be specified for LAM")

        if machines==None and nr==None:
            error("Either machinefile or Nr of CPUs must be specified for MPI type",foamMPI())

        self.mFile=machines
        self.procNr=nr

        self.boot()
        if not self.machineOK():
            error("Error: LAM was not started")

    def machineOK(self):
        """Check whether the LAM machine was properly booted"""
        if self.running:
            if(foamMPI()=="LAM"):
                if self.cpuNr()<=0:
                    self.running=False

        return self.running

    def stop(self):
        """Stops a LAM-machine (if one is running)"""
        self.running=False
        if(foamMPI()=="LAM"):
            self.execute("lamhalt -v")

    def boot(self):
        """Boots a LAM-machine using the machine-file"""
        if foamMPI()=="LAM":
            warning("LAM is untested. Any Feedback most welcome")
            self.execute("lamboot -s -v "+self.mFile)
            self.running=True
        elif foamMPI().find("OPENMPI")>=0:
            self.running=True
        else:
            error(" Unknown or missing MPI-Implementation: "+foamMPI())

    def cpuNr(self):
        if(foamMPI()=="LAM"):
            if self.running:
                lines=self.execute("lamnodes")
                nr=0
                for l in lines:
                    tmp=l.split(':')
                    if len(tmp)>1:
                        nr+=int(tmp[1])
                return nr
            else:
                return -1
        elif foamMPI().find("OPENMPI")>=0:
            if self.mFile:
                f=open(self.mFile)
                l=[i.strip() for i in f.readlines()]
                f.close()
                nr=0
                for m in l:
                    tmp=m.split()
                    if len(tmp)==1:
                        nr+=1
                    elif len(tmp)==0:
                        pass
                    else:
                        error("Machinefile not valid (I think): more than one element in one line:"+str(tmp)+"\nPropably you wrote a line in the form 'node1 cpu=2', but I only understand 'node1\\nnode1'")

                if self.procNr==None:
                    return nr
                else:
                    return min(nr,self.procNr)

            elif self.procNr:
                return self.procNr
            else:
                error("Can't determine Nr of CPUs without machinefile")

    def buildMPIrun(self,argv,expandApplication=True):
        """Builds a list with a working mpirun command (for that MPI-Implementation)
        :param argv: the original arguments that are to be wrapped
        :param expandApplication: Expand the
        :return: list with the correct mpirun-command"""

        nr=str(self.cpuNr())
        mpirun=[config().get("MPI","run_"+foamMPI(),default="mpirun")]
        mpiRunPath=self.which(" ".join(mpirun))
        if not mpiRunPath:
            error("Could not find a path for",mpirun,
                  "Check configuration variable","run_"+foamMPI(),
                  "in section 'MPI'")
        mpirun+=eval(config().get("MPI","options_"+foamMPI()+"_pre",default="[]"))

        if(foamMPI()=="LAM"):
            mpirun+=["-np",nr]
        elif foamMPI().find("OPENMPI")>=0:
            nr=[]
            if "MPI_ARCH_PATH" in environ and config().getboolean("MPI","OpenMPI_add_prefix"):
                nr+=["--prefix",environ["MPI_ARCH_PATH"]]
            if self.procNr!=None:
                nr+=["--n",str(self.procNr)]
            machine=[]
            if self.mFile!=None:
                machine=["--machinefile",self.mFile]
                if config().getdebug("ParallelExecution"):
                    debug("Start of",self.mFile)
                    debug("\n"+open(self.mFile).read())
                    debug("End of",self.mFile)
            mpirun+=machine+nr
        else:
            error(" Unknown or missing MPI-Implementation for mpirun: "+foamMPI())

        mpirun+=eval(config().get("MPI","options_"+foamMPI()+"_post",default="[]"))

        progname=argv[0]
        if expandApplication:
            # old implementation: stat,progname=commands.getstatusoutput('which '+progname)
            progname=self.which(progname)
            if progname:
                progname=argv[0]
                warning("which can not find a match for",progname,". Hoping for the best")

        if oldAppConvention():
            mpirun+=[progname]+argv[1:3]+["-parallel"]+argv[3:]
        else:
            mpirun+=[progname]+argv[1:]+["-parallel"]

        if config().getdebug("ParallelExecution"):
            debug("MPI:",foamMPI())
            debug("Arguments:",mpirun)
            system("which mpirun")
            system("which rsh")
            debug("Environment",environ)
            for a in mpirun:
                if a in environ:
                    debug("Transfering variable",a,"with value",environ[a])

        return mpirun

    def writeMetis(self,sDir):
        """Write the parameter-File for a metis decomposition
        :param sDir: Solution directory
        :type sDir: PyFoam.RunDictionary.SolutionDirectory"""

        params="method metis;\n"

        self.writeDecomposition(sDir,params)

    def writeSimple(self,sDir,direction):
        """Write the parameter-File for a metis decomposition
        :param sDir: Solution directory
        :type sDir: PyFoam.RunDictionary.SolutionDirectory
        :param direction: direction in which to decompose (0=x, 1=y, 2=z)"""

        params ="method simple;\n"
        params+="\nsimpleCoeffs\n{\n\t n \t ("
        if direction==0:
            params+=str(self.cpuNr())+" "
        else:
            params+="1 "
        if direction==1:
            params+=str(self.cpuNr())+" "
        else:
            params+="1 "
        if direction==2:
            params+=str(self.cpuNr())
        else:
            params+="1"
        params+=");\n\t delta \t 0.001;\n}\n"

        self.writeDecomposition(sDir,params)

    def writeDecomposition(self,sDir,par):
        """Write parameter file for a decomposition
        :param par:Parameters specific for that kind of decomposition
        :type par:str
        :param sDir: Solution directory
        :type sDir: PyFoam.RunDictionary.SolutionDirectory"""

        f=open(path.join(sDir.systemDir(),"decomposeParDict"),"w")
        self.writeDictionaryHeader(f)
        f.write("// * * * * * * * * * //\n\n")
        f.write("numberOfSubdomains "+str(self.cpuNr())+";\n\n")
        f.write(par)
        f.write("\n\n// * * * * * * * * * //")
        f.close()

# Should work with Python3 and Python2
