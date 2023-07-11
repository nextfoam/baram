"""Send an EMail to a specified address"""

import sys

from PyFoam.Infrastructure.RunHook import RunHook
from PyFoam.ThirdParty.six import PY3,iteritems,print_

from PyFoam.ThirdParty.six.moves import http_client as httplib

from PyFoam.Error import error
from PyFoam.Basics.TemplateFile import TemplateFile
from PyFoam.ThirdParty.pyratemp import TemplateRenderError

from email.message import Message
import smtplib

class MailToAddress(RunHook):
    """Sends an URL to a Webservice"""
    def __init__(self,runner,name):
        RunHook.__init__(self,runner,name)

        self.server=self.conf().get("smtpserver")
        self.sendTo=self.conf().get("to")
        self.sentFrom=self.conf().get("from")
        self.templates={}
        self.templates["subject"]=self.conf().get("subject")
        self.templates["message"]=self.conf().get("message")
        self.mailFields={}
        mf="mailfields_"
        for name,val in list(self.conf().items()):
            if name.find(mf)==0:
                self.mailFields[name[len(mf):]]=val

    def __call__(self):
        texts={}
        for n,val in iteritems(self.templates):
            template=TemplateFile(content=val,
                                  expressionDelimiter="|-",
                                  encoding="ascii")
            try:
                texts[n]=str(template.getString(self.runner.getData()))
            except TemplateRenderError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                error("Template error",e,"while rendering",val)


        msg=Message()
        msg["To"]=self.sendTo
        msg["From"]=self.sentFrom
        msg["Subject"]=texts["subject"]
        for n,v in iteritems(self.mailFields):
            msg[n]=v
        msg.set_payload(texts["message"])

        print_("Connecting to SMTP-server",self.server)

        try:
            s=smtplib.SMTP(self.server)
        except:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            error("Could not connect to",self.server,":",e)

        print_("Sending mail")
        r=s.sendmail(self.sentFrom,self.sendTo.split(","),msg.as_string())
        print_("\n",self.name,"Sent mail to",self.sendTo," Response:",r)

# not yet tested with python3