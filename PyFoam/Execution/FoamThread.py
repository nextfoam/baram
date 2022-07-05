#  ICE Revision: $Id$
"""Thread wrappers for OpenFOAM"""

import sys

from threading import Thread,Lock,Timer
from PyFoam.ThirdParty.six import print_
from PyFoam.Error import warning,error
from PyFoam import configuration as config
from PyFoam.FoamInformation import shellExecutionPrefix

if sys.version_info<(2,4):
    from popen2 import Popen4
else:
    import subprocess

from time import time,sleep

try:
    from resource import getrusage,getpagesize,RUSAGE_CHILDREN
except ImportError:
    try:
        from PyFoam.ThirdParty.winhacks import getrusage,getpagesize,RUSAGE_CHILDREN
    except ImportError:
        error("Unable to import working getrusage,getpagesize,RUSAGE_CHILDREN functions.")

from os import kill,path,unlink
from platform import uname
import signal

from PyFoam.Basics.LineReader import LineReader
from PyFoam.Infrastructure.Logging import foamLogger

def checkForStopFile(thrd):
    """Checks for the file 'stop' in the directory of the FoamRun. If
    it exists it is removed and the run is stopped gracefully

    If a file 'write' is found then the next timestep is written

    File 'stopWrite' stops the run at the next write

    'kill' stops without writing"""

    fName=path.join(thrd.runner.dir,"stop")

    if path.exists(fName):
        unlink(fName)
        thrd.runner.stopGracefully()
        return

    fName=path.join(thrd.runner.dir,"write")

    if path.exists(fName):
        unlink(fName)
        thrd.runner.writeResults()

    fName=path.join(thrd.runner.dir,"stopWrite")

    if path.exists(fName):
        unlink(fName)
        thrd.runner.stopAtNextWrite()

    fName=path.join(thrd.runner.dir,"kill")

    if path.exists(fName):
        unlink(fName)
        thrd.runner.stopWithoutWrite()

    thrd.timer2=Timer(thrd.timerTime,checkForStopFile,args=[thrd])
    thrd.timer2.start()

def getLinuxMem(thrd):
    """Reads the Memory usage of a thread on a linux-System

    :param thrd: the thread object in question"""

    #    print "Timer called"

    if not thrd.isLinux or thrd.threadPid<0:
        return

    mem=0

    try:
        import psutil
        me=psutil.Process(thrd.threadPid)
        procs=[me]+me.children(True)
        try:
            for p in procs:
                try:
                    mInfo=p.memory_full_info()
                    mem+=mInfo.uss+mInfo.pss # Unique-memory and proportional
                                         # of shared memory. smaller than
                                         # RSS
                except AttributeError:
                    mInfo=p.memory_info()
                    mem+=mInfo.rss
        except psutil.NoSuchProcess:
            pass
    except ImportError:
        try:
            t=open('/proc/%d/status' % thrd.threadPid)
            v=t.read()
            t.close()
            #        f=open('/tmp/test%dstatus' % thrd.threadPid,'w')
            #        f.write(v)
            #        f.close()

            i=v.index('VmRSS')
            tmp=v[i:].split()
            if len(tmp)>=3:
                mem=int(tmp[1])
                if tmp[2].lower()=='kb':
                    mem*=1024
                elif tmp[2].lower()=='mb':
                    mem*=1024*1024
                else:
                    mem=-1
        except Exception:
            e = sys.exc_info()[1] # compatible with 2.x and 3.x
            print_("Getting LinuxMem:",e)
            mem=-1

    if mem>thrd.linuxMaxMem:
        #        print "Setting Memory to: ",mem
        thrd.linuxMaxMem=mem

    #    print "Restarting Timer"

    thrd.timer=Timer(thrd.timerTime,getLinuxMem,args=[thrd])
    thrd.timer.start()

