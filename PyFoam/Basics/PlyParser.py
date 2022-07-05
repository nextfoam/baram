#  ICE Revision: $Id$
"""Base class for all parser classes based on PLY

Most of this class was shamelessly stolen from the examples"""

import sys
from PyFoam.Error import PyFoamException

if sys.version_info < (2,3):
    raise PyFoamException("Version "+str(sys.version_info)+" is not sufficient for ply (2.3 needed)")

import PyFoam.ThirdParty.ply.lex as lex
import PyFoam.ThirdParty.ply.yacc as yacc

import os

from PyFoam.FoamInformation import getUserTempDir

class PlyParser(object):
    """
    Base class for a lexer/parser that has the rules defined as methods
    """
    tokens = ()
    precedence = ()


    def __init__(self, **kw):
        """Constructs the parser and the lexer"""
        self.debug = kw.get('debug', 2)
        self.names = { }
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" + self.__class__.__name__
        except:
            modname = "parser"+"_"+self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"
        #print self.debugfile, self.tabmodule

        # Build the lexer and parser
        lex.lex(module=self, debug=self.debug)
        yacc.yacc(module=self,
                  debug=self.debug,
                  debugfile=self.debugfile,
                  tabmodule=self.tabmodule,
                  outputdir=getUserTempDir(),
                  check_recursion=self.debug)
        self.lex=lex
        self.yacc=yacc

    def parse(self,content):
        """Do the actual parsing
        :param content: String that is to be parsed
        :return: Result of the parsing"""

        if self.debug:
            debug=10
        else:
            debug=0

        return yacc.parse(content,debug=debug)
