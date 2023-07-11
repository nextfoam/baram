"""Helper classes and functions to wrap the zeroconf-library"""

try:
    import zeroconf as zc
    zeroConfOK=True
except ImportError:
    zeroConfOK=False

from PyFoam.Infrastructure.Logging import foamLogger
from PyFoam.Error import warning
from PyFoam.ThirdParty.six import print_,b
from PyFoam.Infrastructure.FoamMetaServer import ServerInfo

from os import path
from time import sleep
import socket

foamServerDescriptorString="_foamserver._tcp.local."

class ZeroConfFoamServer:
    def __init__(self):
        self.info=None
        if zeroConfOK:
            self.zero=zc.Zeroconf()

    def register(self,answerer,port,ssl):
        if not zeroConfOK:
            return

        desc = { 'host' : answerer.hostname(),
                 'ip'   : answerer.ip(),
                 'id'   : answerer.id(),
                 'pid'  : str(answerer.pid()),
                 'port' : str(port),
                 'ssl'  : str(ssl),
                 'path' : answerer.pathToSolution(),}
        if desc["host"].find(".")>0:
            shorthost=desc["host"][0:desc["host"].index(".")]
        else:
            shorthost=desc["host"]
        desc["name"]= "@"+shorthost+":"+desc["port"]+"."+ \
                      foamServerDescriptorString
        basename=path.basename(desc["path"]).replace(".","_")
        extraLen=63-len(desc["name"])
        if len(basename)>extraLen:
            desc["name"]=basename[0:extraLen].replace('.','')+desc["name"]
        else:
            desc["name"]=basename+desc["name"]
        self.info=zc.ServiceInfo(type_=foamServerDescriptorString,
                                 name=desc["name"],
                                 # name="Nix da."+foamServerDescriptorString,
                                 address=socket.inet_aton(answerer.ip()),
                                 port=port,
                                 weight=0,
                                 priority=0,
                                 properties=desc,
                                 server=desc["host"]+".")
        self.zero.register_service(self.info)

    def deregister(self):
        if not zeroConfOK:
            return

        if self.info:
            self.zero.unregister_service(self.info)
            self.info=None

def getServerList(timeout=5,verbose=False,progress=False):
    if not zeroConfOK:
        warning("zeroconf-module not installed.")
        return {}
    if verbose:
        progress=False

    zero=zc.Zeroconf()
    servers={}

    def on_service_state_change(zeroconf, service_type, name, state_change):
        if verbose:
            print_("Service %s of type %s state changed: %s" % (name, service_type, state_change))

        if state_change is zc.ServiceStateChange.Added:
            info = zero.get_service_info(service_type, name)

            if info:
                if verbose:
                    print_("  Address: %s:%d" % (socket.inet_ntoa(info.address), info.port))
                    print_("  Weight: %d, priority: %d" % (info.weight, info.priority))
                    print_("  Server: %s" % (info.server,))
                if info.properties:
                    if verbose:
                        print_("  Properties are:")
                        for key, value in info.properties.items():
                            print_("    %s: %s" % (key, value))
                    try:
                        new=ServerInfo(info.properties[b("ip")],
                                       int(info.properties[b("pid")]),
                                       int(info.properties[b("port")]),
                                       eval(info.properties[b("ssl")]) if b("ssl") in info.properties else False)
                        new.queryData()
                        servers[name]=new
                        if progress:
                            print_("+",flush=True,end="")
                    except socket.error:
                        warning("Connection refused by",new["ip"])
                else:
                    if verbose:
                        print_("  No properties")
            else:
                if verbose:
                    print_("  No info")
        elif state_change is zc.ServiceStateChange.Removed:
            if name in servers:
                if verbose:
                    print_("Remove",name)
                del servers[name]
                if progress:
                    print_("-",flush=True,end="")

    browser = zc.ServiceBrowser(zero,
                                foamServerDescriptorString,
                                handlers=[on_service_state_change])

    if progress:
        print_("Searching  ",flush=True,end="")

    while timeout>0:
        if progress:
            print_(" . ",flush=True,end="")
        timeout-=1
        sleep(1)

    zero.close()

    if progress:
        print_(" Done\n")

    return servers
