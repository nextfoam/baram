#  ICE Revision: $Id$
"""Parameter file is read into memory and modified there"""

from PyFoam.RunDictionary.FileBasis import FileBasisBackup
from PyFoam.Basics.PlyParser import PlyParser
from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from PyFoam.Basics.DataStructures import Vector,Field,Dimension,DictProxy,TupleProxy,Tensor,SymmTensor,Unparsed,UnparsedList,Codestream,DictRedirection,BinaryBlob,BinaryList,BoolProxy

from PyFoam.Error import error,warning,FatalErrorPyFoamException

from os import path
from copy import deepcopy
import sys

from PyFoam.ThirdParty.six import print_,integer_types,iteritems,string_types

class ParsedParameterFile(FileBasisBackup):
    """ Parameterfile whose complete representation is read into
    memory, can be manipulated and afterwards written to disk"""

    def __init__(self,
                 name,
                 backup=False,
                 debug=False,
                 boundaryDict=False,
                 listDict=False,
                 listDictWithHeader=False,
                 listLengthUnparsed=None,
                 preserveComments=True,
                 noHeader=False,
                 binaryMode=False,
                 treatBinaryAsASCII=False,
                 noBody=False,
                 doMacroExpansion=False,
                 dontRead=False,
                 noVectorOrTensor=False,
                 dictStack=None,
                 createZipped=True,
                 longListOutputThreshold=20):
        """:param name: The name of the parameter file
        :param backup: create a backup-copy of the file
        :param boundaryDict: the file to parse is a boundary file
        :param listDict: the file only contains a list
        :param listDictWithHeader: the file only contains a list and a header
        :param listLengthUnparsed: Lists longer than that length are not parsed
        :param binaryMode: Parse long lists in binary mode (to be overridden by
        the settings in the header).
        :param treatBinaryAsASCII: even if the header says that this is a
        binary file treat it like an ASCII-file
        :param noHeader: don't expect a header
        :param noBody: don't read the body of the file (only the header)
        :param doMacroExpansion: expand #include and $var
        :param noVectorOrTensor: short lists of length 3, 6 an 9 are NOT
        interpreted as vectors or tensors
        :param dontRead: Do not read the file during construction
        :param longListOutputThreshold: Lists that are longer than this are
        prefixed with a length
        :param dictStack: dictionary stack for lookup (only used for include)
        """

        self.noHeader=noHeader
        self.noBody=noBody
        FileBasisBackup.__init__(self,
                                 name,
                                 backup=backup,
                                 useBinary=True,
                                 createZipped=createZipped)
        self.debug=debug
        self.boundaryDict=boundaryDict
        self.listDict=listDict
        self.listDictWithHeader=listDictWithHeader
        self.listLengthUnparsed=listLengthUnparsed
        self.doMacros=doMacroExpansion
        self.preserveComments=preserveComments
        self.noVectorOrTensor=noVectorOrTensor
        self.header=None
        self.content=None
        self.longListOutputThreshold=longListOutputThreshold
        self.binaryMode=binaryMode
        self.treatBinaryAsASCII=treatBinaryAsASCII
        self.lastDecoration=""
        self.dictStack=dictStack

        if not dontRead:
            self.readFile()

    def parse(self,content):
        """Constructs a representation of the file"""
        try:
            parser=FoamFileParser(content,
                                  debug=self.debug,
                                  fName=self.name,
                                  boundaryDict=self.boundaryDict,
                                  listDict=self.listDict,
                                  listDictWithHeader=self.listDictWithHeader,
                                  listLengthUnparsed=self.listLengthUnparsed,
                                  noHeader=self.noHeader,
                                  noBody=self.noBody,
                                  preserveComments=self.preserveComments,
                                  binaryMode=self.binaryMode,
                                  treatBinaryAsASCII=self.treatBinaryAsASCII,
                                  noVectorOrTensor=self.noVectorOrTensor,
                                  dictStack=self.dictStack,
                                  doMacroExpansion=self.doMacros)
        except BinaryParserError:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            if not self.treatBinaryAsASCII:
                # Retrying in ASCII-mode although the file thinks it is binary
                parser=FoamFileParser(content,
                                      debug=self.debug,
                                      fName=self.name,
                                      boundaryDict=self.boundaryDict,
                                      listDict=self.listDict,
                                      listDictWithHeader=self.listDictWithHeader,
                                      listLengthUnparsed=self.listLengthUnparsed,
                                      noHeader=self.noHeader,
                                      noBody=self.noBody,
                                      preserveComments=self.preserveComments,
                                      binaryMode=self.binaryMode,
                                      treatBinaryAsASCII=True,
                                      noVectorOrTensor=self.noVectorOrTensor,
                                      dictStack=self.dictStack,
                                      doMacroExpansion=self.doMacros)
            else:
                raise e

        self.content=parser.getData()
        self.header=parser.getHeader()
        self.lastDecoration=parser._decorationBuffer

        return self.content

    def __contains__(self,key):
        return key in self.content

    def __getitem__(self,key):
        return self.content[key]

    def __setitem__(self,key,value):
        self.content[key]=value

    def __delitem__(self,key):
        del self.content[key]

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        for key in self.content:
            yield key

    def __str__(self):
        """Generates a string from the contents in memory
        Used to be called makeString"""

        string="// -*- C++ -*-\n// File generated by PyFoam - sorry for the ugliness\n\n"

        generator=FoamFileGenerator(self.content,
                                    header=self.header if not self.noHeader else None,
                                    longListThreshold=self.longListOutputThreshold)
        string+=generator.makeString(firstLevel=True)

        if len(self.lastDecoration)>0:
            string+="\n\n"+self.lastDecoration

        return string

    def getValueDict(self):
        """Get a dictionary with the values with the decorators removed"""
        result={}
        if self.content:
            for k in self.content:
                if type(k) not in integer_types:
                    result[k]=self.content[k]
        return result

