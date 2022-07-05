"""Data structures in Foam-Files that can't be directly represented by Python-Structures"""

from __future__ import division

from copy import deepcopy
import math
import re

# import FoamFileGenerator in the end to avoid circular dependencies

from PyFoam.ThirdParty.six import integer_types,PY3,string_types,StringIO

if PY3:
    def cmp(a,b):
        if a<b:
            return -1
        elif a==b:
            return 0
        else:
            return 1

class FoamDataType(object):
    def __repr__(self):
        return "'"+str(self)+"'"

    def __eq__(self,other):
        """Implementation to make __cmp__ work again in Python3

        Implementing this method means that these objects are not hashable.
        But that is OK
        """
        return self.__cmp__(other)==0

    def __lt__(self,other):
        "Implementation to make __cmp__ work again in Python3"
        return self.__cmp__(other)<0

    def __ne__(self,other):
        return self.__cmp__(other)!=0

    def __gt__(self,other):
        return self.__cmp__(other)>0

    def __ge__(self,other):
        return self.__cmp__(other)>=0

    def __le__(self,other):
        return self.__cmp__(other)<=0

class Field(FoamDataType):
    def __init__(self,val,name=None,length=None):
        self.val=val
        self.name=name
        self.length=length

        if type(val) in[list,UnparsedList,BinaryList]:
            self.uniform=False
        elif self.name==None:
            self.uniform=True
        else:
            raise TypeError("Type",type(val),"of value",val,"can not be used to determine uniformity")

        if self.length:
            if not self.uniform:
                raise TypeError("Type",type(val),"can't be used with a uniform field (length ",length," specified)")

    def __str__(self):
        result=""
        if self.length:
            result+=str(self.length)+" {"
            result+=str(self.val)+"}"
        else:
            if self.uniform:
                result+="uniform "
            else:
                result+="nonuniform "
                if self.name:
                    result+=self.name+" "

            result+=str(
                PyFoam.Basics.FoamFileGenerator.FoamFileGenerator(
                    self.val,
                    longListThreshold=-1,
                    useFixedType=False
                ))
        return result

    def __cmp__(self,other):
        if other is None or type(other)!=Field:
            return 1
        if self.uniform!=other.uniform:
            return cmp(self.uniform,other.uniform)
        elif self.name!=other.name:
            return cmp(self.name,other.name)
        elif self.length!=other.length:
            return cmp(self.length,other.length)
        else:
            return cmp(self.val,other.val)

    def __getitem__(self,key):
        if self.length:
            if key>=0 and key<self.length:
                return self.val
            else:
                raise IndexError('Key',key,'outside of range 0 to',self.length-1)

        if not self.uniform:
            return self.val[key]
        else:
            return self.val

    def __setitem__(self,key,value):
        assert(not self.uniform)
        self.val[key]=value

    def __len__(self):
        if self.length:
            return self.length
        elif isinstance(self.val,(list,)):
            return len(self.val)
        else:
            raise TypeError("Operation len() unsupported for data of type",type(self.val))

    def isUniform(self):
        return self.uniform

    def isBinary(self):
        return type(self.val)==BinaryList

    def binaryString(self):
        return "nonuniform "+self.name+" <BINARY DATA>"

    def value(self):
        return self.val

    def setUniform(self,data):
        self.val=data
        self.uniform=True
        self.name=None

    def toNumpy(self,regexp,dtypes):
        """Convert to numpy-structured array (with one entry)
        @param regexp: Ignored. Just for compatibility with Unparsed
        @param dtypes: lsit of data types"""
        import numpy as np
        if self.length:
            try:
                tup=tuple(self.val)
            except TypeError:
                tup=(self.val,)
            result=np.repeat(np.array([tup],dtype=dtypes),self.length)
            return result
        else:
            raise TypeError("Can not convert",str(self),"to a numpy-array")

class Dimension(FoamDataType):
    def __init__(self,*dims):
        if len(dims)==1:
            self.dims=None
            self.dimString=dims[0]
        else:
            assert(len(dims)==7)
            self.dims=list(dims)

    def __str__(self):
        result="[ "
        if self.dims is None:
            result+=self.dimString+" "
        else:
            for v in self.dims:
                result+=str(v)+" "
        result+="]"
        return result

    def __cmp__(self,other):
        if other is None:
            return 1
        if self.dims is None:
            if not hasattr(other,"dims"):
                return -1
            if other.dims is not None:
                return -1
            else:
                return cmp(self.dimString,other.dimString)
        else:
            if not hasattr(other,"dims"):
                return 1
            if other.dims is None:
                return 1
            else:
                return cmp(self.dims,other.dims)

    def __getitem__(self,key):
        return self.dims[key]

    def __setitem__(self,key,value):
        self.dims[key]=value