class FoamThread(Thread):
    """Thread running an OpenFOAM command

    The output of the command can be accessed in a thread-safe manner,
    line by line

    Designed to be used by the BasicRunner-class"""

    def __init__(self,cmdline,runner):
        """:param cmdline:cmdline - Command line of the OpenFOAM command
        :param runner: the Runner-object that started this thread"""
        Thread.__init__(self)
        self.cmdline=cmdline
        self.runner=runner
        self.output=None
        self.reader=LineReader(config().getboolean("SolverOutput","stripSpaces"))
        self.keyboardInterupted=False

        self.isLinux=False
        self.isDarwin=False
        self.isWindows=False
        self.threadPid=-1
        self.who=RUSAGE_CHILDREN

        if uname()[0]=="Linux":
            self.isLinux=True
            self.linuxMaxMem=0
        elif uname()[0]=="Darwin":
            self.isDarwin=True
        elif uname()[0]=="Windows":
            self.isWindows=True

        self.resStart=None
        self.resEnd=None

        self.timeStart=None
        self.timeEnd=None

        self.timerTime=5.

        self.stateLock=Lock()
        self.setState(False)

        self.status=None
        self.returncode=None

        self.lineLock=Lock()
        self.line=""

        self.stateLock.acquire()

    def run(self):
        """start the command"""
        # print "Starting ",self.cmdline
        self.resStart=getrusage(self.who)
        self.timeStart=time()

        if sys.version_info<(2,4):
            run=Popen4(self.cmdline)
            self.output=run.fromchild
        else:
            run=subprocess.Popen(shellExecutionPrefix()+self.cmdline,
                                 shell=True,
                                 bufsize=0,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 close_fds=True)
            self.output=run.stdout
        self.run=run
        self.threadPid=run.pid
        foamLogger().info("Started with PID %d" % self.threadPid)
        if self.isLinux:
            #            print "Starting Timer"
            self.timer=Timer(0.1*self.timerTime,getLinuxMem,args=[self])
            self.timer.start()

        #            print "Starting Timer"
        self.timer2=Timer(0.5*self.timerTime,checkForStopFile,args=[self])
        self.timer2.start()

        self.hasSomethingToSay=True
        self.stateLock.release()

        try:
            # print "Waiting",time()
            self.status=run.wait()
            # Python 2.3 on Mac OS X never seems to reach this point
            # print "After wait",time()
            # print "Status:",self.status

            # to give a chance to read the remaining output
            if self.hasSomethingToSay:
                sleep(2.)
            while self.reader.read(self.output):
                print_("Unused output:",self.reader.line)
        except OSError:
            e = sys.exc_info()[1] # compatible with 2.x and 3.x
            print_("Exeption caught:",e)

        self.stopTimer()

        self.threadPid=-1

        self.resEnd=getrusage(self.who)
        self.timeEnd=time()
        #        print "End:",self.timeEnd
        # print "Returned",self.status

        self.getReturnCode()

    def getReturnCode(self):
        if sys.version_info<(2,4):
            # Don't know how to get the returncode from a Popen4-object
            self.returncode=0
        else:
            self.returncode=self.run.returncode
        return self.returncode

    def stopTimer(self):
        if self.isLinux:
            self.timer.cancel()
        self.timer2.cancel()

    def read(self):
        """read another line from the output"""
        self.setState(self.reader.read(self.output))
        self.lineLock.acquire()
        self.line=self.reader.line
        self.lineLock.release()

    def getLine(self):
        """gets the last line from the output"""
        self.lineLock.acquire()
        val=self.line
        self.lineLock.release()

        return val

    def interrupt(self):
        """A keyboard-interrupt is reported"""
#        print "Interrupt"
        self.reader.wasInterupted=True
        self.setState(False)

    def setState(self,state):
        """sets the state of the thread (is there any more output)"""
        self.stateLock.acquire()
        self.hasSomethingToSay=state
        if not self.hasSomethingToSay and self.timeStart and self.reader.wasInterupted:
            self.keyboardInterupted=self.reader.keyboardInterupted

            if self.threadPid>0:
                msg="Killing PID %d" % self.threadPid
                print_(msg)
                foamLogger().warning(msg)
                try:
                    kill(self.threadPid,signal.SIGKILL)
                except OSError:
                    warning("Process",self.threadPid,"was already dead")

        #        print "Set: ",state
        self.stateLock.release()

    def check(self):
        """:return: False if there is no more output of the command"""
        self.stateLock.acquire()
        state=self.hasSomethingToSay
        #        print "Get: ",state
        self.stateLock.release()

        return state

    def cpuTime(self):
        """:return: number of seconds CPU-Time used"""
        return self.cpuUserTime()+self.cpuSystemTime()

    def cpuUserTime(self):
        """:return: number of seconds CPU-Time used in user mode"""
        if self.resEnd==None: # and self.isDarwin:
            # Mac OS X needs this (Ubuntu too?)
            self.resEnd=getrusage(self.who)
        if self.resStart==None or self.resEnd==None:
            return 0
        else:
            return self.resEnd.ru_utime-self.resStart.ru_utime

    def cpuSystemTime(self):
        """:return: number of seconds CPU-Time used in system mode"""
        if self.resEnd==None: #  and self.isDarwin:
            # Mac OS X needs this (Ubuntu too?)
            self.resEnd=getrusage(self.who)
        if self.resStart==None or self.resEnd==None:
            return 0
        else:
            return self.resEnd.ru_stime-self.resStart.ru_stime

    def usedMemory(self):
        """:return: maximum resident set size in MegaByte"""
        scale=1024.*1024.
        if self.isLinux:
            return self.linuxMaxMem/scale

        if self.resStart==None or self.resEnd==None:
            return 0.
        else:
            return getpagesize()*(self.resEnd.ru_maxrss-self.resStart.ru_maxrss)/scale

    def wallTime(self):
        """:return: the wall-clock-time needed by the process"""
        if self.timeEnd==None: #  and self.isDarwin:
            # Mac OS X needs this (Ubuntu too?)
            self.timeEnd=time()

        self.timeEnd=time()

        #        print "Wall:",self.timeEnd,self.timeStart
        if self.timeStart==None or self.timeEnd==None:
            return 0
        else:
            return self.timeEnd-self.timeStart
