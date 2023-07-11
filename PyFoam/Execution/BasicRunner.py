#  ICE Revision: $Id$
"""Run a OpenFOAM command"""

import sys
import string
import gzip
from os import path
from platform import uname
from threading import Timer
from time import time,asctime
import uuid

from PyFoam.FoamInformation import oldAppConvention as oldApp
from PyFoam.ThirdParty.six import print_
import PyFoam.Basics.FoamFileGenerator
from PyFoam.Basics.DataStructures import makePrimitiveString
from PyFoam.Basics.Utilities import rmtree
from PyFoam.Basics.RunDatabase import RunDatabase

if not 'curdir' in dir(path) or not 'sep' in dir(path):
    print_("Warning: Inserting symbols into os.path (Python-Version<2.3)")
    path.curdir='.'
    path.sep   ='/'

from PyFoam.Execution.FoamThread import FoamThread
from PyFoam.Infrastructure.FoamServer import FoamServer
from PyFoam.Infrastructure.Logging import foamLogger
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParameterFile import ParameterFile
from PyFoam.Error import warning,error,debug
from PyFoam import configuration as config

def restoreControlDict(ctrl,runner):
    """Timed function to avoid time-stamp-problems"""
    warning("Restoring the controlDict")
    ctrl.restore()
    runner.controlDict=None

def calcLogname(logname,argv):
    if logname==None:
        return "PyFoam."+path.basename(argv[0])
    else:
        return logname

def findRestartFiles(logfile,sol):
    isRestart=False
    restartnr=None
    restartName=None
    lastlog=None

    if path.exists(logfile) or path.exists(logfile+".gz"):
        ctrlDict=ParameterFile(path.join(sol.controlDict()),backup=False)
        if ctrlDict.readParameter("startFrom")=="latestTime":
            if len(sol)>1:
                isRestart=True
                restartnr=0
                restartName=logfile+".restart00"
                lastlog=logfile

                while path.exists(restartName) or path.exists(restartName+".gz"):
                    restartnr+=1
                    lastlog=restartName
                    restartName=logfile+".restart%02d" % restartnr

    return isRestart,restartnr,restartName,lastlog