class WriteParameterFile(ParsedParameterFile):
    """A specialization that is used to only write to the file"""
    def __init__(self,
                 name,
                 backup=False,
                 className="dictionary",
                 objectName=None,
                 createZipped=False,
                 **kwargs):
        ParsedParameterFile.__init__(self,
                                     name,
                                     backup=backup,
                                     dontRead=True,
                                     createZipped=createZipped,
                                     **kwargs)

        if objectName==None:
            objectName=path.basename(name)

        self.content=DictProxy()
        self.header={"version":"2.0",
                     "format":"ascii",
                     "class":className,
                     "object":objectName}

class Enumerate(object):
    def __init__(self, names):
        for number, name in enumerate(names):
            setattr(self, name, number)

inputModes=Enumerate(["merge","error","warn","protect","overwrite","default"])

class NotAPrelist:
    """Class to return if the length of the prelist does not fit the prefix"""
    def __init__(self,a,b):
        self.a=a
        self.b=b

class FoamFileParser(PlyParser):
    """Class that parses a string that contains the contents of an
    OpenFOAM-file and builds a nested structure of directories and
    lists from it"""

    def __init__(self,
                 content,
                 fName=None,
                 debug=False,
                 noHeader=False,
                 noBody=False,
                 doMacroExpansion=False,
                 boundaryDict=False,
                 preserveComments=True,
                 preserveNewlines=True,
                 listDict=False,
                 listDictWithHeader=False,
                 listLengthUnparsed=None,
                 binaryMode=False,
                 treatBinaryAsASCII=False,
                 duplicateCheck=False,
                 noVectorOrTensor=False,
                 dictStack=None,
                 duplicateFail=True):
        """:param content: the string to be parsed
        :param fName: Name of the actual file (if any)
        :param debug: output debug information during parsing
        :param noHeader: switch that turns off the parsing of the header
        :param duplicateCheck: Check for duplicates in dictionaries
        :param duplicateFail: Fail if a duplicate is discovered"""

        self.binaryMode=binaryMode
        self.treatBinaryAsASCII=treatBinaryAsASCII
        self.fName=fName
        self.data=None
        self.header=None
        self.debug=debug
        self.listLengthUnparsed=listLengthUnparsed
        self.doMacros=doMacroExpansion
        self.preserveComments=preserveComments
        self.preserveNewLines=preserveNewlines
        self.duplicateCheck=duplicateCheck
        self.duplicateFail=duplicateFail
        self.noVectorOrTensor=noVectorOrTensor
        self.inHeader=True
        self.inBinary=False
        self.checkPrelistLength=True

        # Make sure that the first comment is discarded
        self.collectDecorations=False
        self.inputMode=inputModes.merge

        self._decorationBuffer=""

        startCnt=0

        self.dictStack=dictStack
        if self.dictStack==None:
            self.dictStack=[DictProxy()]

        if noBody:
            self.start='noBody'
            startCnt+=1

        if noHeader:
            self.inHeader=False
            self.start='noHeader'
            startCnt+=1
            self.collectDecorations=True

        if listDict:
            self.inHeader=False
            self.start='pureList'
            startCnt+=1
            self.dictStack=[]
            self.collectDecorations=True

        if listDictWithHeader:
            self.start='pureListWithHeader'
            startCnt+=1

        if boundaryDict:
            self.start='boundaryDict'
            startCnt+=1
            self.checkPrelistLength=False

        if startCnt>1:
            error("Only one start symbol can be specified.",startCnt,"are specified")

        PlyParser.__init__(self,debug=debug)

        #sys.setrecursionlimit(50000)
        #print sys.getrecursionlimit()

        self.emptyCnt=0

        self.header,self.data=self.parse(content)

    def __contains__(self,key):
        return key in self.data

    def __getitem__(self,key):
        return self.data[key]

    def __setitem__(self,key,value):
        self.data[key]=value

    def __delitem__(self,key):
        del self.data[key]

    def __iter__(self):
        for key in self.data:
            yield key

