"""Works with a polyMesh/boundary-File"""

from PyFoam.RunDictionary.ParsedParameterFile import ParsedBoundaryDict
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.Error import PyFoamException

from PyFoam.ThirdParty.six import iteritems

class BoundaryDict(ParsedBoundaryDict):
    """Handles data in a boundary-File"""

    def __init__(self,
                 case,
                 backup=False,
                 treatBinaryAsASCII=False,
                 region=None,
                 processor=None,
                 time=None):
        """:param case: Path to the case-directory"""
        try:
            ParsedBoundaryDict.__init__(self,
                                        SolutionDirectory(case,
                                                          archive=None,
                                                          paraviewLink=False).boundaryDict(time=time,
                                                                                           region=region,
                                                                                           processor=processor),
                                        treatBinaryAsASCII=treatBinaryAsASCII,
                                        backup=backup)
        except IOError:
            ParsedBoundaryDict.__init__(self,
                                        SolutionDirectory(case,
                                                          archive=None,
                                                          paraviewLink=False).boundaryDict(region=region,
                                                                                           processor=processor),
                                        treatBinaryAsASCII=treatBinaryAsASCII,
                                        backup=backup)

    def __getitem__(self,key):
        return self.content[key]

    def __setitem__(self,key,value):
        if not type(value)==dict:
            raise PyFoamException("Type of boundary element must be dict, is"+str(type(value)))
        for k in ["type","nFaces","startFace"]:
            if k not in value:
                raise PyFoamException("Required key "+str(k)+" is missing from"+str(value)+"not a valid patch")

        self.content[key]=value

    def __iter__(self):
        for p in self.content:
            yield p

    def patches(self,patchType=None):
        """Returns a list with the names of the patches
        :param patchType: If specified only patches of the specific type are returned"""

        if patchType==None:
            return list(self.content.keys())
        else:
            result=[]
            for k,v in iteritems(self.content):
                if v["type"]==patchType:
                    result.append(k)
            return result

# Should work with Python3 and Python2
