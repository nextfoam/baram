#  ICE Revision: $Id$
"""Basis for the XMLRPC-Servers in PyFoam

Based on 15.5 in "Python Cookbook" for faster restarting

SSL-handling lifted from
http://blogs.blumetech.com/blumetechs-tech-blog/2011/06/python-xmlrpc-server-with-ssl-and-authentication.html

"""

from PyFoam.ThirdParty.six import PY3
from PyFoam.Error import warning
from PyFoam import configuration as config
import PyFoam.Infrastructure.Authentication as auth
from PyFoam.FoamInformation import getUserName

if PY3:
    from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCDispatcher, SimpleXMLRPCRequestHandler
    from xmlrpc.client import ServerProxy
else:
    from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCDispatcher, SimpleXMLRPCRequestHandler
    from xmlrpclib import ServerProxy

import socket
from os import path

class ServerBase(SimpleXMLRPCServer):
    """The Base class for the servers"""
    def __init__(self,addr,useSSL=False,logRequests=False,
                 allow_none=False, encoding=None):
        """:param addr: the (server address,port)-tuple)
        :param logRequests: patched thru to the base class"""
        certfile=config().get("Network","personalSSLCertificate")
        keyfile=config().get("Network","privateSSLKey")
        self.useSSL=useSSL
        if self.useSSL and not path.exists(certfile):
            warning("No certficate file",certfile,
                    "exists. Therefor no SSL-connection for the FoamServer possible\n",
                    "To generate a private key:\n",
                    ("   openssl genrsa -out %s 2048" % keyfile),
                    "\nThen generate the cerificate that is valid for 3 years with \n",
                    ("   openssl req -new -x509 -key %s -out %s -days 1095" % (keyfile,certfile)))
            self.useSSL=False
        self.authOK=True

        if self.useSSL:
            try:
                import ssl
                if PY3:
                    import socketserver
                else:
                    import SocketServer as socketserver
                import socket
            except ImportError:
                warning("Problem with the imports. Dropping SSL-support")
                self.useSSL=False

        if self.useSSL:
            self.logRequests = logRequests

            SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding)

            class VerifyingRequestHandler(SimpleXMLRPCRequestHandler):
                '''
                Request Handler that verifies username and security token to
                XML RPC server in HTTP URL sent by client.
                '''
                # this is the method we must override
                def parse_request(self):
                    # first, call the original implementation which returns
                    # True if all OK so far

                    if SimpleXMLRPCRequestHandler.parse_request(self):
                        # next we authenticate
                        if self.authenticate(self.headers):
                            return True
                        else:
                            # if authentication fails, tell the client
                            self.send_error(401, 'Authentication failed')
                    return False

                def authenticate(self, headers):
                    from base64 import b64decode
                    #    Confirm that Authorization header is set to Basic
                    authHeader=headers.get('Authorization')
                    if authHeader is None:
                        return True
                    (basic, _, encoded) = authHeader.partition(' ')
                    assert basic == 'Basic', 'Only basic authentication supported'
                    #    Encoded portion of the header is a string
                    #    Need to convert to bytestring
                    encodedByteString = encoded.encode()
                    #    Decode Base64 byte String to a decoded Byte String
                    decodedBytes = b64decode(encodedByteString)
                    #    Convert from byte string to a regular String
                    decodedString = decodedBytes.decode()
                    #    Get the username and password from the string
                    (username, _, password) = decodedString.partition(':')
                    #    Check that username and password match internal global dictionary
                    self.server.authOK=auth.checkAuthentication(username,password)
                    return True
            #    Override the normal socket methods with an SSL socket
            socketserver.BaseServer.__init__(self, addr, VerifyingRequestHandler)
            try:
                self.socket = ssl.wrap_socket(
                    socket.socket(self.address_family, self.socket_type),
                    server_side=True,
                    keyfile=keyfile,
                    certfile=certfile,
                    cert_reqs=ssl.CERT_NONE,
                    ssl_version=ssl.PROTOCOL_SSLv23,
                )
                self.server_bind()
                self.server_activate()
            except socket.error as e:
                warning("Socket error",e)
                raise e
        else:
            SimpleXMLRPCServer.__init__(self,addr,logRequests=logRequests)

    def server_bind(self):
        """Should allow a fast restart after the server was killed"""
        self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        SimpleXMLRPCServer.server_bind(self)

    def verify_request(self,request,client_addr):
        """To be overriden later"""
        return True

def getServerProxy(host,port,useSSL=None):
    """Get a proxy to a server. If the useSSL-parameter is unset then it
    tries to automatically get the most secure connection"""

    if useSSL is None:
        useSSL=[True,False]
    else:
        useSSL=[useSSL]

    for s in useSSL:
        if s:
            try:
                import ssl
                import socket
                import uuid
                context=None
                if config().getboolean("Network","allowSelfSignedSSL"):
                    try:
                        context=ssl._create_unverified_context()
                    except AttributeError:
                        pass
                try:
                    user=getUserName()
                    # user="nix"
                    challenge=auth.createChallengeString(str(uuid.uuid4()))
                    try:
                        server=ServerProxy("https://%s:%s@%s:%d" % (user,challenge,
                                                                host,port),
                                           context=context)
                    except TypeError:
                        server=ServerProxy("https://%s:%s@%s:%d" % (user,challenge,
                                                                    host,port))
                    server.system.listMethods()   # provoke a socket-error
                    return server
                except socket.error as reason:
                    if hasattr(reason,"reason"):
                        if reason.reason=="CERTIFICATE_VERIFY_FAILED" and context is None:
                            warning("Can't verify certificate. Set setting 'network'/'allowSelfSignedSSL' to True. This may be insecure")
                            raise reason
            except ImportError:
                warning("Problem with the imports. Dropping SSL-support")
        else:
            return ServerProxy("http://%s:%d" % (host,port))


    warning("Could not connect to",host,"at",port)
    return None

# Should work with Python3 and Python2