##    def __len__(self):
##        if self.data==None:
##            return 0
##        else:
##            return len(self.data)

    def resetDecoration(self):
        self._decorationBuffer=""

    def addToDecoration(self,text):
        if self.collectDecorations:
            self._decorationBuffer+=text

    def addCommentToDecorations(self,text):
        if self.preserveComments:
            self.addToDecoration(text)

    def addNewlinesToDecorations(self,text):
        if self.preserveNewLines:
            self.addToDecoration(text)

    def getDecoration(self):
        tmp=self._decorationBuffer
        self.resetDecoration()
        if len(tmp)>0:
            if tmp[-1]=='\n':
                tmp=tmp[:-1]
        return tmp

    def directory(self):
        if self.fName==None:
            return path.curdir
        else:
            return path.dirname(self.fName)

    def getData(self):
        """ Get the data structure"""
        return self.data

    def getHeader(self):
        """ Get the OpenFOAM-header"""
        return self.header

    def printContext(self,c,ind):
        """Prints the context of the current index"""
        print_("------")
        print_(c[max(0,ind-100):max(0,ind-1)])
        print_("------")
        print_(">",c[ind-1],"<")
        print_("------")
        print_(c[min(len(c),ind):min(len(c),ind+100)])
        print_("------")

    def parserError(self,text,c,ind):
        """Prints the error message of the parser and exit"""
        print_("PARSER ERROR:",text)
        print_("On index",ind)
        self.printContext(c,ind)
        raise PyFoamParserError("Unspecified")

    def condenseAllPreFixLists(self,orig):
        """Checks whether this list is a list that consists only of prefix-Lists"""
        isAllPreList=False
        if (len(orig) % 2)==0:
            isAllPreList=True
            for i in range(0,len(orig),2):
                if type(orig[i])==int and (type(orig[i+1]) in [list,Vector,Tensor,SymmTensor]):
                    if len(orig[i+1])!=orig[i]:
                        isAllPreList=False
                        break
                else:
                    isAllPreList=False
                    break

        if isAllPreList:
            return orig[1::2]
        else:
            return orig

    tokens = (
        'NAME',
        'ICONST',
        'FCONST',
        'SCONST',
        'FOAMFILE',
        'UNIFORM',
        'NONUNIFORM',
        'UNPARSEDCHUNK',
        'CODESTREAMCHUNK',
        'REACTION',
        'SUBSTITUTION',
        'MERGE',
        'OVERWRITE',
        'ERROR',
        'WARN',
        'PROTECT',
        'DEFAULT',
        'INCLUDE',
        'INCLUDE_ETC',
        'INCLUDE_FUNC',
        'INCLUDEIFPRESENT',
        'REMOVE',
        'INPUTMODE',
        'KANALGITTER',
        'CODESTART',
        'CODEEND',
        'BINARYBLOB',
        'RESTOFLINE',
    )

    reserved = {
        'FoamFile'   : 'FOAMFILE',
        'uniform'    : 'UNIFORM',
        'nonuniform' : 'NONUNIFORM',
        'include'    : 'INCLUDE',
        'includeEtc' : 'INCLUDE_ETC',
        'includeFunc' : 'INCLUDE_FUNC',
        'includeIfPresent': 'INCLUDEIFPRESENT',
        'sinclude'   : 'INCLUDEIFPRESENT',
        'remove'     : 'REMOVE',
        'inputMode'  : 'INPUTMODE',
        'merge'      : 'MERGE',
        'overwrite'  : 'OVERWRITE',
        'error'      : 'ERROR',
        'warn'       : 'WARN',
        'protect'    : 'PROTECT',
        'default'    : 'DEFAULT',
        }

    states = (
        ('unparsed', 'exclusive'),
        ('codestream', 'exclusive'),
        ('mlcomment', 'exclusive'),
        ('binaryblob', 'exclusive'),
        ('ignorerestofline', 'exclusive'),
        )

    def t_unparsed_left(self,t):
        r'\('
        t.lexer.level+=1
        #        print "left",t.lexer.level,

    def t_unparsed_right(self,t):
        r'\)'
        t.lexer.level-=1
        #        print "right",t.lexer.level,
        if t.lexer.level < 0 :
            t.value = t.lexer.lexdata[t.lexer.code_start:t.lexer.lexpos-1]
            #            print t.value
            t.lexer.lexpos-=1
            t.type = "UNPARSEDCHUNK"
            t.lexer.lineno += t.value.count('\n')
            t.lexer.begin('INITIAL')
            return t

    t_unparsed_ignore = ' \t\n0123456789.-+e'

    def t_unparsed_error(self,t):
        print_("Error unparsed",t.lexer.lexdata[t.lexer.lexpos])
        t.lexer.skip(1)

    t_binaryblob_ignore = ''

    def t_binaryblob_close(self,t):
        r"\)"
        size=t.lexer.lexpos-t.lexer.binary_start-1