class BasicRunner(object):
    """Base class for the running of commands

    When the command is run the output is copied to a LogFile and
    (optionally) standard-out

    The argument list assumes for the first three elements the
    OpenFOAM-convention:

    <cmd> <dir> <case>

    The directory name for outputs is therefor created from <dir> and
    <case>

    Provides some handle-methods that are to be overloaded for
    additional functionality"""

    def __init__(self,
                 argv=None,
                 silent=False,
                 logname=None,
                 compressLog=False,
                 lam=None,
                 server=False,
                 restart=False,
                 noLog=False,
                 logTail=None,
                 remark=None,
                 jobId=None,
                 parameters=None,
                 writeState=True,
                 echoCommandLine=None):
        """:param argv: list with the tokens that are the command line
        if not set the standard command line is used
        :param silent: if True no output is sent to stdout
        :param logname: name of the logfile
        :param compressLog: Compress the logfile into a gzip
        :param lam: Information about a parallel run
        :param server: Whether or not to start the network-server
        :type lam: PyFoam.Execution.ParallelExecution.LAMMachine
        :param noLog: Don't output a log file
        :param logTail: only the last lines of the log should be written
        :param remark: User defined remark about the job
        :param parameters: User defined dictionary with parameters for
                 documentation purposes
        :param jobId: Job ID of the controlling system (Queueing system)
        :param writeState: Write the state to some files in the case
        :param echoCommandLine: Prefix that is printed with the command line. If unset nothing is printed
        """

        if sys.version_info < (2,3):
            # Python 2.2 does not have the capabilities for the Server-Thread
            if server:
                warning("Can not start server-process because Python-Version is too old")
            server=False

        if argv==None:
            self.argv=sys.argv[1:]
        else:
            self.argv=argv

        if oldApp():
            self.dir=path.join(self.argv[1],self.argv[2])
            if self.argv[2][-1]==path.sep:
                self.argv[2]=self.argv[2][:-1]
        else:
            self.dir=path.curdir
            if "-case" in self.argv:
                self.dir=self.argv[self.argv.index("-case")+1]

        logname=calcLogname(logname,argv)

        try:
            sol=self.getSolutionDirectory()
        except OSError:
            e = sys.exc_info()[1] # compatible with 2.x and 3.x
            error("Solution directory",self.dir,"does not exist. No use running. Problem:",e)

        self.echoCommandLine=echoCommandLine
        self.silent=silent
        self.lam=lam
        self.origArgv=self.argv
        self.writeState=writeState
        self.__lastLastSeenWrite=0
        self.__lastNowTimeWrite=0

        if self.lam!=None:
            self.argv=lam.buildMPIrun(self.argv)
            if config().getdebug("ParallelExecution"):
                debug("Command line:"," ".join(self.argv))
        self.cmd=" ".join(self.argv)
        foamLogger().info("Starting: "+self.cmd+" in "+path.abspath(path.curdir))
        self.logFile=path.join(self.dir,logname+".logfile")

        isRestart,restartnr,restartName,lastlog=findRestartFiles(self.logFile,sol)

        if restartName:
            self.logFile=restartName

        if not isRestart:
            from os import unlink
            from glob import glob
            for g in glob(self.logFile+".restart*"):
                if path.isdir(g):
                    rmtree(g)
                else:
                    unlink(g)

        self.noLog=noLog
        self.logTail=logTail
        if self.logTail:
            if self.noLog:
                warning("Log tail",self.logTail,"and no-log specified. Using logTail")
            self.noLog=True
            self.lastLines=[]

        self.compressLog=compressLog
        if self.compressLog:
            self.logFile+=".gz"

        self.fatalError=False
        self.fatalFPE=False
        self.fatalStackdump=False
        self.endSeen=False
        self.warnings=0
        self.started=False

        self.isRestarted=False
        if restart:
            self.controlDict=ParameterFile(path.join(self.dir,"system","controlDict"),backup=True)
            self.controlDict.replaceParameter("startFrom","latestTime")
            self.isRestarted=True
        else:
            self.controlDict=None

        self.run=FoamThread(self.cmd,self)

        self.server=None
        if server:
            self.server=FoamServer(run=self.run,master=self)
            self.server.setDaemon(True)
            self.server.start()
            try:
                IP,PID,Port=self.server.info()
                f=open(path.join(self.dir,"PyFoamServer.info"),"w")
                print_(IP,PID,Port,file=f)
                f.close()
            except AttributeError:
                warning("There seems to be a problem with starting the server:",self.server,"with attributes",dir(self.server))
                self.server=None

        self.createTime=None
        self.nowTime=None
        self.startTimestamp=time()

        self.stopMe=False
        self.writeRequested=False

        self.endTriggers=[]

        self.lastLogLineSeen=None
        self.lastTimeStepSeen=None

        self.remark=remark
        self.jobId=jobId

        self.data={"lines":0} #        self.data={"lines":0L}
        self.data[RunDatabase.unique_id]=str(uuid.uuid1())
        self.data["logfile"]=self.logFile
        self.data["casefullname"]=path.abspath(self.dir)
        self.data["casename"]=path.basename(path.abspath(self.dir))
        self.data["solver"]=path.basename(self.argv[0])
        self.data["solverFull"]=self.argv[0]
        self.data["commandLine"]=self.cmd
        self.data["hostname"]=uname()[1]
        if remark:
            self.data["remark"]=remark
        else:
            self.data["remark"]="No remark given"
        if jobId:
            self.data["jobId"]=jobId
        parameterFile=sol.getParametersFromFile()
        if len(parameterFile):
            self.data["parameters"]={}
            for k,v in parameterFile.items():
                self.data["parameters"][k]=makePrimitiveString(v)
        if parameters:
            if "parameters" not in self.data:
                self.data["parameters"]={}
            self.data["parameters"].update(parameters)
        self.data["starttime"]=asctime()

    def appendTailLine(self,line):
        """Append lines to the tail of the log"""
        if len(self.lastLines)>10*self.logTail:
            # truncate the lines, but not too often
            self.lastLines=self.lastLines[-self.logTail:]
            self.writeTailLog()

        self.lastLines.append(line+"\n")

    def writeTailLog(self):
        """Write the last lines to the log"""
        fh=open(self.logFile,"w")
        if len(self.lastLines)<=self.logTail:
            fh.writelines(self.lastLines)
        else:
            fh.writelines(self.lastLines[-self.logTail:])
        fh.close()

    def start(self):
        """starts the command and stays with it till the end"""

        self.started=True
        if not self.noLog:
            if self.compressLog:
                fh=gzip.open(self.logFile,"w")
            else:
                fh=open(self.logFile,"w")

        self.startHandle()

        self.writeStartTime()
        self.writeTheState("Running")

        check=BasicRunnerCheck()

        if self.echoCommandLine:
            print_(self.echoCommandLine+" "+" ".join(self.argv))

        self.run.start()
        interrupted=False

        totalWarningLines=0
        addLinesToWarning=0
        collectWarnings=True

        while self.run.check():
            try:
                self.run.read()
                if not self.run.check():
                    break

                line=self.run.getLine()

                if "errorText" in self.data:
                    self.data["errorText"]+=line+"\n"

                if addLinesToWarning>0:
                    self.data["warningText"]+=line+"\n"
                    addLinesToWarning-=1
                    totalWarningLines+=1
                    if totalWarningLines>500:
                        collectWarnings=False
                        addLinesToWarning=0
                        self.data["warningText"]+="No more warnings added because limit of 500 lines exceeded"
                self.data["lines"]+=1
                self.lastLogLineSeen=time()
                self.writeLastSeen()

                tmp=check.getTime(line)
                if check.controlDictRead(line):
                    if self.writeRequested:
                        duration=config().getfloat("Execution","controlDictRestoreWait",default=30.)
                        warning("Preparing to reset controlDict to old glory in",duration,"seconds")
                        Timer(duration,
                              restoreControlDict,
                              args=[self.controlDict,self]).start()
                        self.writeRequested=False

                if tmp!=None:
                    self.data["time"]=tmp
                    self.nowTime=tmp
                    self.writeTheState("Running",always=False)
                    self.writeNowTime()
                    self.lastTimeStepSeen=time()
                    if self.createTime==None:
                        # necessary because interFoam reports no creation time
                        self.createTime=tmp
                    try:
                        self.data["stepNr"]+=1
                    except KeyError:
                        self.data["stepNr"]=1  # =1L

                    self.data["lasttimesteptime"]=asctime()

                tmp=check.getCreateTime(line)
                self.endSeen=check.endSeen
                if tmp!=None:
                    self.createTime=tmp

                if not self.silent:
                    try:
                        print_(line)
                    except IOError:
                        e = sys.exc_info()[1] # compatible with 2.x and 3.x
                        if e.errno!=32:
                            raise e
                        else:
                            # Pipe was broken
                            self.run.interrupt()

                if line.find("FOAM FATAL ERROR")>=0 or line.find("FOAM FATAL IO ERROR")>=0:
                    self.fatalError=True
                    self.data["errorText"]="PyFoam found a Fatal Error "
                    if "time" in self.data:
                        self.data["errorText"]+="at time "+str(self.data["time"])+"\n"
                    else:
                        self.data["errorText"]+="before time started\n"
                    self.data["errorText"]+="\n"+line+"\n"

                if line.find("Foam::sigFpe::sigFpeHandler")>=0:
                    self.fatalFPE=True
                if line.find("Foam::error::printStack")>=0:
                    self.fatalStackdump=True

                if self.fatalError and line!="":
                    foamLogger().error(line)

                if line.find("FOAM Warning")>=0:
                    self.warnings+=1
                    try:
                        self.data["warnings"]+=1
                    except KeyError:
                        self.data["warnings"]=1
                    if collectWarnings:
                        addLinesToWarning=20
                        if not "warningText" in self.data:
                            self.data["warningText"]=""
                        else:
                            self.data["warningText"]+=("-"*40)+"\n"
                        self.data["warningText"]+="Warning found by PyFoam on line "
                        self.data["warningText"]+=str(self.data["lines"])+" "
                        if "time" in self.data:
                            self.data["warningText"]+="at time "+str(self.data["time"])+"\n"
                        else:
                            self.data["warningText"]+="before time started\n"
                        self.data["warningText"]+="\n"+line+"\n"

                if self.server!=None:
                    self.server._insertLine(line)

                self.lineHandle(line)

                if not self.noLog:
                    fh.write(line+"\n")
                    fh.flush()
                elif self.logTail:
                    self.appendTailLine(line)

            except KeyboardInterrupt:
                e = sys.exc_info()[1] # compatible with 2.x and 3.x
                foamLogger().warning("Keyboard Interrupt")
                self.run.interrupt()
                self.writeTheState("Interrupted")
                self.data["keyboardInterrupt"]=True
                interrupted=True

        if not "keyboardInterrupt" in self.data:
            self.data["keyboardInterrupt"]=self.run.keyboardInterupted

        self.data["interrupted"]=interrupted
        self.data["OK"]=self.runOK()
        self.data["endSeen"]=self.endSeen
        self.data["cpuTime"]=self.run.cpuTime()
        self.data["cpuUserTime"]=self.run.cpuUserTime()
        self.data["cpuSystemTime"]=self.run.cpuSystemTime()
        self.data["wallTime"]=self.run.wallTime()
        self.data["usedMemory"]=self.run.usedMemory()
        self.data["endtime"]=asctime()

        self.data["fatalError"]=self.fatalError
        self.data["fatalFPE"]=self.fatalFPE
        self.data["fatalStackdump"]=self.fatalStackdump

        self.writeNowTime(force=True)

        self.stopHandle()

        if not interrupted:
            if self.endSeen:
                self.writeTheState("Finished - Ended")
            else:
                self.writeTheState("Finished")

        for t in self.endTriggers:
            t()

        if not self.noLog:
            fh.close()
        elif self.logTail:
            self.writeTailLog()

        if self.server!=None:
            self.server.deregister()
            self.server.kill()

        foamLogger().info("Finished")

        return self.data

    def writeToStateFile(self,fName,message):
        """Write a message to a state file"""
        if self.writeState:
            open(path.join(self.dir,"PyFoamState."+fName),"w").write(message+"\n")

    def writeStartTime(self):
        """Write the real time the run was started at"""
        self.writeToStateFile("StartedAt",asctime())

    def writeTheState(self,state,always=True):
        """Write the current state the run is in"""
        if always or (time()-self.__lastLastSeenWrite)>9:
            self.writeToStateFile("TheState",state)

    def writeLastSeen(self):
        if (time()-self.__lastLastSeenWrite)>10:
            self.writeToStateFile("LastOutputSeen",asctime())
            self.__lastLastSeenWrite=time()

    def writeNowTime(self,force=False):
        if (time()-self.__lastNowTimeWrite)>10 or force:
            self.writeToStateFile("CurrentTime",str(self.nowTime))
            self.__lastNowTimeWrite=time()

    def runOK(self):
        """checks whether the run was successful"""
        if self.started:
            return not self.fatalError and not self.fatalFPE and not self.fatalStackdump # and self.run.getReturnCode()==0
        else:
            return False

    def startHandle(self):
        """to be called before the program is started"""
        pass

    def _writeStopAt(self,value,message):
        """Write stopAt to stop the run gracefully"""
        if not self.stopMe:
            self.stopMe=True
            if not self.isRestarted:
                if self.controlDict:
                    warning("The controlDict has already been modified. Restoring will be problementic")
                self.controlDict=ParameterFile(path.join(self.dir,"system","controlDict"),backup=True)
            self.controlDict.replaceParameter("stopAt",value)
            warning(message)

    def stopGracefully(self):
        """Tells the runner to stop at the next convenient time"""
        self._writeStopAt("writeNow","Stopping run and writting")

    def stopAtNextWrite(self):
        """Tells the runner to stop at the next write"""
        self._writeStopAt("nextWrite","Stopping run at next write")

    def stopWithoutWrite(self):
        """Tells the runner to stop without writing"""
        self._writeStopAt("noWriteNow","Stopping run without writing")

    def writeResults(self):
        """Writes the next possible time-step"""
        #        warning("writeResult is not yet implemented")
        if not self.writeRequested:
            if not self.isRestarted:
                if self.controlDict:
                    warning("The controlDict has already been modified. Restoring will be problementic")
                self.controlDict=ParameterFile(path.join(self.dir,"system","controlDict"),backup=True)
            self.controlDict.replaceParameter("writeControl","timeStep")
            self.controlDict.replaceParameter("writeInterval","1")
            self.writeRequested=True

    def stopHandle(self):
        """called after the program has stopped"""
        if self.stopMe or self.isRestarted:
            self.controlDict.restore()

    def lineHandle(self,line):
        """called every time a new line is read"""
        pass

    def logName(self):
        """Get the name of the logfiles"""
        return self.logFile

    def getSolutionDirectory(self,archive=None):
        """:return: The directory of the case
        :rtype: PyFoam.RunDictionary.SolutionDirectory
        :param archive: Name of the directory for archiving results"""

        return SolutionDirectory(self.dir,archive=archive,parallel=True)

    def addEndTrigger(self,f):
        """:param f: A function that is to be executed at the end of the simulation"""
        self.endTriggers.append(f)

