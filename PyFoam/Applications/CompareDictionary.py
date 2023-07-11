#  ICE Revision: $Id$
"""
Application class that implements pyFoamCompareDictionary.py
"""

from os import path

import sys

from .PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile,PyFoamParserError
from PyFoam.Basics.DataStructures import DictProxy,Dimension,Tensor,SymmTensor,Vector,Field,TupleProxy,BoolProxy
from PyFoam.Basics.FoamFileGenerator import makeString

from PyFoam.Error import error,warning

from .CommonParserOptions import CommonParserOptions

from PyFoam.Basics.TerminalFormatter import TerminalFormatter

from PyFoam.ThirdParty.six import print_,integer_types

f=TerminalFormatter()
f.getConfigFormat("source",shortName="src")
f.getConfigFormat("destination",shortName="dst")
f.getConfigFormat("difference",shortName="diff")
f.getConfigFormat("error",shortName="name")

class CompareDictionary(PyFoamApplication,
                        CommonParserOptions):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Takes two dictionary and compares them semantically (by looking at the
structure, not the textual representation. If the dictionaries do not
have the same name, it looks for the destination file by searching the
equivalent place in the destination case. If more than two files are
specified then the last name is assumed to be a directory and all the
equivalents to the other files are searched there.
        """

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog [options] <source> <destination-case>",
                                   nr=2,
                                   exactNr=False,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("--not-equal",
                               action="store_true",
                               default=False,
                               dest="notequal",
                               help="Allow source and destination to have different names")
        self.parser.add_option("--debug",
                               action="store_true",
                               default=False,
                               dest="debug",
                               help="Debug the comparing process")
        self.parser.add_option("--significant-digits",
                               action="store",
                               type="int",
                               default=6,
                               dest="digits",
                               help="How many digits of the bigger number should be similar if two numbers are compared. Default: %default")
        self.parser.add_option("--long-field-threshold",
                               action="store",
                               type="int",
                               default=None,
                               dest="longlist",
                               help="Fields that are longer than this won't be parsed, but read into memory (and compared as strings). Default: unset")

        CommonParserOptions.addOptions(self)



    def run(self):
        sFiles=self.parser.getArgs()[0:-1]
        dFile=path.abspath(self.parser.getArgs()[-1])

        for s in sFiles:
            sName=path.abspath(s)
            dName=dFile

            if len(s)>1:
                print_(f.name+"Source file",sName,f.reset)
            try:
                source=ParsedParameterFile(sName,
                                           backup=False,
                                           debug=self.opts.debugParser,
                                           listLengthUnparsed=self.opts.longlist,
                                           noBody=self.opts.noBody,
                                           noHeader=self.opts.noHeader,
                                           boundaryDict=self.opts.boundaryDict,
                                           listDict=self.opts.listDict,
                                           listDictWithHeader=self.opts.listDictWithHeader)
            except IOError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.warning("Problem with file",sName,":",e)
                continue
            except PyFoamParserError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.warning("Parser problem with",sName,":",e)
                continue

            found=False

            if path.isfile(sName) and path.isfile(dName):
                found=True

            if not found and not self.opts.notequal and path.basename(sName)!=path.basename(dName):
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
                                         listLengthUnparsed=self.opts.longlist,
                                         noBody=self.opts.noBody,
                                         noHeader=self.opts.noHeader,
                                         boundaryDict=self.opts.boundaryDict,
                                         listDict=self.opts.listDict,
                                         listDictWithHeader=self.opts.listDictWithHeader)
            except IOError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.error("Problem with file",dName,":",e)

            self.pling=False

            if not self.opts.boundaryDict and not self.opts.listDict and not self.opts.listDictWithHeader:
                self.compareDict(source.content,dest.content,1,path.basename(sName))
            else:
                self.compareIterable(source.content,dest.content,1,path.basename(sName))

            if not self.pling:
                print_("\nNo differences found")

    def dictString(self,path,name):
        return "%s[%s]" % (path,name)

    def iterString(self,path,index):
        return "%s[%d]" % (path,index)

    def compare(self,src,dst,depth,name):
        if type(src)!=type(dst):
            print_(f.diff+">><<",name,": Types differ"+f.reset+"\n+"+f.src+">>Source:"+f.reset+"\n",makeString(src),"\n"+f.dst+"<<Destination:"+f.reset+"\n",makeString(dst)+f.reset)
            self.pling=True
        elif type(src) in [tuple,list,TupleProxy]:
            self.compareIterable(src,dst,depth,name)
        elif isinstance(src,(str,float,bool,BoolProxy)+integer_types) or src==None:
            self.comparePrimitive(src,dst,depth,name)
        elif src.__class__ in [Dimension,Tensor,SymmTensor,Vector]:
            self.comparePrimitive(src,dst,depth,name)
        elif src.__class__==Field:
            self.compareField(src,dst,depth,name)
        elif type(src) in [DictProxy,dict]:
            self.compareDict(src,dst,depth,name)
        else:
            warning("Type of",name,"=",type(src),"unknown")
            if self.opts.debug:
                try:
                    print_("Class of",name,"=",src.__class__,"unknown")
                except:
                    pass

    def compareField(self,src,dst,depth,name):
        if src!=dst:
            self.pling=True
            print_(f.diff+">><< Field",name,": Differs"+f.reset+"\n"+f.src+">>Source:"+f.reset+"\n",end=" ")
            if src.uniform:
                print_(src)
            else:
                print_("nonuniform - field not printed")
            print_(f.dst+"<<Destination:"+f.reset+"\n",end=" ")
            if dst.uniform:
                print_(dst)
            else:
                print_("nonuniform - field not printed")

    def comparePrimitive(self,src,dst,depth,name):
        different=False
        numTypes=(float,)+integer_types
        if isinstance(src,numTypes) and isinstance(dst,numTypes):
            tol=max(abs(src),abs(dst))*(10**-self.opts.digits)
            if abs(src-dst)>tol:
                different=True
        elif src!=dst:
            different=True
        if different:
            print_(f.diff+">><<",name,": Differs"+f.reset+"\n"+f.src+">>Source:"+f.reset+"\n",src,"\n"+f.dst+"<<Destination:"+f.reset+"\n",dst)
            self.pling=True

    def compareIterable(self,src,dst,depth,name):
        nr=min(len(src),len(dst))

        for i in range(nr):
            if self.opts.debug:
                print_("Comparing",self.iterString(name,i))
            self.compare(src[i],dst[i],depth+1,self.iterString(name,i))

        if nr<len(src):
            print_(f.src+">>>>",self.iterString(name,nr),"to",self.iterString(name,len(src)-1),"missing from destination\n"+f.reset,makeString(src[nr:]))
            self.pling=True
        elif nr<len(dst):
            print_(f.dst+"<<<<",self.iterString(name,nr),"to",self.iterString(name,len(dst)-1),"missing from source\n"+f.reset,makeString(dst[nr:]))
            self.pling=True

    def compareDict(self,src,dst,depth,name):
        for n in src:
            if not n in dst:
                print_(f.src+">>>>",self.dictString(name,n),": Missing from destination\n"+f.reset,makeString(src[n]))
                self.pling=True
            else:
                if self.opts.debug:
                    print_("Comparing",self.dictString(name,n))
                self.compare(src[n],dst[n],depth+1,self.dictString(name,n))

        for n in dst:
            if not n in src:
                print_(f.dst+"<<<<",self.dictString(name,n),": Missing from source\n"+f.reset,makeString(dst[n]))
                self.pling=True

# Should work with Python3 and Python2