class FixedLength(FoamDataType):
    def __init__(self,vals):
        self.vals=vals[:]

    def __str__(self):
        return "("+" ".join(["%g"%v for v in self.vals])+")"

    def __cmp__(self,other):
        if other==None or not issubclass(type(other),FixedLength):
            return 1
        return cmp(self.vals,other.vals)

    def __getitem__(self,key):
        return self.vals[key]

    def __setitem__(self,key,value):
        self.vals[key]=value

    def __len__(self):
        return len(self.vals)

class Vector(FixedLength):
    def __init__(self,x,y,z):
        FixedLength.__init__(self,[x,y,z])

    def __add__(self,y):
        x=self
        if type(y)==Vector:
            return Vector(x[0]+y[0],x[1]+y[1],x[2]+y[2])
        elif type(y) in integer_types+(float,):
            return Vector(x[0]+y,x[1]+y,x[2]+y)
        else:
            return NotImplemented

    def __radd__(self,y):
        x=self
        if type(y) in integer_types+(float,):
            return Vector(x[0]+y,x[1]+y,x[2]+y)
        else:
            return NotImplemented

    def __sub__(self,y):
        x=self
        if type(y)==Vector:
            return Vector(x[0]-y[0],x[1]-y[1],x[2]-y[2])
        elif type(y) in integer_types+(float,):
            return Vector(x[0]-y,x[1]-y,x[2]-y)
        else:
            return NotImplemented

    def __rsub__(self,y):
        x=self
        if type(y) in integer_types+(float,):
            return Vector(y-x[0],y-x[1],y-x[2])
        else:
            return NotImplemented

    def __mul__(self,y):
        x=self
        if type(y)==Vector:
            return Vector(x[0]*y[0],x[1]*y[1],x[2]*y[2])
        elif type(y) in integer_types+(float,):
            return Vector(x[0]*y,x[1]*y,x[2]*y)
        else:
            return NotImplemented

    def __rmul__(self,y):
        x=self
        if type(y) in integer_types+(float,):
            return Vector(y*x[0],y*x[1],y*x[2])
        else:
            return NotImplemented

    def __div__(self,y):
        x=self
        if type(y)==Vector:
            return Vector(x[0]/y[0],x[1]/y[1],x[2]/y[2])
        elif type(y) in integer_types+(float,):
            return Vector(x[0]/y,x[1]/y,x[2]/y)
        else:
            return NotImplemented

    def __truediv__(self,y):
        return self.__div__(y)

    def __xor__(self,y):
        x=self
        if type(y)==Vector:
            return Vector(x[1]*y[2]-x[2]*y[1],
                          x[2]*y[0]-x[0]*y[2],
                          x[0]*y[1]-x[1]*y[0])
        else:
            return NotImplemented

    def __abs__(self):
        x=self
        return math.sqrt(x[0]*x[0]+x[1]*x[1]+x[2]*x[2])

    def __neg__(self):
        x=self
        return Vector(-x[0],-x[1],-x[2])

    def __pos__(self):
        x=self
        return Vector( x[0], x[1], x[2])

class Tensor(FixedLength):
    def __init__(self,v1,v2,v3,v4,v5,v6,v7,v8,v9):
        FixedLength.__init__(self,[v1,v2,v3,v4,v5,v6,v7,v8,v9])

class SymmTensor(FixedLength):
    def __init__(self,v1,v2,v3,v4,v5,v6):
        FixedLength.__init__(self,[v1,v2,v3,v4,v5,v6])

