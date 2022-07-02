"""Lists the running pyFoam-Processes"""

from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam import configuration as config
from PyFoam.ThirdParty.six import print_,iteritems
from PyFoam.Infrastructure.ZeroConf import getServerList
from PyFoam.Infrastructure.ServerBase import getServerProxy

import socket,sys,time
from PyFoam.ThirdParty.six import PY3

if PY3:
    from xmlrpc.server import Fault
    from xmlrpc.client import ProtocolError
else:
    from xmlrpclib import ProtocolError

from optparse import OptionGroup

class NetList(PyFoamApplication):
    def __init__(self):
        description="""\
Lists all the processes known to a meta-server
        """
        self.defaultHost=config().get("Metaserver","ip")
        self.defaultPort=config().getint("Metaserver","port")
        self.defaultTimeout=config().getfloat("Network","zeroconfTimeout")

        PyFoamApplication.__init__(self,description=description,usage="%prog [options]",interspersed=True,nr=0)

    def addOptions(self):
        spec=OptionGroup(self.parser,
                         "Source Specification",
                         "Where we get the info about the processes from")
        self.parser.add_option_group(spec)
        spec.add_option("--no-zeroconf",
                        action="store_false",
                        dest="zeroconf",
                        default=True,
                        help="Don't get the server info via ZeroConf. Requires correct settings of --server and --port. DEPRECATED")
        spec.add_option("--server",
                        type="string",
                        dest="server",
                        default=self.defaultHost,
                        help="The server that should be queried (Default: "+self.defaultHost+")")
        spec.add_option("--port",
                        type="int",
                        dest="port",
                        default=self.defaultPort,
                        help="The port at which the query takes place (Default: "+str(self.defaultPort)+")")
        spec.add_option("--zeroconf-wait",
                        type="float",
                        dest="timeout",
                        default=self.defaultTimeout,
                        help="How many seconds to wait for zeroconf-info. Default: %default (set with configuration 'Network/zeroconfTimeout')")
        spec.add_option("--debug-zeroconf",
                        action="store_true",
                        dest="debugZeroconf",
                        default=False,
                        help="Output additional info about ZeroConf")

        spec.add_option("--no-progress-zeroconf",
                        action="store_false",
                        dest="progressZeroconf",
                        default=True,
                        help="Do not output progress information when looking for servers")

        what=OptionGroup(self.parser,
                         "What",
                         "What should be listed")
        self.parser.add_option_group(what)
        what.add_option("--dump",
                        action="store_true",
                        dest="dump",
                        default=False,
                        help="Dump all the statically stored data")
        what.add_option("--process",
                        action="store_true",
                        dest="process",
                        default=False,
                        help="Additional data about the process")
        what.add_option("--time",
                        action="store_true",
                        dest="time",
                        default=False,
                        help="Request timing information")
        what.add_option("--resources",
                        action="store_true",
                        dest="resources",
                        default=False,
                        help="Reports the amount of memory used and the current load on the maching")
        what.add_option("--ip",
                        action="store_true",
                        dest="ip",
                        default=False,
                        help="Output the IP-number instead of the machine name")
        what.add_option("--user",
                        action="store",
                        dest="user",
                        default=None,
                        help="Only show runs that belong to a certain username")

    def run(self):
        from PyFoam.Infrastructure.Authentication import ensureKeyPair
        ensureKeyPair()

        if self.opts.zeroconf:
            data=getServerList(self.opts.timeout,
                               verbose=self.opts.debugZeroconf,
                               progress=self.opts.progressZeroconf)
        else:
            self.warning("Using the old method of querying the meta-server. This is deprecated")
            try:
                self.server=getServerProxy(self.parser.options.server,self.parser.options.port)
                data=self.server.list()
            except socket.error as reason:
                print_("Socket error while connecting:",reason)
                sys.exit(1)
            except ProtocolError as reason:
                print_("XMLRPC-problem",reason)
                sys.exit(1)

        if len(data)==0:
            self.warning("No runs found")
            return

        hostString="Hostname"
        maxhost=len(hostString)
        cmdString="Command Line"
        maxcommandline=len(cmdString)

        for name,info in iteritems(data):
            if len(info["commandLine"])>maxcommandline:
                maxcommandline=len(info["commandLine"])
            if self.opts.ip:
                tmpHost=info["ip"]
            else:
                tmpHost=info["hostname"]
                if tmpHost=="no info":
                    tmpHost=info["ip"]
            if len(tmpHost)>maxhost:
                maxhost=len(tmpHost)

        header=hostString+(" "*(maxhost-len(hostString)))+" | "+" Port  | User       | "+cmdString+"\n"
        line=("-"*(len(header)))
        header+=line

        formatString="%-"+str(maxhost)+"s | %6d | %10s | %s"
        print_(header)

        for name,info in iteritems(data):
            if self.opts.user:
                if self.opts.user!=info["user"]:
                    continue

            if self.opts.ip:
                tmpHost=info["ip"]
            else:
                tmpHost=info["hostname"]
                if tmpHost=="no info":
                    tmpHost=info["ip"]

            print_(formatString % (tmpHost,info["port"],info["user"],info["commandLine"]))
            if self.parser.options.process:
                isParallel=self.forwardCommand(info,"isParallel()")
                if isParallel:
                    pidString="CPUs: %5d" % self.forwardCommand(info,"procNr()")
                else:
                    pidString="PID: %6d" % info["pid"]
                print_("  %s   Working dir: %s" % (pidString,info["cwd"]))
            if self.parser.options.time:
                startTime=self.forwardCommand(info,"startTime()")
                endTime=self.forwardCommand(info,"endTime()")
                createTime=self.forwardCommand(info,"createTime()")
                nowTime=self.forwardCommand(info,"time()")
                try:
                    progress=(nowTime-createTime)/(endTime-createTime)
                except ZeroDivisionError:
                    progress=0

                try:
                    progress2=(nowTime-startTime)/(endTime-startTime)
                except ZeroDivisionError:
                    progress2=0

                print_("  Time: %g Timerange: [ %g , %g ]  Mesh created: %g -> Progress: %.2f%% (Total: %.2f%%)" % (nowTime,startTime,endTime,createTime,progress*100,progress2*100))

                wallTime=self.forwardCommand(info,"wallTime()")
                now=time.time()
                start=now-wallTime
                startString=time.strftime("%Y-%b-%d %H:%M",time.localtime(start))
                try:
                    estimate=start+wallTime/progress
                    estimateString=time.strftime("%Y-%b-%d %H:%M",time.localtime(estimate))
                except ZeroDivisionError:
                    estimate=start
                    estimateString=" - NaN - "

                print_("  Started: %s   Walltime: %8gs  Estimated End: %s" % (startString,wallTime,estimateString))

            if self.opts.resources:
                mem=self.forwardCommand(info,"usedMemory()")
                loads=self.forwardCommand(info,"loadAvg()")
                loadString=""
                try:
                    if len(loads)==3:
                        loadString="  Load 1m: %.1f - 5m: %.1f - 15m: %.1f" % tuple(loads)
                except TypeError:
                    loadString="  Load: "+str(loads)
                print(("   Max memory: %f MB" % mem)+loadString)
            if self.parser.options.process or self.parser.options.time:
                print_(line)
            if self.parser.options.dump:
                print_(info)
                print_(line)

    def forwardCommand(self,info,cmd):
        """Forwards a command
        :param info: dictionary with the information
        :param cmd: the command that will be forwarded
        """
        result=0

        try:
            if self.opts.zeroconf:
                server=getServerProxy(info["ip"],info["port"])
                result=eval("server."+cmd)
            else:
                result=float(self.server.forwardCommand(info["ip"],info["port"],cmd))
        except:
            pass

        return result
