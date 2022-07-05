#  ICE Revision: $Id$
"""Helpers for the networking functionality"""

import socket
import errno
import time

from PyFoam import configuration as config
from PyFoam.ThirdParty.six import print_,PY3

if PY3:
    import xmlrpc.client as xmlrpclib
else:
    import xmlrpclib

import xml,sys

def freeServerPort(start,length=1):
    """
    Finds a port that is free for serving
    :param start: the port to start with
    :param length: the number of ports to scan
    :return: number of the first free port, -1 if none is found
    """
    port=-1

    for p in range(start,start+length):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('',p))
        except socket.error:
            e = sys.exc_info()[1] # compatible with 2.x and 3.x
            if e.errno!=errno.EADDRINUSE:
                #                sock.shutdown(2)
                sock.close()
                raise
        else:
            #            sock.shutdown(2)
            sock.close()
            time.sleep(config().getfloat("Network","portWait")) # to avoid that the port is not available. Introduces possible race-conditons
            port=p
            break


    return port

def checkFoamServers(host,start,length=1):
    """
    Finds the port on a remote host on which Foam-Servers are running
    :param host: the IP of the host that should be checked
    :param start: the port to start with
    :param length: the number of ports to scan
    :return: a list with the found ports, None if the machine is unreachable
    """

    ports=[]

##    try:
##        name,alias,rest =socket.gethostbyaddr(host)
##    except socket.herror,reason:
##        # no name for the host
##        return None

    for p in range(start,start+length):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.setdefaulttimeout(config().getfloat("Network","socketTimeout"))
        ok=False
        try:
            sock.connect((host,p))
            sock.close()
        except socket.error:
            reason = sys.exc_info()[1] # compatible with 2.x and 3.x
            code=reason.errno
            if code in [errno.EHOSTUNREACH,errno.ENETUNREACH,errno.ETIMEDOUT] or code=="timed out" or code<0:
                # Host unreachable: no more scanning
                return None
            elif code==errno.ECONNREFUSED:
                # port does not exist
                continue
            else:
                print_(errno.errorcode[code])
                raise reason

        try:
            server=xmlrpclib.ServerProxy("http://%s:%d" % (host,p))
            ok=server.isFoamServer()
        except xmlrpclib.ProtocolError:
            pass
        except xml.parsers.expat.ExpatError:
            pass

        if ok:
            ports.append(p)

    return ports

# Should work with Python3 and Python2
