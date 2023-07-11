#  ICE Revision: $Id$
"""Standardized Error Messages"""

import traceback
import sys

from PyFoam.Basics.TerminalFormatter import TerminalFormatter
from PyFoam.ThirdParty.six import print_

defaultFormat=TerminalFormatter()
defaultFormat.getConfigFormat("error")
defaultFormat.getConfigFormat("warning",shortName="warn")

def getLine(up=0):
     try:  # just get a few frames
         f = traceback.extract_stack(limit=up+2)
         if f:
            return f[0]
     except:
         if __debug__:
             traceback.print_exc()
             pass
         return ('', 0, '', None)

def isatty(s):
     """Workaround for outputstreams that don't implement isatty
     (specifically vtkPythonStdStreamCaptureHelper)
     """
     try:
          return s.isatty
     except AttributeError:
          return False

def __common(format,standard,*text):
    """Common function for errors and Warnings"""
    info=getLine(up=2)

    isTerm=isatty(sys.stderr)

    if format and isTerm:
         print_(format, end=' ', file=sys.stderr)
    print_("PyFoam",standard.upper(),"on line",info[1],"of file",info[0],":", end=' ', file=sys.stderr)
    for t in text:
         print_(t, end=' ', file=sys.stderr)

    if isTerm:
        print_(defaultFormat.reset, file=sys.stderr)

def warning(*text):
    """Prints a warning message with the occuring line number
    :param text: The error message"""
    __common(defaultFormat.warn,"Warning",*text)

def oldSchoolError(*text):
    """Prints an error message and aborts
    :param text: The error message"""
    __common(defaultFormat.error,"Fatal Error",*text)
    sys.exit(-1)

def error(*text):
    """Raises an error that might or might not get caught
    :param text: The error message"""
    #    __common(defaultFormat.error,"Fatal Error",*text)
    raise FatalErrorPyFoamException(*text)

def debug(*text):
    """Prints a debug message with the occuring line number
    :param text: The error message"""
    __common(None,"Debug",*text)

def notImplemented(obj,name):
     """Prints a 'not implemented' message for abstract interfaces
     :param obj: the object for which the method is not defined
     :param name: name of the method"""
     error("The method",name,"is not implemented in this object of type",obj.__class__)

class PyFoamException(Exception):
     """The simplest exception for PyFoam"""

     def __init__(self,*text):
          self.descr=text[0]
          for t in text[1:]:
               self.descr+=" "+str(t)

     def __str__(self):
          return "Problem in PyFoam: '"+self.descr+"'"

class FatalErrorPyFoamException(PyFoamException):
     """The PyFoam-exception that does not expect to be caught"""

     def __init__(self, *text, **kwargs):
          # Up reports how many levels of the stack-trace should be
          # discarded. 2 usually is the place where the exception was raised
          up = kwargs.get("up", 2) # necessary because a up=2 in the definition does not work in python 2

          info=getLine(up=up)
          descr="PyFoam FATAL ERROR on line %d of file %s:" % (info[1],info[0])
          #          super(FatalErrorPyFoamException,self).__init__(descr,*text) # does not work with Python 2.4
          PyFoamException.__init__(self,descr,*text)

     def __str__(self):
          return "FatalError in PyFoam: '"+self.descr+"'"

# Should work with Python3 and Python2