class BoolProxy(object):
    """Wraps a boolean parsed from a file. Optionally stores a textual
    representation
    """

    TrueStrings=["on",
                 "yes",
                 "true",
#                "y"     # this breaks parsing certain files
    ]
    FalseStrings=[
        "off",
        "no",
        "false",
#        "n",           # this breaks parsing certain files
#        "none",        # this breaks parsing of cases where the word none is needed
        "invalid"
    ]

    def __init__(self,val=None,textual=None):
        if val==None and textual==None:
            raise TypeError("'BoolProxy' initialized without values")
        elif val==None:
            if textual in BoolProxy.TrueStrings:
                self.val=True
            elif textual in BoolProxy.FalseStrings:
                self.val=False
            else:
                raise TypeError(str(textual)+" not in "+str(BoolProxy.TrueStrings)
                                +" or "+str(BoolProxy.TrueStrings))
        else:
            if val not in [True,False]:
                raise TypeError(str(val)+" is not a boolean")
            self.val=val
        self.textual=textual
        if self.textual:
            if self.val:
                if self.textual not in BoolProxy.TrueStrings:
                    raise TypeError(self.textual+" not in "
                                    +str(BoolProxy.TrueStrings))
            else:
                if self.textual not in BoolProxy.FalseStrings:
                    raise TypeError(self.textual+" not in "
                                    +str(BoolProxy.FalseStrings))

    def __nonzero__(self):
        return self.val

    # for Python 3
    def __bool__(self):
        return self.val

    def __str__(self):
        if self.textual==None:
            if self.val:
                return "yes"
            else:
                return "no"
        else:
            return self.textual

    def __repr__(self):
        return self.__str__()

    def __eq__(self,o):
        if type(o) in [bool,BoolProxy]:
            return self.val==o
        elif isinstance(o,string_types):
            if self.textual==o:
                return True
            else:
                try:
                    return self.val==BoolProxy(textual=o)
                except TypeError:
                    return False
        else:
            # raise TypeError("Can't compare BoolProxy with "+str(type(o)))
            return self.val==o

    def __ne__(self,o):
        return not self.__eq__(o)

class DictRedirection(object):
    """This class is in charge of handling redirections to other directories"""
    def __init__(self,fullCopy,reference,name):
        self._fullCopy=fullCopy
        self._reference=reference
        self._name=name

    def useAsRedirect(self):
        self._fullCopy=None

    def getContent(self):
        result=self._fullCopy
        self._fullCopy=None
        return result

    def __call__(self):
        return self._reference

    def __str__(self):
        return "$"+self._name

    def __float__(self):
        return float(self._reference)

    def keys(self):
        if self._fullCopy:
            return self._fullCopy.keys()
        else:
            return self._reference.keys()

class DictProxy(dict):
    """A class that acts like a dictionary, but preserves the order
    of the entries. Used to beautify the output"""

    def __init__(self):
        dict.__init__(self)
        self._order=[]
        self._decoration={}
        self._regex=[]
        self._redirects=[]

    def isRegexp(self,key):
        if type(key)==str:
            if key[0]=='"' and key[-1]=='"':
                return True
        return False

    def __setitem__(self,key,value):
        if self.isRegexp(key):
            exp=re.compile(key[1:-1])
            self._regex=[(key,exp,value)]+self._regex
        else:
            dict.__setitem__(self,key,value)
        if key not in self._order or self.isRegexp(key):
            self._order.append(key)

    def __getitem__(self,key):
        try:
            return dict.__getitem__(self,key)
        except KeyError:
            for k,e,v in self._regex:
                if e.match(key):
                    return v
            for r in self._redirects:
                try:
                    return r()[key]
                except KeyError:
                    pass

            raise KeyError(key)

    def __delitem__(self,key):
        dict.__delitem__(self,key)
        self._order.remove(key)
        if key in self._decoration:
            del self._decoration[key]

    def __deepcopy__(self,memo):
        new=DictProxy()
        for k in self._order:
            if type(k)==DictRedirection:
                new.addRedirection(k)
            else:
                try:
                    new[k]=deepcopy(self[k],memo)
                except KeyError:
                    new[k]=deepcopy(self.getRegexpValue(k),memo)

        return new

    def __contains__(self,key):
        if dict.__contains__(self,key):
            return True
        else:
            for k,e,v in self._regex:
                if e.match(key):
                    return True
            for r in self._redirects:
                if key in r():
                    return True

            return False

    def __enforceString(self,v,toString):
        if not isinstance(v,string_types) and toString:
            r=str(v)
            if isinstance(v,(list,dict)):
                r='"'+r+'"'
            return r
        else:
            return v

    def update(self,other=None,toString=False,**kwargs):
        """Emulate the regular update of dict"""
        if other:
            if hasattr(other,"keys"):
                for k in other.keys():
                    self[k]=self.__enforceString(other[k],toString)
            else:
                for k,v in other:
                    self[k]=self.__enforceString(v,toString)
        for k in kwargs:
            self[k]=self.__enforceString(kwargs[k],toString)

    def keys(self):
        result=[x for x in self._order if x not in self._redirects and not self.isRegexp(x)]
        for r in self._redirects:
            for k in r.keys():
                if not k in result:
                    result.append(k)

        return result

    def __iter__(self):
        s=set()
        for k in self._order:
            if k not in self._redirects and not self.isRegexp(k):
                s.add(k)
                yield k
        for r in self._redirects:
            for k in r.keys():
                if not k in s:
                    s.add(k)
                    yield k

    def __str__(self):
        first=True
        result="{"
        for k in self.keys():
            v=self[k]
            if first:
                first=False
            else:
                result+=", "
            result+="%s: %s" % (repr(k),repr(v))
        result+="}"
        return result

    def iteritems(self):
        lst=[]
        for k in self:
            lst.append((k,self[k]))
        return lst

    # needed for python 3. Should be a generator, but ...
    def items(self):
        return self.iteritems()

    def addDecoration(self,key,text):
        if key in self:
            if key not in self._decoration:
                self._decoration[key]=""
            self._decoration[key]+=text

    def getDecoration(self,key):
        if key in self._decoration:
            return " \t"+self._decoration[key]
        else:
            return ""

    def getRegexpValue(self,key):
        for k,e,v in self._regex:
            if k==key:
                return v
        raise KeyError(key)

    def addRedirection(self,redir):
        self._order.append(redir)
        redir.useAsRedirect()
        self._redirects.append(redir)

