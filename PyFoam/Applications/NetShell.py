"""An interactive Shell that queries a pyFoamServer"""

from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam.ThirdParty.six import print_,PY3
from PyFoam.Infrastructure.ServerBase import getServerProxy

import readline,sys
from optparse import OptionGroup

import socket
if PY3:
    from xmlrpc.server import Fault
    from xmlrpc.client import ProtocolError
else:
    from xmlrpclib import ProtocolError,Fault

class NetShell(PyFoamApplication):
    prompt="PFNET> "

    def __init__(self):
        description="""\
Connects to a running pyFoam-Server and executes commands via remote
procedure calls
        """
        PyFoamApplication.__init__(self,description=description,usage="%prog <host> <port>",interspersed=True,nr=2)
    def addOptions(self):
        what=OptionGroup(self.parser,
                         "Command",
                         "Specify command")
        self.parser.add_option_group(what)

        what.add_option("--command",
                        type="string",
                        dest="command",
                        default=None,
                        help="Executes this command and finishes")

    def run(self):
        from PyFoam.Infrastructure.Authentication import ensureKeyPair
        ensureKeyPair()

        host=self.parser.getArgs()[0]
        port=int(self.parser.getArgs()[1])

        cmd=self.parser.options.command

        try:
            self.server=getServerProxy(host,port)
            methods=self.server.system.listMethods()
            if not cmd:
                print_("Connected to server",host,"on port",port)
                print_(len(methods),"available methods found")
        except socket.error as reason:
            print_("Socket error while connecting:",reason)
            sys.exit(1)
        except ProtocolError as reason:
            print_("XMLRPC-problem",reason)
            sys.exit(1)

        if cmd:
            result=self.executeCommand(cmd)
            if result!=None:
                print_(result)
            sys.exit(0)

        while 1:
            try:
                if PY3:
                    line = input(self.prompt)
                else:
                    line = raw_input(self.prompt)
            except (KeyboardInterrupt,EOFError):    # Catch a ctrl-D
                print_()
                print_("Goodbye")
                sys.exit()
            line.strip()
            parts=line.split()

            if len(parts)==0:
                print_("For help type 'help'")
                continue

            if parts[0]=="help":
                if len(parts)==1:
                    print_("For help on a method type 'help <method>'")
                    print_("Available methods are:")
                    for m in methods:
                        print_("\t",m)
                elif len(parts)==2:
                    name=parts[1]
                    if name in methods:
                        signature=self.executeCommand("system.methodSignature(\""+name+"\")")
                        help=self.executeCommand("system.methodHelp(\""+name+"\")")
                        print_("Method    : ",name)
                        print_("Signature : ",signature)
                        print_(help)
                    else:
                        print_("Method",name,"does not exist")
                else:
                    print_("Too many arguments")
            else:
                result=self.executeCommand(line)
                if result!=None:
                    print_(result)

    def executeCommand(self,cmd):
        result=None
        try:
            result=eval("self.server."+cmd)
            if result==None: # this needed to catch the unmarschalled-None-exception
                return None
        except Fault as reason:
            print_("XMLRPC-problem:",reason.faultString)
        except socket.error as reason:
            print_("Problem with socket (server propably dead):",reason)
        except TypeError as reason:
            print_("Type error: ",reason)
            result=None
        except SyntaxError as reason:
            print_("Syntax Error in:",cmd)

        return result
