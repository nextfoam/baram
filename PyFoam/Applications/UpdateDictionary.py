#  ICE Revision: $Id$
"""
Application class that implements pyFoamUpdateDictionary.py
"""

import sys

from os import path

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Basics.DataStructures import DictProxy,TupleProxy

from PyFoam.Error import error,warning

from .CommonParserOptions import CommonParserOptions

from PyFoam.Basics.TerminalFormatter import TerminalFormatter

from PyFoam.ThirdParty.six import print_
from PyFoam.ThirdParty.six.moves import input

f=TerminalFormatter()
f.getConfigFormat("source",shortName="src")
f.getConfigFormat("destination",shortName="dst")
f.getConfigFormat("difference",shortName="diff")
f.getConfigFormat("question",shortName="ask")
f.getConfigFormat("input")

class UpdateDictionary(PyFoamApplication,
                       CommonParserOptions):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Takes two dictionary and modifies the second one after the example of
the first. If the dictionaries do not have the same name, it looks for
the destination file by searching the equivalent place in the
destination case
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <source> <destination-case>",
                                   nr=2,
                                   changeVersion=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("--interactive",
                               action="store_true",
                               default=True,
                               dest="interactive",
                               help="Asks the user before applying changes")

        self.parser.add_option("--batch",
                               action="store_false",
                               default=True,
                               dest="interactive",
                               help="Don't ask the user before applying changes")

        self.parser.add_option("--clear-unused",
                               action="store_true",
                               default=False,
                               dest="clear",
                               help="Removes all the dictionary entries that are not in the source")

        self.parser.add_option("--add-missing",
                               action="store_true",
                               default=False,
                               dest="add",
                               help="Add all the dictionary entries that are not in the destination")

        self.parser.add_option("--append-lists",
                               action="store_true",
                               default=False,
                               dest="append",
                               help="Append to lists if they are shorter than the original")

        self.parser.add_option("--shorten-lists",
                               action="store_true",
                               default=False,
                               dest="shorten",
                               help="Shortens lists if they are longer than the original")

        self.parser.add_option("--all",
                               action="store_true",
                               default=False,
                               dest="all",
                               help="Do all the editing commands: clear, add, shorten and append")

        self.parser.add_option("--test",
                               action="store_true",
                               default=False,
                               dest="test",
                               help="Does not write the file but only prints it to the screen")

        self.parser.add_option("--not-equal",
                               action="store_true",
                               default=False,
                               dest="notequal",
                               help="Allow source and destination to have different names")

        self.parser.add_option("--verbose",
                               action="store_true",
                               default=False,
                               dest="verbose",
                               help="Print every change that is being made")

        self.parser.add_option("--min-recursion",
                               action="store",
                               default=0,
                               type="int",
                               dest="min",
                               help="Minimum depth of the recursive decent into dictionaries at which 'editing' should start (default: %default)")

        self.parser.add_option("--max-recursion",
                               action="store",
                               default=100,
                               type="int",
                               dest="max",
                               help="Maximum depth of the recursive decent into dictionaries (default: %default)")

        CommonParserOptions.addOptions(self)

    def ask(self,*question):
        if not self.opts.interactive:
            return False
        else:
            print_(f.ask,"QUESTION:",end="")
            for q in question:
                print_(q,end="")

            answer=None
            while answer!="y" and answer!="n":
                answer=input(f.reset+f.ask+"   [Y]es or [N]no ? "+f.input).strip()[0].lower()
            print_(f.reset,end="")
            return answer=="y"

    def workList(self,source,dest,depth):
        if depth>self.opts.max:
            if self.opts.verbose:
                print_("- "*depth,"Recursion ended")
            return

        for i in range(min(len(source),len(dest))):
            if type(source[i])==type(dest[i]) and type(source[i]) in  [dict,DictProxy]:
                if self.opts.verbose:
                    print_("- "*depth,"Entering dict nr.",i)
                self.workDict(source[i],dest[i],depth+1)
                if self.opts.verbose:
                    print_("- "*depth,"Leaving dict nr.",i)
            elif type(source[i])==type(dest[i]) and type(source[i]) in [tuple,TupleProxy,list]:
                if self.opts.verbose:
                    print_("- "*depth,"Entering tuple nr.",i)
                self.workList(source[i],dest[i],depth+1)
                if self.opts.verbose:
                    print_("- "*depth,"Leaving tuple nr.",i)
            elif self.opts.interactive:
                if source[i]!=dest[i]:
                    if self.ask("Replace for index",i,"the value",dest[i],"with the value",source[i]):
                        dest[i]=source[i]

        if len(source)<len(dest) and self.opts.shorten:
            if self.ask("Clip [",len(source),":] with the values ",dest[len(source):],"from the list"):
                if self.opts.verbose:
                    print_("- "*depth,"Clipping",len(dest)-len(source),"entries starting with",len(source))
                dest=dest[0:len(source)]
        elif len(source)>len(dest) and self.opts.append:
            if self.ask("Append [",len(dest),":] with the values ",source[len(dest):],"to the list"):
                if self.opts.verbose:
                    print_("- "*depth,"Appending",len(source)-len(dest),"entries starting with",len(dest))
                dest+=source[len(dest):]

    def workDict(self,source,dest,depth):
        if depth>self.opts.max:
            if self.opts.verbose:
                print_("- "*depth,"Recursion ended")
            return

        if depth>=self.opts.min:
            doIt=True
        else:
            doIt=False

        for name in source:
            if name not in dest:
                if self.opts.add and doIt:
                    if self.ask("Add the key",name,"with value",source[name]):
                        if self.opts.verbose:
                            print_("- "*depth,"Adding",name)
                        dest[name]=source[name]
            elif type(source[name]) in [dict,DictProxy]:
                if type(dest[name]) not in [dict,DictProxy]:
                    error("Entry",name,"is not a dictionary in destination (but in source)")
                if self.opts.verbose:
                    print_("- "*depth,"Entering dict ",name)
                self.workDict(source[name],dest[name],depth+1)
                if self.opts.verbose:
                    print_("- "*depth,"Leaving dict ",name)
            elif type(source[name])==type(dest[name]) and type(dest[name]) in [tuple,TupleProxy,list]:
                if self.opts.verbose:
                    print_("- "*depth,"Entering tuple ",name)
                self.workList(source[name],dest[name],depth+1)
                if self.opts.verbose:
                    print_("- "*depth,"Leaving tuple ",name)
            elif self.opts.interactive:
                if source[name]!=dest[name]:
                    if self.ask("Replace for key",name,"the value",dest[name],"with the value",source[name]):
                        dest[name]=source[name]
            else:
                if self.opts.verbose:
                    print_("- "*depth,"Nothing done for",name)

        if self.opts.clear and doIt:
            weg=[]
            for name in dest:
                if name not in source:
                    weg.append(name)

            for name in weg:
                if self.ask("Remove the key",name,"with the value",dest[name]):
                    if self.opts.verbose:
                        print_("- "*depth,"Removing",name)
                    del dest[name]

    def run(self):
        sName=path.abspath(self.parser.getArgs()[0])
        dName=path.abspath(self.parser.getArgs()[1])

        if self.opts.all:
            self.opts.append=True
            self.opts.shorten=True
            self.opts.add=True
            self.opts.clear=True

        try:
            source=ParsedParameterFile(sName,
                                       backup=False,
                                       debug=self.opts.debugParser,
                                       noBody=self.opts.noBody,
                                       noHeader=self.opts.noHeader,
                                       boundaryDict=self.opts.boundaryDict,
                                       listDict=self.opts.listDict,
                                       listDictWithHeader=self.opts.listDictWithHeader)
        except IOError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.error("Problem with file",sName,":",e)

        if not self.opts.notequal and path.basename(sName)!=path.basename(dName):
            found=False
            parts=sName.split(path.sep)
            for i in range(len(parts)):
                tmp=path.join(*[dName]+parts[-(i+1):])

                if path.exists(tmp):
                    found=True
                    dName=tmp
                    warning("Found",dName,"and using this")
                    break

            if not found:
                error("Could not find a file named",path.basename(sName),"in",dName)

        if path.samefile(sName,dName):
            error("Source",sName,"and destination",dName,"are the same")

        try:
            dest=ParsedParameterFile(dName,
                                     backup=False,
                                     debug=self.opts.debugParser,
                                     noBody=self.opts.noBody,
                                     noHeader=self.opts.noHeader,
                                     boundaryDict=self.opts.boundaryDict,
                                     listDict=self.opts.listDict,
                                     listDictWithHeader=self.opts.listDictWithHeader)
        except IOError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            self.error("Problem with file",dName,":",e)

        dCase=dest.getCaseDir()

        if self.opts.interactive:
            self.opts.verbose=True

        if not self.opts.boundaryDict and not self.opts.listDict and not self.opts.listDictWithHeader:
            self.workDict(source.content,dest.content,1)
        else:
            self.workList(source.content,dest.content,1)

        if self.opts.test or self.opts.interactive:
            print_(str(dest))

        if not self.opts.test and self.ask("\n Write this file to disk"):
            dest.writeFile()
            if dCase!=None:
                self.addToCaseLog(dCase,"Source",sName,"Destination:",dName)

# Should work with Python3 and Python2
