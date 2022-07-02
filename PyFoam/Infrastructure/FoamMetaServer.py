#  ICE Revision: $Id$
"""A XMLRPC-Server that knows all PyFoam-Runs in its subnet"""

from PyFoam.Infrastructure.ServerBase import ServerBase,getServerProxy
from PyFoam.ThirdParty.six import PY3

if PY3:
    from xmlrpc.server import Fault
    from xmlrpc.client import ServerProxy
else:
    from xmlrpclib import Fault,ServerProxy
    from PyFoam.ThirdParty.IPy import IP

import socket
from threading import Lock,Thread,Timer

from PyFoam.Infrastructure.Logging import foamLogger
from PyFoam.Infrastructure.NetworkHelpers import checkFoamServers
from PyFoam import configuration as config
from PyFoam.ThirdParty.six import print_,binary_type

import sys,time,copy,os
from traceback import extract_tb

DO_WEBSYNC = config().getboolean('Metaserver','doWebsync')
WEBSERVER_RPCURL = "http://%(host)s/metaserver/xmlrpc/" % {"host":config().get('Metaserver','webhost')}
WEBSYNC_INTERVAL = config().getfloat('Metaserver','websyncInterval')

class FoamMetaServer(object):
    """The Metaserver.

    Collects all the known FoamServers. Then waits for the servers to
    register themselves. Checks at regular intervalls whether the processes are still alive
    """
    def __init__(self,port=None):
        """:param port: The port on which the server should listen"""
        if port==None:
            port=config().getint("Metaserver","port")

        foamLogger("server").info("Starting Server up")
        self.pid=os.getpid()
        try:
            self.webserver = ServerProxy(WEBSERVER_RPCURL)
            self.servers={}
            self.dataLock=Lock()
            self.startupLock=Lock()

            self.collect()

            self.checker=MetaChecker(self)
            self.checker.setDaemon(True)
            self.checker.start()

            self._server=ServerBase(('',port),logRequests=False)
            self._server.register_instance(self)
            self._server.register_introspection_functions()
            self._server.serve_forever() # occasional errors with "Broken pipe"
        except KeyboardInterrupt:
            foamLogger("server").warning("Keyboard interrupt")
        except socket.error as reason:
            foamLogger("server").error("Socket Error: "+str(reason))
            print_("Can't start server, Problem with socket: ",reason[1])
        except:
            foamLogger("server").error("Unknown exception "+str(sys.exc_info()[0]))
            foamLogger("server").error(str(sys.exc_info()[1]))
            foamLogger("server").error("Traceback: "+str(extract_tb(sys.exc_info()[2])))

    def list(self):
        """Returns a list of the found Foam-Runs"""
        self.dataLock.acquire()
        servers=copy.deepcopy(self.servers)
        self.dataLock.release()

        result={}

        for idnum,info in servers.iteritems():
            result[idnum]=info._info

        return result

    def collect(self):
        """Starts a thread that collects the data of the servers from the net"""
        collector=MetaCollector(self)
        collector.setDaemon(True)
        collector.start()
        return True

    def scan(self,additional):
        """Starts a thread that collects the data of the servers from the net
        :param additional: a string with a list of additional subnets that should be scanned"""
        collector=MetaCollector(self,additional=additional)
        collector.setDaemon(True)
        collector.start()
        return True

    def kill(self):
        """Exits the server"""
        foamLogger("server").warning("Terminating due to request")
        t=Timer(1.,self._suicide)
        t.start()
        return True

    def _suicide(self):
        """The server kills itself"""
        os.kill(self.pid,1)

    def registerServer(self,ip,pid,port,sync=True,external=False):
        """Registers a new server via XMLRPC
        :param ip: IP of the server
        :param pid: Die PID at the server
        :param port: the port at which the server is listening
        :param sync: (optional) if to sync with the webserver or not
        """
        return self._registerServer(ip,pid,port,sync=sync,external=True)

    def _registerServer(self,ip,pid,port,sync=True,external=False):
        """Registers a new server
        :param ip: IP of the server
        :param pid: Die PID at the server
        :param port: the port at which the server is listening
        :param external: was called via XMLRPC
        :param sync: (optional) if to sync with the webserver or not
        """
        self.dataLock.acquire()
        serverID="%s:%d" % (ip,port)

        foamLogger("server").info("Registering: %s with PID: %d" % (serverID,pid))

        insertServer=False
        try:
            if self.servers.has_key(serverID):
                # maybe it's another process
                server=getServerProxy(ip,port)
                gotPid=server.pid()
                if pid!=gotPid:
                    self.servers.pop(serverID)
                    foamLogger("server").warning("Server "+serverID+" changed PID from %d to %d" % (pid,gotPid))
                    insertServer=True
                else:
                    foamLogger("server").warning("Server "+serverID+" already registered")
            else:
                insertServer=True

            if insertServer:
                new=ServerInfo(ip,pid,port)
                doIt=external
                if not doIt:
                    doIt=new.checkValid()

                if doIt:
                    new.queryData() # occasional errors with 'Connection refused'
                    self.servers[serverID]=new
                    foamLogger("server").debug("Inserted "+serverID)
        except:
            foamLogger("server").error("Registering Server "+serverID+" failed:"+str(sys.exc_info()[0]))
            foamLogger("server").error("Reason:"+str(sys.exc_info()[1]))
            foamLogger("server").error("Trace:"+str(extract_tb(sys.exc_info()[2])))

        self.dataLock.release()

        if DO_WEBSYNC and insertServer and sync:
            foamLogger("server").info("Registering %s for webserver: %s" % (serverID,'new/%(ip)s/%(port)s/' % {'ip':ip, 'port':port}))
            try:
                self.webserver.new_process(ip, port)
            except:
                foamLogger("server").warning("Registering %s for webserver failed!" % (serverID))
        return True

    def deregisterServer(self,ip,pid,port,sync=True):
        """Deregisters a server
        :param ip: IP of the server
        :param pid: Die PID at the server
        :param port: the port at which the server is listening
        :param sync: (optional) if to sync with the webserver or not
        """
        self.dataLock.acquire()
        serverID="%s:%d" % (ip,port)
        foamLogger("server").info("Deregistering: %s with PID: %d" % (serverID,pid))

        try:
            if self.servers.has_key(serverID):
                self.servers.pop(serverID)

                if DO_WEBSYNC and sync:
                    foamLogger("server").info("Deregistering %s from webserver: %s" % (serverID,'end/%(ip)s/%(port)s/' % {'ip':ip, 'port':port}))
                    try:
                        self.webserver.end_process(ip, port)
                    except:
                        foamLogger("server").warning("Deregistering %s from webserver failed" % (serverID))
            else:
                foamLogger("server").warning("Server "+serverID+" not registered")
        except:
            foamLogger("server").error("Deregistering Server "+serverID+" failed:"+str(sys.exc_info()[0]))
            foamLogger("server").error("Reason:"+str(sys.exc_info()[1]))
            foamLogger("server").error("Trace:"+str(extract_tb(sys.exc_info()[2])))

        self.dataLock.release()

        return True

    def forwardCommand(self,ip,port,cmd):
        """Forwards a RPC to another machine
        :param ip: IP of the server
        :param port: the port at which the server is listening
        :param cmd: the command that should be executed there
        :return: the result of the command
        """
        result=""
        try:
            server=getServerProxy(ip,port)
            result=eval("server."+cmd)
            foamLogger("server").debug("Forwarding to "+ip+"the command\""+cmd+"\" Result:"+str(result))
        except Fault as reason:
            result="Fault: "+str(reason)
        except socket.error as reason:
            result="socket.error: "+str(reason)
        except TypeError as reason:
            result="Type error: ",reason
        except SyntaxError as reason:
            result="Syntax Error in:"+cmd

        if result==None:
            result=""

        return result

