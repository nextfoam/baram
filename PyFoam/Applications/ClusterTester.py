#  ICE Revision: $Id$
"""
Application class that implements pyFoamClusterTester
"""
import sys

if sys.version_info<(2,4):
    from os import system
else:
    import subprocess

import os,string
from os import mkdir,path
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam import configuration as config

from .CommonParallel import CommonParallel

from PyFoam.ThirdParty.six import print_

class ClusterTester(PyFoamApplication,
                    CommonParallel):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Is used to test Cluster-Scripts before they are submitted to the
cluster. It tries to resemble the environment the script will
find. Cluster in this context means the Sun Grid Engine
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <cluster-script> <script options>",
                                   changeVersion=False,
                                   nr=1,
                                   exactNr=False,
                                   interspersed=1,
                                   **kwargs)

    def addOptions(self):
        general=OptionGroup(self.parser,
                        "Cluster General",
                        "Stuff that is similar for all queueing implementations")
        general.add_option("--no-clear",
                           action="store_false",
                           default=True,
                           dest="clear",
                           help="Do not clear the Environment from OpenFOAM-specific variables")
        general.add_option("--restart",
                           action="store_true",
                           default=False,
                           dest="restart",
                           help="Treat the case as being restarted")
        self.parser.add_option_group(general)

        sge=OptionGroup(self.parser,
                        "SGE",
                        "Stuff that is specific to a SunGridEngine-environment")
        sge.add_option("--taskid",
                       type="int",
                       dest="taskid",
                       default=None,
                       help="The task-ID of a multitask job")
        sge.add_option("--job-id",
                       type="int",
                       dest="jobid",
                       default=666,
                       help="The job-ID")
        sge.add_option("--jobname",
                       dest="jobname",
                       default=None,
                       help="The job-Name")
        self.parser.add_option_group(sge)

        CommonParallel.addOptions(self)

    def run(self):
        scriptName=self.parser.getArgs()[0]

        if self.opts.clear:
            print_("Clearing out old the environment ....")
            for k in list(os.environ.keys()):
                if k.find("FOAM")==0 or k.find("WM_")==0:
                    del os.environ[k]
                    continue

                if k=="PATH" or k=="LD_LIBRARY_PATH":
                    tmp=os.environ[k].split(":")
                    vals=[item for item in tmp if item.find("OpenFOAM")<0]
                    os.environ[k]=":".join(vals)

        tmpdir=path.join("/tmp","pyClusterTest.%d" % self.opts.jobid)
        os.environ["TMP"]=tmpdir

        if not path.exists(tmpdir):
            mkdir(tmpdir)

        if self.opts.procnr!=None:
            os.environ["NSLOTS"]=str(self.opts.procnr)
        if self.opts.machinefile!=None:
            os.environ["PE_HOSTFILE"]=self.opts.machinefile

        machinefile=path.join(tmpdir,"machines")
        if self.opts.machinefile!=None:
            open(machinefile,"w").write(open(self.opts.machinefile).read())
        elif self.opts.procnr!=None:
            open(machinefile,"w").write("localhost\n"*self.opts.procnr)
            os.environ["PE_HOSTFILE"]=machinefile

        if self.opts.restart:
            os.environ["RESTARTED"]="1"
        else:
            os.environ["RESTARTED"]="0"

        if self.opts.taskid!=None:
            os.environ["SGE_TASK_ID"]=str(self.opts.taskid)

        os.environ["JOB_ID"]=str(self.opts.jobid)

        if self.opts.jobname==None:
            self.opts.jobname=scriptName

        os.environ["JOB_NAME"]=self.opts.jobname

        os.environ["SHELL"]=config().get("Paths","python")

        callString=scriptName
        if len(self.parser.getArgs())>1:
            for a in self.parser.getArgs()[1:]:
                callString+=" "+a

        print_("Executing",callString)
        if sys.version_info<(2,4):
            ret=system(config().get("Paths","python")+" "+callString)
        else:
            ret=subprocess.call([config().get("Paths","python")]+self.parser.getArgs())
        print_("Result=",ret)

# Should work with Python3 and Python2