#        print size,ord(t.lexer.lexdata[t.lexer.lexpos-1]),ord(t.lexer.lexdata[t.lexer.lexpos]),ord(t.lexer.lexdata[t.lexer.lexpos+1])
#        print size,ord(t.lexer.lexdata[t.lexer.binary_start-1]),ord(t.lexer.lexdata[t.lexer.binary_start])
#        print size % (t.lexer.binary_listlen), len(t.lexer.lexdata)
        if (size % t.lexer.binary_listlen)==0:
            # length of blob is multiple of the listlength
            nextChar=t.lexer.lexdata[t.lexer.lexpos]
            nextNextChar=t.lexer.lexdata[t.lexer.lexpos+1]
            if (nextChar in [';','\n'] and nextNextChar=='\n'):
                t.value = t.lexer.lexdata[t.lexer.binary_start:t.lexer.lexpos-1]
                assert(len(t.value)%t.lexer.binary_listlen == 0)
                t.lexer.lexpos-=1
                t.type = "BINARYBLOB"
                t.lexer.lineno += t.value.count('\n')
                t.lexer.begin('INITIAL')
                self.inBinary=False
                return t

    def t_binaryblob_throwaway(self,t):
        r'[^\)]'
        pass

    def t_binaryblob_error(self,t):
        print_("Error binaryblob",t.lexer.lexdata[t.lexer.lexpos])
        t.lexer.skip(1)

    def t_codestream_end(self,t):
        r"\#\}"
        t.value = t.lexer.lexdata[t.lexer.code_start:t.lexer.lexpos-2]
        t.lexer.lexpos-=2
        t.type = "CODESTREAMCHUNK"
        t.lexer.lineno += t.value.count('\n')
        t.lexer.begin('INITIAL')
        return t

    t_codestream_ignore = ''

    def t_codestream_throwaway(self,t):
        r'[^#]'
        pass

    def t_codestream_error(self,t):
        if t.lexer.lexdata[t.lexer.lexpos]!='#':
            print_("Error Codestream",t.lexer.lexdata[t.lexer.lexpos])
        t.lexer.skip(1)

    def t_NAME(self,t):
        r'[a-zA-Z_][+\-<>(),.\*|a-zA-Z_0-9&%:]*'
        t.type=self.reserved.get(t.value,'NAME')
        if t.value[-1]==")":
            if t.value.count(")")>t.value.count("("):
                # Give back the last ) because it propably belongs to a list
                t.value=t.value[:-1]
                t.lexer.lexpos-=1

        return t

    def t_SUBSTITUITION(self,t):
        r'\$[a-zA-Z_.:{][+\-<>(),.\*|a-zA-Z_0-9&%:${}]*'
        t.type=self.reserved.get(t.value,'SUBSTITUTION')
        if t.value[-1]==")":
            if t.value.count(")")>t.value.count("("):
                # Give back the last ) because it propably belongs to a list
                t.value=t.value[:-1]
                t.lexer.lexpos-=1

        return t

    t_CODESTART = r'\#\{'

    t_CODEEND = r'\#\}'

    t_KANALGITTER = r'\#'

    t_ICONST = r'(-|)\d+([uU]|[lL]|[uU][lL]|[lL][uU])?'

    t_FCONST = r'(-|)((\d+)(\.\d*)([eE](\+|-)?(\d+))? | (\d+)[eE](\+|-)?(\d+))([lL]|[fF])?'

    t_SCONST = r'\"([^\\\n]|(\\.))*?\"'

    literals = "(){};[]^"

    t_ignore=" \t\r"

    # Define a rule so we can track line numbers
    def t_newline(self,t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        now=t.lexer.lexpos
        next=t.lexer.lexdata.find('\n',now)
        if next>=0:
            line=t.lexer.lexdata[now:next]
            pos=line.find("=")

            if pos>=0 and not self.binaryMode:
                if ((line.find("//")>=0 and line.find("//")<pos)) or \
                   (line.find("/*")>=0 and line.find("/*")<pos) or \
                   (line.find('"')>=0 and line.find('"')<pos):
                    return
                t.value = line
                t.type = "REACTION"
                t.lexer.lineno += 1
                t.lexer.lexpos = next
                return t
        #        self.addNewlinesToDecorations(t.value)

    t_ignorerestofline_ignore = ""

    # t_ignorerestofline_SCONST = t_SCONST

    def t_ignorerestofline_SCONST(self,t):
        r'\"([^\\\n]|(\\.))*?\"'
        t.type = "SCONST"
        return t

    def t_ignorerestofline_restofline(self,t):
        r'[^\n]+'
        t.lexer.begin("INITIAL")
        t.type = "RESTOFLINE"
        return t

    def t_ignorerestofline_newline(self,t):
        r'[\n]'
        t.lexer.lineno += t.value.count('\n')
        t.lexer.begin("INITIAL")
        t.type = "RESTOFLINE"
        return t

    def t_ignorerestofline_error(self,t):
        print_("Error Reading rest of line",t.lexer.lexdata[t.lexer.lexpos])
        t.lexer.skip(1)

    # C++ comment (ignore)
    def t_ccode_comment(self,t):
        r'//.*'
        t.lexer.lineno += t.value.count('\n')
        self.addCommentToDecorations(t.value)

    def t_startmlcomment(self,t):
        r'/\*'
        t.lexer.begin('mlcomment')
        self.mllevel=1
        self.mlcomment_start = t.lexer.lexpos-2

    def t_mlcomment_newlevel(self,t):
        r'/\*'
        self.mllevel+=1

    def t_mlcomment_endcomment(self,t):
        r'\*/'
        self.mllevel-=1
        if self.mllevel<=0:
            t.lexer.begin('INITIAL')
            mlcomment=t.lexer.lexdata[self.mlcomment_start:t.lexer.lexpos]
            t.lexer.lineno += mlcomment.count('\n')
            self.addCommentToDecorations(mlcomment)

    def t_mlcomment_throwaway(self,t):
        r'[^\*]'
        pass

    t_mlcomment_ignore = ''

    def t_mlcomment_error(self,t):
        if t.lexer.lexdata[t.lexer.lexpos]!="*":
            print_("Error comment",t.lexer.lexdata[t.lexer.lexpos])
        t.lexer.skip(1)

    # Error handling rule
    def t_error(self,t):
        msg="Illegal character '%s' in line %d (pos: %d)" % (
            t.value[0],
            t.lexer.lineno,
            t.lexer.lexpos)
        raise PyFoamParserError(msg)
        #        t.lexer.skip(1) # the old days when illegal characters were accepted

    def p_global(self,p):
        'global : header dictbody'
        p[0] = ( p[1] , p[2] )

    def p_gotHeader(self,p):
        'gotHeader :'
        p.lexer.lexpos=len(p.lexer.lexdata)
        self.inHeader=False

    def p_noBody(self,p):
        ''' noBody : FOAMFILE '{' dictbody gotHeader '}' '''
        p[0] = ( p[3] , {} )

    def p_noHeader(self,p):
        'noHeader : dictbody'
        p[0] = ( None , p[1] )

    def p_pureList(self,p):
        'pureList : onlyListOrPList'
        p[0] = ( None , p[1] )

    def p_onlyListOrPList(self,p):
        '''onlyListOrPList : list
                           | prelist
                           | uniformfield '''
        if isinstance(p[1],(NotAPrelist,)):
            p[0]=(p[1].a,p[1].b)
        else:
            p[0]=p[1]

    def p_pureListWithHeader(self,p):
        '''pureListWithHeader : header onlyListOrPList'''
        p[0] = ( p[1] , p[2] )

    def p_afterHeader(self,p):
        'afterHeader :'
        pass

    def p_boundaryDict(self,p):
        '''boundaryDict : header list
                        | header prelist '''
        #        p[0] = (  p[1] , dict(zip(p[2][::2],p[2][1::2])) )
        p[0] = (  p[1] , p[2] )

    def p_header(self,p):
        'header : FOAMFILE dictionary'
        self.inHeader=False
        p[0] = p[2]

        # if p[0]["format"]=="binary":
        #     if not self.treatBinaryAsASCII:
        #         self.binaryMode=True
        #     else:
        #         self.binaryMode=False
        # elif p[0]["format"]=="ascii":
        #     self.binaryMode=False
        # else:
        #     raise FatalErrorPyFoamException("Don't know how to parse file format",p[0]["format"])

        self.collectDecorations=True

    def p_macro(self,p):
        '''macro : KANALGITTER include RESTOFLINE
                 | KANALGITTER inputMode RESTOFLINE
                 | KANALGITTER remove RESTOFLINE'''
        p[0] = p[1]+p[2]+"\n"
        if self.doMacros:
            p[0]="// "+p[0]

    def p_ignore_rest_of_line(self,p):
        '''ignore_rest_of_line : '''
        p.lexer.begin("ignorerestofline")

    def p_include(self,p):
        '''include : INCLUDE SCONST ignore_rest_of_line
                   | INCLUDE_ETC SCONST ignore_rest_of_line
                   | INCLUDE_FUNC NAME ignore_rest_of_line
                   | INCLUDE_FUNC SCONST ignore_rest_of_line
                   | INCLUDEIFPRESENT SCONST ignore_rest_of_line'''
        if self.doMacros:
            fName=path.join(self.directory(),p[2][1:-1])

            if p[1]=="includeFunc":
                funcName=p[2]
                if funcName[0]=='"' and funcName[-1]=='"':
                    funcName=funcName[1:-1].strip()
                includeName=funcName
                if funcName[-1]==")" and funcName.find("(")>0:
                    includeName=includeName[:includeName.find("(")]
                    raise PyFoamParserError("Parameters for #includeFunc not implemented")

            if p[1]=="includeEtc":
                from PyFoam.FoamInformation import foamEtc
                fName=path.join(foamEtc(),p[2][1:-1])
            elif p[1]=="includeFunc"and not path.exists(fName):
                from PyFoam.FoamInformation import foamPostProcessing
                from PyFoam.Basics.Utilities import findFileInDir

                fName=findFileInDir(self.directory(),includeName)
                if not path.exists(fName):
                    fName=findFileInDir(foamPostProcessing(),includeName)

            read=True

            if p[1]=="includeIfPresent" and not path.exists(fName):
                read=False
            if read and not path.exists(fName):
                raise PyFoamParserError("The included file "+fName+" does not exist")
            if read:
                try:
                    data=ParsedParameterFile(fName,
                                             noHeader=True,
                                             preserveComments=self.preserveComments,
                                             dictStack=self.dictStack if p[1]!="includeFunc" else None,
                                             doMacroExpansion=self.doMacros)
                except PyFoamParserError:
                    # retry but discard header
                    data=ParsedParameterFile(fName,
                                             noHeader=False,
                                             preserveComments=self.preserveComments,
                                             dictStack=self.dictStack if p[1]!="includeFunc" else None,
                                             doMacroExpansion=self.doMacros)
                into=self.dictStack[-1]
                if p[1]=="includeFunc":
                    into[funcName]=data.content
                else:
                    for k in data:
                        into[k]=data[k]

        p[0] = p[1] + " " + p[2]

    def p_inputMode(self,p):
        '''inputMode : INPUTMODE ignore_rest_of_line ERROR
                     | INPUTMODE ignore_rest_of_line WARN
                     | INPUTMODE ignore_rest_of_line PROTECT
                     | INPUTMODE ignore_rest_of_line DEFAULT
                     | INPUTMODE ignore_rest_of_line MERGE
                     | INPUTMODE ignore_rest_of_line OVERWRITE'''
        p[0] = p[1] + " " + p[3]
        self.inputMode=getattr(inputModes,p[3])

    def p_remove(self,p):
        '''remove : REMOVE ignore_rest_of_line word
                  | REMOVE wlist'''
        p[0] = p[1] + " "
        if len(p)==4:
            p[0]+=p[3]
        else:
            p[0]+="( "
            p[0]+=" ".join(p[2])
            p[0]+=" )"

    def p_wlist(self,p):
        '''wlist : '(' wordlist ignore_rest_of_line ')' '''
        p[0] = p[2]

    def p_integer(self,p):
        '''integer : ICONST'''
        p[0] = int(p[1])

    def p_float(self,p):
        '''float : FCONST'''
        p[0] = float(p[1])

    def p_enter_dict(self,p):
        '''enter_dict :'''
        self.dictStack.append(DictProxy())

    def p_exit_dict(self,p):
        '''exit_dict :'''
        p[0]=self.dictStack.pop()

    def p_dictionary(self,p):
        '''dictionary : '{' enter_dict dictbody '}' exit_dict
                      | '{' '}' '''
        if len(p)==6:
            p[0] = p[5]
        else:
            p[0] = DictProxy()

    def p_dictbody(self,p):
        '''dictbody : dictbody dictline
                    | dictline
                    | empty'''

        if len(p)==3:
            p[0]=p[1]
            if self.duplicateCheck:
                if p[2][0] in p[0]:
                    if self.duplicateFail:
                        error("Key",p[2][0],"already defined")
                    else:
                        warning("Key",p[2][0],"already defined")
            if type(p[2][0])==DictRedirection and p[2][1]=='':
                p[0].addRedirection(p[2][0])
            else:
                if type(p[2][1])==DictRedirection:
                    p[0][p[2][0]]=p[2][1].getContent()
                else:
                    p[0][p[2][0]]=p[2][1]
                p[0].addDecoration(p[2][0],self.getDecoration())
        else:
            p[0]=self.dictStack[-1]

            if p[1]:
                if type(p[1][0])==DictRedirection and p[1][1]=='':
                    p[0].addRedirection(p[1][0])
                else:
                    if type(p[1][1])==DictRedirection:
                        p[0][p[1][0]]=p[1][1].getContent()
                    else:
                        p[0][p[1][0]]=p[1][1]


    def p_list(self,p):
        '''list : '(' itemlist ')' '''
        p[0] = self.condenseAllPreFixLists(p[2])
        if not self.noVectorOrTensor and (
            len(p[2])==3 or len(p[2])==9 or len(p[2])==6):
            isVector=True
            for i in p[2]:
                try:
                    float(i)
                except:
                    isVector=False
            if isVector:
                if len(p[2])==3:
                    p[0]=Vector(*p[2])
                elif len(p[2])==9:
                    p[0]=Tensor(*p[2])
                else:
                    p[0]=SymmTensor(*p[2])

    def p_unparsed(self,p):
        '''unparsed : UNPARSEDCHUNK'''
        p[0] = Unparsed(p[1])

    def p_binaryblob(self,p):
        '''binaryblob : BINARYBLOB'''
        p[0] = BinaryBlob(p[1])

    def p_prelist_seen(self,p):
        '''prelist_seen : '''
        if self.binaryMode:
                p.lexer.begin('binaryblob')
                p.lexer.binary_start = p.lexer.lexpos
                p.lexer.binary_listlen = p[-1]
                self.inBinary=True
        elif self.listLengthUnparsed!=None:
            if int(p[-1])>=self.listLengthUnparsed:
                p.lexer.begin('unparsed')
                p.lexer.level=0
                p.lexer.code_start = p.lexer.lexpos

    def p_codestream(self,p):
        '''codestream : codeSeen CODESTART CODESTREAMCHUNK CODEEND '''
        p[0] = Codestream(p[3])

    def p_codeSeen(self,p):
        '''codeSeen : '''
        p.lexer.begin('codestream')
        p.lexer.level=0
        p.lexer.code_start = p.lexer.lexpos

    def p_uniformfield(self,p):
        ''' uniformfield : integer '{' number '}'
                         | integer '{' vector '}'
                         | integer '{' tensor '}'
                         | integer '{' symmtensor '}' '''
        p[0] = Field(p[3],length=p[1])

    def p_prelist(self,p):
        '''prelist : integer prelist_seen '(' itemlist ')'
                   | integer prelist_seen '(' binaryblob ')'
                   | integer prelist_seen '(' unparsed ')'
                   | integer prelist_seen '{' item '}' '''
        if type(p[4])==Unparsed:
            p[0] = UnparsedList(int(p[1]),p[4].data)
        elif type(p[4])==BinaryBlob:
            p[0] = BinaryList(int(p[1]),p[4].data)
        elif p[5]=='}':
            p[0]=[ p[4] ]*int(p[1])
        else:
            if len(p[4])!=p[1] and self.checkPrelistLength:
                p[0] = NotAPrelist(p[1],p[4])
            else:
                p[0] = self.condenseAllPreFixLists(p[4])

    def p_itemlist(self,p):
        '''itemlist : itemlist item
                    | itemlist ';'
                    | item '''
        if len(p)==2:
            if p[1]==None:
                p[0]=[]
            else:
                p[0]=[ p[1] ]
        else:
            p[0]=p[1]
            if isinstance(p[2],(NotAPrelist,)):
                p[0].append(p[2].a)
                p[0].append(p[2].b)
            else:
                if p[2]!=';':
                    p[0].append(p[2])

    def p_wordlist(self,p):
        '''wordlist : wordlist word
                    | word '''
        if len(p)==2:
            if p[1]==None:
                p[0]=[]
            else:
                p[0]=[ p[1] ]
        else:
            p[0]=p[1]
            p[0].append(p[2])

    def p_word(self,p):
        '''word : NAME
                | UNIFORM
                | NONUNIFORM
                | MERGE
                | OVERWRITE
                | DEFAULT
                | WARN
                | PROTECT
                | ERROR'''
        if p[1] in BoolProxy.TrueStrings+BoolProxy.FalseStrings:
            p[0]=BoolProxy(textual=p[1])
        else:
            p[0]=p[1]

    def parseSubst_root(self,nm,stck):
        if nm[0]==":":
            stck=[self.dictStack[0]]
            nm=nm[1:]
        elif nm[0]=='.':
            nm=nm[1:]
            off=0
            while nm[0]=='.':
                nm=nm[1:]
                off+=1
            if off>0:
                stck=stck[:-off]
        elif nm[0]=="{":
            inner=nm[1:nm.rfind("}")].strip()
            if inner[0]=="$":
                nm=self.parseSubst_root(inner[1:],stck)()
            else:
                nm=inner
        rest=None
        if nm.find(".")>0:
            rest=nm[nm.find(".")+1:]
            nm=nm[:nm.find(".")]
        for i,di in enumerate(reversed(stck)):
            if nm in di:
                if rest==None:
                    v=DictRedirection(deepcopy(di[nm]),
                                      di[nm],
                                      nm)
                    return v
                else:
                    newStck=stck[:i]
                    newStck.append(di[nm])
                    return self.parseSubst_root(rest,newStck)

    def p_substitution(self,p):
        '''substitution : SUBSTITUTION'''
        if self.doMacros:
            nm=p[1][1:]
            p[0]="<Symbol '"+nm+"' not found>"
            stck=self.dictStack
            p[0]=self.parseSubst_root(nm,stck)
        else:
            p[0]=p[1]

    def p_dictkey(self,p):
        '''dictkey : word
                   | SCONST'''
        if type(p[1])==BoolProxy:
            p[0]=str(p[1])
        else:
            p[0]=p[1]

    def p_dictline(self,p):
        '''dictline : dictkey dictitem ';'
                    | dictkey list ';'
                    | dictkey prelist ';'
                    | dictkey uniformfield ';'
                    | dictkey fieldvalue ';'
                    | macro
                    | substitution ';'
                    | dictkey codestream ';'
                    | dictkey dictionary'''
        if len(p)==4 and self.inHeader and p[1]=="format" and type(p[2])==str:
            if p[2]=="binary":
                if not self.treatBinaryAsASCII:
                    self.binaryMode=True
                else:
                    self.binaryMode=False
            elif p[2]=="ascii":
                self.binaryMode=False
            else:
                raise FatalErrorPyFoamException("Don't know how to parse file format",p[0]["format"])

        if len(p)==4 and type(p[2])==list:
            # remove the prefix from long lists (if present)
            doAgain=True
            tmp=p[2]
            while doAgain:
                doAgain=False
                for i in range(len(tmp)-1):
                    if type(tmp[i])==int and type(tmp[i+1]) in [list]:
                        if tmp[i]==len(tmp[i+1]):
                            nix=tmp[:i]+tmp[i+1:]
                            for i in range(len(tmp)):
                                tmp.pop()
                            tmp.extend(nix)
                            doAgain=True
                            break
        if len(p)==4:
            if isinstance(p[2],(NotAPrelist,)):
                p[0] = ( p[1] , (p[2].a,p[2].b) )
            else:
                p[0] = ( p[1] , p[2] )
        elif len(p)==3:
            if p[2]==';':
                p[0]= (p[1],'')
            else:
                p[0] = ( p[1] , p[2] )
        else:
            p[0] = ( self.emptyCnt , p[1] )
            self.emptyCnt+=1

    def p_number(self,p):
        '''number : integer
                  | FCONST'''
        try:
            p[0] = int(p[1])
        except ValueError:
            p[0] = float(p[1])

    def p_symbolic_dimension_terminal(self,p):
        ''' symbolic_dimension_terminal : word
                                        | number
                                        | '('
                                        | ')'
                                        | '*'
                                        | '/'
                                        | '^' '''
        p[0]=p[1]

    # We don't care if the dimension string makes sense. only the right symbols are checked for
    def p_symbolic_dimension(self,p):
        '''symbolic_dimension :  symbolic_dimension_terminal symbolic_dimension
                              |  symbolic_dimension_terminal '''
        if len(p)==2:
            p[0]=str(p[1])
        else:
            inter=" "
            if isinstance(p[1],string_types) and p[1] in "(*/^":
                inter=""
            elif p[2][0] in ")*/^":
                inter=""
            p[0]=str(p[1])+inter+p[2]

    def p_dimension(self,p):
        '''dimension : '[' number number number number number number number ']'
                     | '[' number number number number number ']'
                     | '[' symbolic_dimension ']' '''
        if len(p)==4:
            p[0]=Dimension(p[2])
        else:
            result=p[2:-1]
            if len(result)==5:
                result+=[0,0]
            p[0]=Dimension(*result)

    def p_vector(self,p):
        '''vector : '(' number number number ')' '''
        if self.noVectorOrTensor:
            p[0]=p[2:5]
        else:
            p[0]=Vector(*p[2:5])

    def p_tensor(self,p):
        '''tensor : '(' number number number number number number number number number ')' '''
        if self.noVectorOrTensor:
            p[0]=p[2:11]
        else:
            p[0]=Tensor(*p[2:11])

    def p_symmtensor(self,p):
        '''symmtensor : '(' number number number number number number ')' '''
        if self.noVectorOrTensor:
            p[0]=p[2:8]
        else:
            p[0]=SymmTensor(*p[2:8])

    def p_fieldvalue_uniform(self,p):
        '''fieldvalue : UNIFORM number
                      | UNIFORM vector
                      | UNIFORM tensor
                      | UNIFORM symmtensor'''
        p[0] = Field(p[2])

    def p_fieldvalue_nonuniform(self,p):
        '''fieldvalue : NONUNIFORM NAME list
                      | NONUNIFORM prelist
                      | NONUNIFORM NAME prelist'''
        if len(p)==4:
            if isinstance(p[3],(NotAPrelist,)):
                p[0] = Field(p[3].b,name=p[2])
            else:
                p[0] = Field(p[3],  name=p[2])
        else:
            if isinstance(p[2],(NotAPrelist,)):
                p[0] = Field(p[2].b)
            else:
                p[0] = Field(p[2]  )

    def p_dictitem(self,p):
        '''dictitem : longitem
                    | pitem'''
        if type(p[1])==tuple:
            if len(p[1])==2 and p[1][0]=="uniform":
                p[0]=Field(p[1][1])
            elif len(p[1])==3 and p[1][0]=="nonuniform":
                p[0]=Field(p[1][2],name=p[1][1])
            else:
                p[0]=TupleProxy(p[1])
        else:
            p[0] = p[1]

    def p_longitem(self,p):
        '''longitem : pitemlist pitem'''
        p[0] = p[1]+(p[2],)

    def p_pitemlist(self,p):
        '''pitemlist : pitemlist pitem
                     | pitem '''
        if len(p)==2:
            p[0]=(p[1],)
        else:
##             print type(p[1][-1])
##             if type(p[1][-1])==int and type(p[2])==tuple:
##                 print "Hepp",p[2]
            p[0]=p[1]+(p[2],)

    def p_pitem(self,p):
        '''pitem : word
                 | SCONST
                 | number
                 | dictionary
                 | list
                 | dimension
                 | substitution
                 | empty'''
        p[0] = p[1]

    def p_item(self,p):
        '''item : pitem
                | REACTION
                | prelist
                | list
                | uniformfield
                | dictionary'''
        p[0] = p[1]

    def p_empty(self,p):
        'empty :'
        pass

    def p_error(self,p):
        if self.inBinary:
            raise BinaryParserError("Problem reading binary", p) # .type, p.lineno
        else:
            raise PyFoamParserError("Syntax error in file %s at token" % self.fName, p) # .type, p.lineno
        # Just discard the token and tell the parser it's okay.
        # self.yacc.errok()

class PyFoamParserError(FatalErrorPyFoamException):
    def __init__(self,descr,data=None):
        FatalErrorPyFoamException.__init__(self,"Parser Error:",descr)
        self.descr=descr
        self.data=data

    def __str__(self):
        result="Error in PyFoamParser: '"+self.descr+"'"
        if self.data!=None:
            val=self.data.value
            if len(val)>100:
                val=val[:40]+" .... "+val[-40:]

            result+=" @ %r (Type: %s ) in line %d at position %d" % (val,
                                                                     self.data.type,
                                                                     self.data.lineno,
                                                                     self.data.lexpos)
        else:
            result+=" NONE"

        return result

    def __repr__(self):
        return str(self)

class BinaryParserError(PyFoamParserError):
    def __init__(self,descr,data=None):
        PyFoamParserError.__init__(self,descr,data)

class FoamStringParser(FoamFileParser):
    """Convenience class that parses only a headerless OpenFOAM dictionary"""

    def __init__(self,
                 content,
                 debug=False,
                 noVectorOrTensor=False,
                 duplicateCheck=False,
                 listDict=False,
                 doMacroExpansion=False,
                 duplicateFail=False):
        """:param content: the string to be parsed
        :param debug: output debug information during parsing"""

        FoamFileParser.__init__(self,
                                content,
                                debug=debug,
                                noHeader=not listDict,
                                boundaryDict=False,
                                listDict=listDict,
                                noVectorOrTensor=noVectorOrTensor,
                                duplicateCheck=duplicateCheck,
                                doMacroExpansion=doMacroExpansion,
                                duplicateFail=duplicateFail)

    def __str__(self):
        return str(FoamFileGenerator(self.data))

class ParsedBoundaryDict(ParsedParameterFile):
    """Convenience class that parses only a OpenFOAM polyMesh-boundaries file"""

    def __init__(self,
                 name,
                 treatBinaryAsASCII=False,
                 backup=False,
                 debug=False):
        """:param name: The name of the parameter file
        :param backup: create a backup-copy of the file"""

        ParsedParameterFile.__init__(self,
                                     name,
                                     backup=backup,
                                     treatBinaryAsASCII=treatBinaryAsASCII,
                                     debug=debug,
                                     boundaryDict=True)

    def parse(self,content):
        """Constructs a representation of the file"""
        temp=ParsedParameterFile.parse(self,content)
        self.content=DictProxy()
        for i in range(0,len(temp),2):
            self.content[temp[i]]=temp[i+1]
        return self.content

    def __str__(self):
        string="// File generated by PyFoam - sorry for the ugliness\n\n"
        temp=[]
        for k,v in iteritems(self.content):
            temp.append((k,v))

        temp.sort(key=lambda x:int(x[1]["startFace"]))

        temp2=[]

        for b in temp:
            temp2.append(b[0])
            temp2.append(b[1])

        generator=FoamFileGenerator(temp2,header=self.header)
        string+=str(generator)

        return string

class ParsedFileHeader(ParsedParameterFile):
    """Only parse the header of a file"""

    def __init__(self,name):
        ParsedParameterFile.__init__(self,name,backup=False,noBody=True)

    def __getitem__(self,name):
        return self.header[name]

    def __contains__(self,name):
        return name in self.header

    def __len__(self):
        return len(self.header)

# Should work with Python3 and Python2
