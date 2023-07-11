"""Call an URL from a webservice"""

import sys

from PyFoam.Infrastructure.RunHook import RunHook
from PyFoam.ThirdParty.six import PY3,iteritems,print_
if PY3:
    import urllib.parse as urllib
else:
    import urllib

import socket
from PyFoam.ThirdParty.six.moves import http_client as httplib

from PyFoam.Error import error
from PyFoam.Basics.TemplateFile import TemplateFile
from PyFoam.ThirdParty.pyratemp import TemplateRenderError

class SendToWebservice(RunHook):
    """Sends an URL to a Webservice"""
    def __init__(self,runner,name):
        RunHook.__init__(self,runner,name)

        self.host=self.conf().get("host")
        self.url=self.conf().get("url",default="")
        self.method=self.conf().get("method",default="POST")
        self.useSSL=self.conf().getboolean("useSSL",False)
        self.parameters={}
        for name,val in list(self.conf().items()):
            if name.find("param_")==0:
                self.parameters[name[len("param_"):]]=val
        self.headers={}
        for name,val in list(self.conf().items()):
            if name.find("header_")==0:
                self.headers[name[len("header_"):]]=val
        self.templates=self.conf().get("templates",default="").split()
        for t in self.templates:
            if t not in self.parameters:
                error("Tempalte parameter",t,"not in specified parameters",
                      self.parameters)

    def __call__(self):
        if self.useSSL:
            meth=httplib.HTTPSConnection
        else:
            meth=httplib.HTTPConnection

        conn=meth(self.host)

        parameters={}
        for n,val in iteritems(self.parameters):
            if n in self.templates:
                template=TemplateFile(content=val,
                                      expressionDelimiter="|-",
                                      encoding="ascii")
                try:
                    parameters[n]=str(template.getString(self.runner.getData()))
                except TemplateRenderError:
                    e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                    error("Template error",e,"while rendering",val)
            else:
                parameters[n]=val
        encoded=urllib.urlencode(parameters)
        try:
            conn.request(self.method,
                         self.url,
                         encoded,
                         self.headers)
        except socket.error:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            error("Could not connect to",self.host,":",e)

        result=conn.getresponse()
        print_("\n",self.name,"Result of request:",result.status,result.reason,result.read())

# Should work with Python3 and Python2
