#  ICE Revision: $Id$ 
"""Formats the output on a terminal"""

import os

from PyFoam.Infrastructure.Configuration import Configuration as config

def getTerminalCode(code):
    result=""
    try:
        result=os.popen("tput "+code).read()
    except:
        pass
    return result

class TerminalFormatter(object):
    """Class that contains the formating codes for the terminal"""
    
    reset   =getTerminalCode("sgr0")

    bold    =getTerminalCode("bold")
    under   =getTerminalCode("smul")
    standout=getTerminalCode("smso")

    black   =getTerminalCode("setaf 0")
    red     =getTerminalCode("setaf 1")
    green   =getTerminalCode("setaf 2")
    cyan    =getTerminalCode("setaf 3")
    blue    =getTerminalCode("setaf 4")
    magenta =getTerminalCode("setaf 5")
    yellow  =getTerminalCode("setaf 6")
    white   =getTerminalCode("setaf 7")

    back_black   =getTerminalCode("setab 0")
    back_red     =getTerminalCode("setab 1")
    back_green   =getTerminalCode("setab 2")
    back_cyan    =getTerminalCode("setab 3")
    back_blue    =getTerminalCode("setab 4")
    back_magenta =getTerminalCode("setab 5")
    back_yellow  =getTerminalCode("setab 6")
    back_white   =getTerminalCode("setab 7")

    def buildSequence(self,specification):
        """Build an escape sequence from a specification string
        :param specification: the specification string that is a number
        of komma-separated words. The words specify the color and the
        formatting"""

        seq=""
        for s in specification.split(','):
            seq+=eval("self."+s)

        return seq

    def addFormat(self,name,specification):
        """Add a new format to the object
        :param name: Name under which the format is added to the formatter
        :param specification: The specification string for the format"""

        exec("self."+name+"=self.buildSequence('"+specification+"')")
        
    def getConfigFormat(self,name,shortName=None):
        """Gets a format sequence from the global configuration and adds it
        to the formatter object
        :param name: Name under which this is found in the 'Formats'-section
        of the configuration
        :param shortName: Short name under which this is stored in the
        foratter. If none is given the regular name is used"""

        spec=config().get("Formats",name,default="reset")
        nm=name
        if shortName:
            nm=shortName
        self.addFormat(nm,spec)
        
        
