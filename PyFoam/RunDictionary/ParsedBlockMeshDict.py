#  ICE Revision: $Id$
"""A parsed blockMeshDict"""

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

class ParsedBlockMeshDict(ParsedParameterFile):
    """ A parsed version of a blockMeshDict-file. Adds some
    convenience-methods to access parts of the file"""

    def __init__(self,
                 name,
                 backup=False,
                 debug=False,
                 doMacroExpansion=False):
        ParsedParameterFile.__init__(self,
                                     name,
                                     backup=backup,
                                     debug=debug,
                                     longListOutputThreshold=None,
                                     doMacroExpansion=doMacroExpansion)

    def convertToMeters(self):
        try:
            return float(self["convertToMeters"])
        except KeyError:
            return 1

    def vertices(self):
        factor=self.convertToMeters()
        return [[float(y)*factor for y in x] for x in self["vertices"]]

    def blocks(self):
        """Returns a list with the 8 vertices that define each block"""
        result=[]
        i=1
        while i<len(self["blocks"]):
            result.append([int(b) for b in self["blocks"][i]])
            if type(self["blocks"][i+1])==str:
                i+=6
            else:
                i+=5

        return result

    def patches(self):
        """Returns a dictionary with lists of 4-tuples that define each patch"""
        result={}
        if "boundary" in self:
            # New format in 2.0
            for k,d in zip(self["boundary"][0::2],self["boundary"][1::2]):
                result[k]=[[int(i) for i in x] for x in d["faces"]]
        else:
            for i in range(1,len(self["patches"]),3):
                result[self["patches"][i]]=[[int(j) for j in x] for x in self["patches"][i+1]]

        return result

    def arcs(self):
        factor=self.convertToMeters()
        result=[]
        try:
            for i in range(len(self["edges"])):
                if str(self["edges"][i])=='arc':
                    result.append((int(self["edges"][i+1]),
                                   [float(y)*factor for y in self["edges"][i+3]],
                                   int(self["edges"][i+2])))
        except KeyError:
            pass

        return result

    def getBounds(self):
        v=self.vertices()
        mi=[ 1e10, 1e10, 1e10]
        ma=[-1e10,-1e10,-1e10]
        for p in v:
            for i in range(3):
                mi[i]=min(p[i],mi[i])
                ma[i]=max(p[i],ma[i])
        return mi,ma

    def typicalLength(self):
        mi,ma=self.getBounds()

        biggest=max(ma[0]-mi[0],ma[1]-mi[1],ma[2]-mi[2])
        smallest=min(ma[0]-mi[0],ma[1]-mi[1],ma[2]-mi[2])

        #        return 2*biggest*smallest/(biggest+smallest)
        return (biggest+smallest)/2

# Should work with Python3 and Python2
