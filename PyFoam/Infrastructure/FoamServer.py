#  ICE Revision: $Id$
"""A XMLRPC-Server that answeres about the current state of a Foam-Run"""

from PyFoam.ThirdParty.six import PY3

from PyFoam.Infrastructure.ServerBase import ServerBase

if PY3:
    from xmlrpc.client import ServerProxy
else:
    from xmlrpclib import ServerProxy

from time import sleep
from random import random
import select

from PyFoam import configuration as config
from PyFoam import versionString
from PyFoam.Basics.RingBuffer import RingBuffer
from PyFoam.Infrastructure.NetworkHelpers import freeServerPort
from PyFoam.Infrastructure.Logging import foamLogger
from PyFoam.FoamInformation import foamMPI
from PyFoam.RunDictionary.ParameterFile import ParameterFile
from PyFoam.Error import warning
from PyFoam.Basics.GeneralPlotTimelines import allPlots
from PyFoam.Basics.TimeLineCollection import allLines
from PyFoam.Infrastructure.ZeroConf import ZeroConfFoamServer

from PyFoam.Infrastructure.Hardcoded import userName

from threading import Lock,Thread,Timer
from time import time
from os import environ,path,getpid,getloadavg
from platform import uname
import socket

import sys,string
from traceback import extract_tb

def findFreePort(useSSL=None):
    """Finds a free server port on this machine and returns it

    Valid server ports are in the range 18000 upward (the function tries to
    find the lowest possible port number

    ATTENTION: this part may introduce race conditions"""

    if useSSL is None:
        useSSL=config().getboolean("Network","SSLServerDefault")

    if useSSL:
        startPort=config().getint("Network","startServerPortSSL")
    else:
        startPort=config().getint("Network","startServerPort")
    return useSSL,freeServerPort(startPort,
                                 length=config().getint("Network","nrServerPorts"))

# Wrapper that checks if the method was authenticated
from functools import wraps
def needsAuthentication(func):
    @wraps(func)
    def wrap(s,*args):
        if not s._foamserver._server.authOK:
            return "Sorry. You're not authenticated for this"
        return func(s,*args)
    return wrap