import re

class BasicRunnerCheck(object):
    """A small class that does primitve checking for BasicRunner
    Duplicates other efforts, but ...."""

    floatRegExp="[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"

    def __init__(self):
        #        self.timeExpr=re.compile("^Time = (%f%)$".replace("%f%",self.floatRegExp))
        self.timeExpr=config().getRegexp("SolverOutput","timeregexp")
        self.createExpr=re.compile("^Create mesh for time = (%f%)$".replace("%f%",self.floatRegExp))
        self.endSeen=False

    def getTime(self,line):
        """Does this line contain time information?"""
        m=self.timeExpr.match(line)
        if m:
            self.endSeen=False
            try:
                return float(m.group(2))
            except ValueError:
                warning("Problem while converting",m.group(2),"to float")
                return None
        else:
            if line.strip()=="End":
                self.endSeen=True
            return None

    def getCreateTime(self,line):
        """Does this line contain mesh time information?"""
        m=self.createExpr.match(line)
        if m:
            return float(m.group(1))
        else:
            return None

    def controlDictRead(self,line):
        """Was the controlDict reread?"""
        phrases=["Reading object controlDict from file",
                 "Re-reading object controlDict from file"]

        for p in phrases:
            if line.find(p)>=0:
                return True

        return False

# Should work with Python3 and Python2
