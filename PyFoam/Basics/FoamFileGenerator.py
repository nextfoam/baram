#  ICE Revision: $Id$
"""Transform a Python data-structure into a OpenFOAM-File-Representation"""

from PyFoam.Error import error,PyFoamException
from PyFoam.Basics.DataStructures import Vector,Field,Dimension,TupleProxy,DictProxy,Tensor,SymmTensor,Unparsed,UnparsedList,Codestream,DictRedirection,BinaryList,BoolProxy

from PyFoam.ThirdParty.six import string_types,integer_types
from collections import OrderedDict

class FoamFileGenerator(object):
    """Class that generates a OpenFOAM-compatible representation of a
    data-structure"""

    primitiveTypes=[SymmTensor,Tensor,Vector,Dimension,Field,Unparsed]

    def __init__(self,
                 data,
                 header=None,
                 longListThreshold=20,
                 useFixedType=True):
        """:param data: data structure that will be turned into a
        Foam-compatible file
        :param header: header information that is to be prepended
        :param longListThreshold: Threshold for lists before they are considered
        long. This means that they are prefixed with the number of elements. If the
        threshold is 0 or None then no list is considered long
        """

        self.data=data
        self.header=header
        self.longListThreshold=longListThreshold
        self.useFixedType=useFixedType

    def __str__(self):
        return self.makeString()

    def __quoteString(self,val):
        """Quote the string if it contains illegal characters"""
        if len(val)==0:
            return val
        if val[0] in ["'",'"']:
            return val
        quote=False
        for c in r'\{}/;"': # list from word::stripInvalid
            if val.find(c)>=0:
                quote=True
                break
        if quote:
            if val.find('"')>=0:
                return "'"+val+"'"
            else:
                return '"'+val+'"'
        else:
            return val

    def makeString(self,firstLevel=False):
        """turns the data into a string"""
        result=""
        if self.header:
            result+="FoamFile\n{\n"+self.strDict(self.header,indent=1)+"}\n\n"

        if type(self.data) in [dict,DictProxy,OrderedDict]:
            result+=self.strDict(self.data,firstLevel=firstLevel)
        elif type(self.data) in [tuple,TupleProxy]:
            result+=self.strTuple(self.data)
        elif type(self.data) in [list,UnparsedList,BinaryList]:
            result+=self.strList(self.data)
        elif self.data is None:
            raise FoamFileGeneratorError("<None> found")
        else:
            result+=self.strPrimitive(self.data)

        return result

    def strPrimitive(self,pri):
        if type(pri)==bool:
            if pri:
                return "yes"
            else:
                return "no"
        elif type(pri)==BoolProxy:
            return str(pri)
        elif isinstance(pri,string_types):
            return self.__quoteString(pri)
        elif isinstance(pri,integer_types+(float,)):
            return str(pri)
        elif pri.__class__ in self.primitiveTypes:
            return str(pri)
        elif type(pri)==DictRedirection:
            return str(pri())
        else:
            error("List, Dict or valid primitve expected,",type(pri),"found in",pri)

    def strDict(self,dic,indent=0,firstLevel=False):
        s=""
        if type(dic)==DictProxy:
            order=dic._order
        else:
            order=list(dic.keys())
            if not isinstance(dic,(OrderedDict,)):
                order.sort()

        for k in order:
            if type(k)==DictRedirection:
                v=k
            else:
                try:
                    v=dic[k]
                except KeyError:
                    v=dic.getRegexpValue(k)

            end="\n"
            if type(dic)==DictProxy:
                end=dic.getDecoration(k)+"\n"

            if firstLevel:
                end+="\n"

            # remove trailing spaces
            end="\n".join([part.rstrip() for part in end.split("\n")])

            if type(k)==int:
                s+=v
                continue

            if str(k).find("anonymValue")==0:
                k=""

            s+=(" "*indent)+str(k)
            if isinstance(v,string_types):
                if type(v)==Codestream:
                    s+="\n"
                    s+=" "*indent
                    s+=str(v)
                    s+=";"+end
                else:
                    s+=" "+self.__quoteString(v)+";"+end
            elif type(v) in [dict,DictProxy,OrderedDict]:
                s+="\n"+(" "*indent)+"{\n"
                s+=self.strDict(v,indent+2)
                s+=(" "*indent)+"}"+end
            elif type(v) in [list,UnparsedList]:
                s+="\n"
                s+=self.strList(v,indent+2)
                if s[-1]=="\n":
                    s=s[:-1]
                s+=";"+end
            elif isinstance(v,(tuple,TupleProxy)):
                s+=" "+self.strTuple(v,indent+2)+";"+end
            elif type(v) in [bool,BoolProxy]:
                if v:
                    s+=" yes;\n"
                else:
                    s+=" no;\n"
            elif isinstance(v,integer_types+(float,)):
                s+=" "+str(v)+";"+end
            elif v.__class__ in self.primitiveTypes:
                s+=" "+str(v)+";"+end
            elif type(v)==type(None):
                s+=" /* empty */ ;"+end
            elif type(v)==DictRedirection:
                s+=";"+end
            else:
                error("Unhandled type",type(v)," for",v)
        return s

    def strList(self,lst,indent=0):
        s=""

        if type(lst)==UnparsedList:
            s+=(" "*indent)+str(len(lst))+" ("
            s+=lst.data
            if lst.data[-1]!="\n":
                s+="\n"
            s+=(" "*indent)+")\n"
            return s
        elif type(lst)==BinaryList:
            s+=(" "*indent)+str(len(lst))+" ("
            s+=lst.data
            s+=")"
            return s

        theLen=len(lst)

        if len(lst)>2 and len(lst)%2==0:
            if isinstance(lst[0],string_types) and (type(lst[1]) in [dict,DictProxy]):
                theLen=len(lst)/2

        isFixedType=False
        if self.useFixedType and (len(lst)==3 or len(lst)==9 or len(lst)==6):
            isFixedType=True
            for l in lst:
                try:
                    float(l)
                except (ValueError,TypeError):
                    isFixedType=False

        if isFixedType:
            s+="("+" ".join(["%g"%v for v in lst])+")"
        else:
            if self.longListThreshold:
                if theLen>self.longListThreshold:
                    s+=(" "*indent)+str(theLen)+"\n"
            s+=(" "*indent)+"(\n"
            for v in lst:
                if isinstance(v,string_types):
                    s+=(" "*(indent+2))+v+"\n"
                elif type(v) in [dict,DictProxy]:
                    s+="\n"+(" "*(indent+2))+"{\n"
                    s+=self.strDict(v,indent+4)
                    s+="\n"+(" "*(indent+2))+"}\n"
                elif type(v) in [list,UnparsedList]:
                    s+="\n"
                    s+=self.strList(v,indent+2)
                elif type(v)==tuple:
                    s+=" "+self.strTuple(v,indent+2)+" "
                else:
                    s+=(" "*(indent+2))+str(v)+"\n"

            s+=(" "*indent)+")\n"

        return s

    def strTuple(self,lst,indent=0):
        s=""

        for v in lst:
            if isinstance(v,string_types):
                s+=v+" "
            elif type(v) in [dict,DictProxy]:
                s+="{\n"
                s+=self.strDict(v,indent+4)
                s+=(" "*(indent+2))+"} "
            elif type(v) in [list,UnparsedList]:
                s+=" "
                s+=self.strList(v,indent+2)
            else:
                s+=(" "*(indent+2))+str(v)+" "

        return s

def makeString(data):
    return str(FoamFileGenerator(data))

class FoamFileGeneratorError(PyFoamException):
    def __init__(self,descr):
        PyFoamException.__init__(self,descr)

# Should work with Python3 and Python2