class FoamAnswerer(object):
    """The class that handles the actual requests (only needed to hide the
    Thread-methods from the world
    """
    def __init__(self,run=None,master=None,lines=100,foamserver=None):
        """
        :param run: The thread that controls the run
        :param master: The Runner-Object that controls everything
	:param lines: the number of lines the server should remember
        """
        self._run=run
        self._master=master
        self._foamserver=foamserver
        self._lines=RingBuffer(nr=lines)
        self._lastTime=time()
        self._linesLock=Lock()
        self._maxOutputTime=config().getfloat("IsAlive","maxTimeStart")

    def _insertLine(self,line):
        """Inserts a new line, not to be called via XMLRPC"""
        self._linesLock.acquire()
        self._lines.insert(line)
        tmp=time()
        if (tmp-self._lastTime)>self._maxOutputTime:
            self._maxOutputTime=tmp-self._lastTime
        self._lastTime=tmp
        self._linesLock.release()

    def isFoamServer(self):
        """This is a Foam-Server (True by default)"""
        return True

    def isLiving(self):
        """The calculation still generates output and therefor seems to be living"""
        return self.elapsedTime()<self._maxOutputTime

    @needsAuthentication
    def _kill(self):
        """Interrupts the FOAM-process"""
        if self._run:
            foamLogger().warning("Killed by request")
            self._run.interrupt()
            return True
        else:
            return False

    @needsAuthentication
    def stop(self):
        """Stops the run gracefully (after writing the last time-step to disk)"""
        self._master.stopGracefully()
        return True

    @needsAuthentication
    def stopAtNextWrite(self):
        """Stops the run gracefully the next time data is written to disk"""
        self._master.stopAtNextWrite()
        return True

    @needsAuthentication
    def write(self):
        """Makes the program write the next time-step to disk and the continue"""
        self._master.writeResults()
        return True

    def argv(self):
        """Argument vector with which the runner was called"""
        if self._master:
            return self._master.origArgv
        else:
            return []

    def usedArgv(self):
        """Argument vector with which the runner started the run"""
        if self._master:
            return self._master.argv
        else:
            return []

    def isParallel(self):
        """Is it a parallel run?"""
        if self._master:
            return self._master.lam!=None
        else:
            return False

    def procNr(self):
        """How many processors are used?"""
        if self._master:
            if self._master.lam!=None:
                return self._master.lam.cpuNr()
            else:
                return 1
        else:
            return 0

    @needsAuthentication
    def nrWarnings(self):
        """Number of warnings the executable emitted"""
        if self._master:
            return self._master.warnings
        else:
            return 0

    def commandLine(self):
        """The command line"""
        if self._master:
            return " ".join(self._master.origArgv)
        else:
            return ""

    @needsAuthentication
    def actualCommandLine(self):
        """The actual command line used"""
        if self._master:
            return self._master.cmd
        else:
            return ""

    @needsAuthentication
    def scriptName(self):
        """Name of the Python-Script that runs the show"""
        return sys.argv[0]

    @needsAuthentication
    def runnerData(self):
        """:return: the data the runner collected so far"""
        return self._master.data

    def lastLogLineSeen(self):
        """:return: the time at which the last log-line was seen"""
        return self._master.lastLogLineSeen

    def lastTimeStepSeen(self):
        """:return: the time at which the last log-line was seen"""
        return self._master.lastTimeStepSeen

    @needsAuthentication
    def lastLine(self):
        """:return: the last line that was output by the running FOAM-process"""
        self._linesLock.acquire()
        result=self._lines.last()
        self._linesLock.release()
        if not result:
            return ""
            return result

    @needsAuthentication
    def tail(self):
        """:return: the current last lines as a string"""
        self._linesLock.acquire()
        tmp=self._lines.dump()
        self._linesLock.release()
        result=""
        for l in tmp:
            result+=l

        return result

    def elapsedTime(self):
        """:return: time in seconds since the last line was output"""
        self._linesLock.acquire()
        result=time()-self._lastTime
        self._linesLock.release()

        return result

    @needsAuthentication
    def getEnviron(self,name):
        """:param name: name of an environment variable
        :return: value of the variable, empty string if non-existing"""
        result=""
        if name in environ:
            result=environ[name]
        return result

    def mpi(self):
        """:return: name of the MPI-implementation"""
        return foamMPI()

    def foamVersion(self):
        """Version number of the Foam-Version"""
        return self.getEnviron("WM_PROJECT_VERSION")

    def pyFoamVersion(self):
        """:return: Version number of the PyFoam"""
        return versionString()

    def uname(self):
        """:return: the complete uname-information"""
        return uname()

    def ip(self):
        """:return: the ip of this machine"""
        try:
            address = socket.gethostbyname(socket.gethostname())
            # This gives 127.0.0.1 if specified so in the /etc/hosts ...
        except:
            address = ''
        if not address or address.startswith('127.'):
            # ...the hard way.
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('10.255.255.255', 1))
                address = s.getsockname()[0]
            except:
                # Got no internet connection
                address="127.0.0.1"
        return address

    def hostname(self):
        """:return: The name of the computer"""
        return uname()[1]

    @needsAuthentication
    def configuration(self):
        """:return: all the configured parameters"""
        return config().dump()

    @needsAuthentication
    def cwd(self):
        """:return: the current working directory"""
        return path.abspath(path.curdir)

    @needsAuthentication
    def pid(self):
        """:return: the PID of the script"""
        return getpid()

    def loadAvg(self):
        """:return: a tuple with the average loads of the last 1, 5 and 15 minutes"""
        return getloadavg()

    def user(self):
        """:return: the user that runs this script"""
        return userName()

    def id(self):
        """:return: an ID for this run: IP:port:startTimestamp """
        return "%s:%d:%f" % (self.ip(),self._foamserver._port,self.startTimestamp())

    def startTimestamp(self):
        """:return: the unix-timestamp of the process start"""
        return self._master.startTimestamp

    def time(self):
        """:return: the current time in the simulation"""
        if self._master.nowTime:
            return self._master.nowTime
        else:
            return 0

    def createTime(self):
        """:return: the time in the simulation for which the mesh was created"""
        if self._master.nowTime:
            return self._master.createTime
        else:
            return 0

    def _readParameter(self,name):
        """Reads a parametr from the controlDict
        :param name: the parameter
        :return: The value"""
        control=ParameterFile(self._master.getSolutionDirectory().controlDict())
        return control.readParameter(name)

    def startTime(self):
        """:return: parameter startTime from the controlDict"""
        return float(self._readParameter("startTime"))

    def endTime(self):
        """:return: parameter endTime from the controlDict"""
        return float(self._readParameter("endTime"))

    def deltaT(self):
        """:return: parameter startTime from the controlDict"""
        return float(self._readParameter("deltaT"))

    @needsAuthentication
    def pathToSolution(self):
        """:return: the path to the solution directory"""
        return self._master.getSolutionDirectory().name

    @needsAuthentication
    def writtenTimesteps(self):
        """:return: list of the timesteps on disc"""
        return self._master.getSolutionDirectory().getTimes()

    @needsAuthentication
    def solutionFiles(self,time):
        """:param time: name of the timestep
        :return: list of the solution files at that timestep"""
        return self._master.getSolutionDirectory()[time].getFiles()

    @needsAuthentication
    def listFiles(self,directory):
        """:param directory: Sub-directory of the case
        :return: List of the filenames (not directories) in that case"""
        return self._master.getSolutionDirectory().listFiles(directory)

    @needsAuthentication
    def getDictionaryText(self,directory,name):
        """:param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :return: the contents of the file as a big string"""
        return self._master.getSolutionDirectory().getDictionaryText(directory,name)

    @needsAuthentication
    def getDictionaryContents(self,directory,name):
        """:param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :return: the contents of the file as a python data-structure"""
        return self._master.getSolutionDirectory().getDictionaryContents(directory,name)

    @needsAuthentication
    def writeDictionaryText(self,directory,name,text):
        """Writes the contents of a dictionary
        :param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :param text: String with the dictionary contents"""

        self._master.getSolutionDirectory().writeDictionaryText(directory,name,text)

        return True

    @needsAuthentication
    def writeDictionaryContents(self,directory,name,contents):
        """Writes the contents of a dictionary
        :param directory: Sub-directory of the case
        :param name: name of the dictionary file
        :param contents: Python-dictionary with the dictionary contents"""

        self._master.getSolutionDirectory().writeDictionaryContents(directory,name,contents)
        return True

    @needsAuthentication
    def getPlots(self):
        """Get all the information about the plots"""
        return allPlots().prepareForTransfer()

    @needsAuthentication
    def getPlotData(self):
        """Get all the data for the plots"""
        return allLines().prepareForTransfer()

    @needsAuthentication
    def controlDictUnmodified(self):
        """Checks whether there is a pending change to the controlDict"""
        return self._master.controlDict == None

    def getRemark(self):
        """Get the user-defined remark for this job"""
        if self._master.remark:
            return self._master.remark
        else:
            return ""

    @needsAuthentication
    def setRemark(self,remark):
        """Overwrite the user-defined remark
        :return: True if the remark was set previously"""
        oldRemark=self._master.remark
        self._master.remark=remark
        return oldRemark!=None

    def jobId(self):
        """Return the job-ID of the queuing-system. Empty if unset"""
        if self._master.jobId:
            return self._master.jobId
        else:
            return ""