class ServerInfo(object):
    """Contains the information about a server"""
    def __init__(self,ip,pid,port,ssl=False):
        """
        :param ip: IP of the server
        :param pid: Die PID at the server
        :param port: the port at which the server is listening
        """
        self._info={}
        self._info["ip"]=ip
        if PY3 and type(ip)==binary_type:
            self._info["ip"]=ip.decode()
        self._info["pid"]=pid
        self._info["port"]=port
        self._info["ssl"]=ssl

    def checkValid(self):
        """Check with server whether this data item is still valid"""
        result=False

        foamLogger("server").debug("Checking "+self["ip"]+"@"+str(self["port"]))

        try:
            server=getServerProxy(self["ip"],self["port"])
            pid=server.pid()
            if pid==self["pid"]:
                result=True
        except socket.timeout as reason:
            foamLogger("server").info(self["ip"]+"@"+str(self["port"])+" seems to be dead")
        except:
            foamLogger("server").debug("Checking Valid "+self["ip"]+" failed:"+str(sys.exc_info()[0]))
            foamLogger("server").debug("Reason:"+str(sys.exc_info()[1]))
            foamLogger("server").debug("Trace:"+str(extract_tb(sys.exc_info()[2])))

        foamLogger("server").debug("Result for "+self["ip"]+"@"+str(self["port"])+" = "+str(result))

        return result

    def queryData(self):
        """Ask the server for additional data"""
        server=getServerProxy(self["ip"],self["port"],useSSL=self["ssl"])
        for name in ["commandLine","cwd","foamVersion","isParallel","mpi","pyFoamVersion","scriptName","user","hostname"]:
            if server is not None:
                result=eval("server."+name+"()")
            else:
                result="no info"
            self[name]=result

    def __getitem__(self,key):
        return self._info[key]

    def __setitem__(self,key,value):
        self._info[key]=value