class TupleProxy(list):
    """Enables Tuples to be manipulated"""

    def __init__(self,tup=()):
        list.__init__(self,tup)

class Unparsed(object):
    """A class that encapsulates an unparsed string"""

    def __init__(self,data):
        self.data=data

    def __str__(self):
        return self.data

    def __hash__(self):
        return hash(self.data)

    def __lt__(self,other):
        return self.data<other.data

    def toNumpy(self,regexp,dtypes):
        """Assume that the unparsed data contains line-wise data and transform it to a numpy-array.
        @param regexp: regular expression where the groups correspond to the dtypes,
        @param dtypes: list with dtypes"""
        import numpy as np
        try:
            return np.fromregex(StringIO(self.data),
                                regexp,
                                dtypes)
        except TypeError:
            from PyFoam.ThirdParty.six import BytesIO,b
            return np.fromregex(BytesIO(b(self.data)),
                                regexp,
                                dtypes)

class BinaryBlob(Unparsed):
    """Represents a part of the file with binary data in it"""
    def __init__(self,data):
        Unparsed.__init__(self,data)

class Codestream(str):
    """A class that encapsulates an codestream string"""

    def __str__(self):
        return "#{" + str.__str__(self) + "#}"

class UnparsedList(object):
    """A class that encapsulates a list that was not parsed for
    performance reasons"""

    def __init__(self,lngth,data):
        self.data=data
        self.length=lngth

    def __len__(self):
        return self.length

    def __cmp__(self,other):
        return cmp(self.data,other.data)

    def __eq__(self,other):
        return self.data==other.data

    def __lt__(self,other):
        return self.data<other.data

    def toNumpy(self,regexp,dtypes):
        import numpy as np
        try:
            return np.fromregex(StringIO(self.data),
                                regexp,
                                dtypes)
        except TypeError:
            from PyFoam.ThirdParty.six import BytesIO,b
            return np.fromregex(BytesIO(b(self.data)),
                                regexp,
                                dtypes)

class BinaryList(UnparsedList):
    """A class that represents a list that is saved as binary data"""

    def __init__(self,lngth,data):
        UnparsedList.__init__(self,lngth,data)

def makePrimitiveString(val):
    """Make strings of types that might get written to a directory"""
    if isinstance(val,(Dimension,FixedLength,BoolProxy)):
        return str(val)
    else:
        return val

# Moved to the end to avoid circular dependencies
import PyFoam.Basics.FoamFileGenerator

# Should work with Python3 and Python2