class FoamServer(Thread):
    """This is the class that serves the requests about the FOAM-Run"""
    def __init__(self,run=None,master=None,lines=100):
        """
        :param run: The thread that controls the run
        :param master: The Runner-Object that controls everything
        :param lines: the number of lines the server should remember
	"""
        Thread.__init__(self)

        self.isRegistered=False

        tries=0

        maxTries=config().getint("Network","socketRetries")

        ok=False

        self._zConf=ZeroConfFoamServer()

        while not ok and tries<maxTries:
            ok=True
            tries+=1

            self.__ssl,self._port=findFreePort()

            self._running=False

            if self._port<0:
                foamLogger().warning("Could not get a free port. Server not started")
                return

            try:
                foamLogger().info("Serving on port %d" % self._port)
                self._server=ServerBase(('',self._port),useSSL=self.__ssl,logRequests=False)
                self.__ssl=self._server.useSSL
                self._server.register_introspection_functions()
                self._answerer=FoamAnswerer(run=run,master=master,lines=lines,foamserver=self)
                self._server.register_instance(self._answerer)
                self._server.register_function(self.killServer)
                self._server.register_function(self.kill)
                if run:
                    self._server.register_function(run.cpuTime)
                    self._server.register_function(run.cpuUserTime)
                    self._server.register_function(run.cpuSystemTime)
                    self._server.register_function(run.wallTime)
                    self._server.register_function(run.usedMemory)
            except socket.error:
                reason = sys.exc_info()[1] # compatible with 2.x and 3.x
                ok=False
                warning("Could not start on port",self._port,"althoug it was promised. Try:",tries,"of",maxTries)
                foamLogger().warning("Could not get port %d - SocketError: %s. Try %d of %d" % (self._port,str(reason),tries,maxTries))
                sleep(2+20*random())

        if not ok:
            foamLogger().warning("Exceeded maximum number of tries for getting a port: %d" % maxTries)
            warning("Did not get a port after %d tries" % tries)
        else:
            if tries>1:
                warning("Got a port after %d tries" % tries)

    def run(self):
        foamLogger().info("Running server at port %d" % self._port)
        if self._port<0:
            return
        # wait befor registering to avoid timeouts
        reg=Timer(5.,self.register)
        reg.start()

        self._running=True

        try:
            while self._running:
                self._server.handle_request()
        except select.error:
            # This seems to be necessary since python 2.6
            pass

        # self._server.serve_forever() # the old way
        self._server.server_close()

        foamLogger().warning("Stopped serving on port %d" % self._port)

    def info(self):
        """Returns the IP, the PID and the port of the server (as one tuple)"""

        return self._answerer.ip(),self._answerer.pid(),self._port

    def kill(self):
        """Interrupts the FOAM-process (and kills the server)"""
        self._answerer._kill()
        return self.killServer()

    def killServer(self):
        """Kills the server process"""
        tmp=self._running
        self._running=False
        return tmp

    def register(self):
        """Tries to register with the Meta-Server"""

        foamLogger().info("Trying to register as IP:%s PID:%d Port:%d"
                          % (self._answerer.ip(),
                             self._answerer.pid(),self._port))

        self._zConf.register(self._answerer,self._port,self.__ssl)

        try:
            try:
                meta=ServerProxy(
                    "http://%s:%d" % (config().get(
                        "Metaserver","ip"),config().getint("Metaserver","port")))
                response=meta.registerServer(self._answerer.ip(),
                                             self._answerer.pid(),self._port)
                self.isRegistered=True
                foamLogger().info("Registered with server. Response "
                                  + str(response))
            except socket.error:
                reason = sys.exc_info()[1] # compatible with 2.x and 3.x
                foamLogger().warning("Can't connect to meta-server - SocketError: "+str(reason))
            except:
                foamLogger().error("Can't connect to meta-server - Unknown Error: "+str(sys.exc_info()[0]))
                foamLogger().error(str(sys.exc_info()[1]))
                foamLogger().error("Traceback: "+str(extract_tb(sys.exc_info()[2])))
        except:
            # print "Error during registering (no socket module?)"
            pass

    def deregister(self):
        """Tries to deregister with the Meta-Server"""

        self._zConf.deregister()

        if  self.isRegistered:
            try:
                meta=ServerProxy("http://%s:%d" % (config().get("Metaserver","ip"),config().getint("Metaserver","port")))
                meta.deregisterServer(self._answerer.ip(),self._answerer.pid(),self._port)
            except socket.error:
                reason = sys.exc_info()[1] # compatible with 2.x and 3.x
                foamLogger().warning("Can't connect to meta-server - SocketError: "+str(reason))
            except:
                foamLogger().error("Can't connect to meta-server - Unknown Error: "+str(sys.exc_info()[0]))
                foamLogger().error(str(sys.exc_info()[1]))
                foamLogger().error("Traceback: "+str(extract_tb(sys.exc_info()[2])))
        else:
            foamLogger().warning("Not deregistering, because it seems we were not registered in the first place ")
        self._server.server_close()

    def _insertLine(self,line):
        """Inserts a new line, not to be called via XMLRPC"""
        self._answerer._insertLine(line)

# Should work with Python3 and Python2