class MetaChecker(Thread):
    """Checks regularily whether the registered Servers are still alive"""
    def __init__(self,parent):
        """:param parent: the FoamMetaServer that gets the information"""
        Thread.__init__(self)
        self.parent=parent
        self.sleepTime=config().getfloat("Metaserver","checkerSleeping")
        self.syncTimes={}

    def run(self):
        foamLogger("server").info("Checker starting")
        while True:
            self.parent.startupLock.acquire()
            foamLogger("server").debug("Start Checking")

            self.parent.dataLock.acquire()
            servers=copy.deepcopy(self.parent.servers)
            self.parent.dataLock.release()

            for key,obj in servers.iteritems():
                isOK=obj.checkValid()
                if not isOK:
                    foamLogger("server").info("Server "+key+" not OK. Deregistering")
                    self.parent.deregisterServer(obj["ip"],obj["pid"],obj["port"])
                elif DO_WEBSYNC:
                    if not self.syncTimes.has_key(key):
                        self.syncTimes[key]=self.sleepTime

                    if self.syncTimes[key] >= WEBSYNC_INTERVAL:
                        self.syncTimes[key]=self.sleepTime
                        foamLogger("server").debug("Refreshing "+key+" on Webserver")
                        try:
                            self.parent.webserver.refresh(obj['ip'], obj['port'])
                        except socket.timeout as e:
                            pass
                        except:
                            foamLogger("server").warning("Unknown exception "+str(sys.exc_info()[0])+" while syncing with webserver %s" % (WEBSERVER_RPCURL))
                    else:
                        self.syncTimes[key] += self.sleepTime

            foamLogger("server").debug("Stop Checking - sleeping")
            self.parent.startupLock.release()
            time.sleep(self.sleepTime)

class MetaCollector(Thread):
    """Scans the net in a separate thread"""
    def __init__(self,parent,additional=None):
        """:param parent: the FoamMetaServer that gets the information
        :param additional: A string with alist of additional subnets that should be scanned"""
        Thread.__init__(self)
        self.parent=parent
        self.additional=additional

    def run(self):
        self.parent.startupLock.acquire()
        foamLogger("server").info("Collector starting")

        if DO_WEBSYNC:
            foamLogger("server").info("Get Processes from Webserver")
            try:
                webserver = ServerProxy(WEBSERVER_RPCURL)
                for ip,port,pid in webserver.running_processes():
                    port = int(port)
                    try:
                        server=getServerProxy(ip,port)
                        pid=server.pid()  # occasional errors with 'Connection refused'
                        self.parent._registerServer(ip,pid,port,sync=False)
                    except:
                        foamLogger("server").error("Unknown exception "+str(sys.exc_info()[0])+" while registering %s:%s" % (ip, port))
                        foamLogger("server").error("Reason:"+str(sys.exc_info()[1]))
                        foamLogger("server").error("Trace:"+str(extract_tb(sys.exc_info()[2])))
            except:
                foamLogger("server").warning("Unknown exception "+str(sys.exc_info()[0])+" while syncing with webserver %s" % (WEBSERVER_RPCURL))

        port=config().getint("Network","startServerPort")
        length=config().getint("Network","nrServerPorts")

        machines=config().get("Metaserver","searchservers")

        addreses=machines.split(',')
        if self.additional!=None:
            addreses=self.additional.split(',')+addreses

        for a in addreses:
            foamLogger("server").info("Collecting in subnet "+a)
            for host in IP(a):
                try:
                    name,alias,rest =socket.gethostbyaddr(str(host))
                except socket.herror as reason:
                    # no name for the host
                    name="unknown"

                foamLogger("server").debug("Collector Checking:"+str(host)+" "+name)

                result=None
                try:
                    result=checkFoamServers(str(host),port,length)
                except:
                    foamLogger("server").error("Unknown exception "+str(sys.exc_info()[0])+" while checking for new servers"+str((str(host),port,length)))
                    foamLogger("server").error("Reason:"+str(sys.exc_info()[1]))
                    foamLogger("server").error("Trace:"+str(extract_tb(sys.exc_info()[2])))

                if result!=None:
                    foamLogger("server").debug("Collector Found "+str(result)+" for "+name)
                    for p in result:
                        try:
                            server=getServerProxy(str(host),p)
                            ip=server.ip()
                            pid=server.pid()
                            self.parent._registerServer(ip,pid,p)
                        except:
                            foamLogger("server").error("Unknown exception "+str(sys.exc_info()[0])+" while registering "+name)
                            foamLogger("server").error("Reason:"+str(sys.exc_info()[1]))
                            foamLogger("server").error("Trace:"+str(extract_tb(sys.exc_info()[2])))
                else:
                    foamLogger("server").debug("Collector Found "+str(result)+" for "+name)

        self.parent.startupLock.release()

        foamLogger("server").info("Collector finished")
