#  ICE Revision: $Id$
"""
Application class that implements pyFoamUpgradeDictionariesTo20
"""

from os import path

from .UpgradeDictionariesTo17 import UpgradeDictionariesTo17,DictionaryUpgradeInfo

from PyFoam.Basics.DataStructures import DictProxy,TupleProxy
from PyFoam.Error import error,warning

class ReactionFileUpgradeInfo(DictionaryUpgradeInfo):
    def __init__(self):
        DictionaryUpgradeInfo.__init__(self)
        self.noHeader=True

    def name(self):
        return "reactionFile20"

    def location(self):
        return path.join("constant","reactions")

    def checkUpgrade(self,content):
        if "reactions" not in content:
            return False
        else:
            return type(content["reactions"]) in [list]

    def makeCoeffList(self,raw,default,specNames):
        specs=set(specNames)
        lst=[]
        for s,v in zip(raw[0::2],raw[1::2]):
            lst.append([s,v])
            specs.remove(s)

        for s in specs:
            lst.append([s,default])

        return lst

    def manipulate(self,content):
        newReactions=DictProxy()
        rData=zip(*[content["reactions"][i::3] for i in range(3)])
        cnt=1
        for rType,scheme,parameters in rData:
            name="reaction%d"%cnt
            cnt+=1
            r={}
            r["type"]=rType
            r["reaction"]='"'+str(scheme).strip()+'"'
            if rType in ["irreversibleArrheniusReaction",
                         "reversibleArrheniusReaction"]:
                r["A"]=parameters[0]
                r["beta"]=parameters[1]
                r["Ta"]=parameters[2]
            elif rType in ["reversiblethirdBodyArrheniusReaction"]:
                r["A"]=parameters[0][0]
                r["beta"]=parameters[0][1]
                r["Ta"]=parameters[0][2]
                r["defaultEfficiency"]=parameters[1][0]
                r["coeffs"]=self.makeCoeffList(parameters[1][1:],
                                               parameters[1][0],
                                               content["species"])
            elif rType in ["reversibleArrheniusLindemannFallOffReaction"]:
                r["k0"]={}
                r["k0"]["A"]=parameters[0][0]
                r["k0"]["beta"]=parameters[0][1]
                r["k0"]["Ta"]=parameters[0][2]
                r["kInf"]={}
                r["kInf"]["A"]=parameters[1][0]
                r["kInf"]["beta"]=parameters[1][1]
                r["kInf"]["Ta"]=parameters[1][2]
                r["F"]={}
                r["thirdBodyEfficiencies"]={}
                r["thirdBodyEfficiencies"]["defaultEfficiency"]=parameters[2][0]
                r["thirdBodyEfficiencies"]["coeffs"]=self.makeCoeffList(parameters[2][1:],
                                                                        parameters[2][0],
                                                                        content["species"])
            elif rType in ["reversibleArrheniusTroeFallOffReaction"]:
                r["k0"]={}
                r["k0"]["A"]=parameters[0][0]
                r["k0"]["beta"]=parameters[0][1]
                r["k0"]["Ta"]=parameters[0][2]
                r["kInf"]={}
                r["kInf"]["A"]=parameters[1][0]
                r["kInf"]["beta"]=parameters[1][1]
                r["kInf"]["Ta"]=parameters[1][2]
                r["F"]={}
                r["F"]["alpha"]=parameters[2][0]
                r["F"]["Tsss"]=parameters[2][1]
                r["F"]["Ts"]=parameters[2][2]
                r["F"]["Tss"]=parameters[2][3]
                r["thirdBodyEfficiencies"]={}
                r["thirdBodyEfficiencies"]["defaultEfficiency"]=parameters[3][0]
                r["thirdBodyEfficiencies"]["coeffs"]=self.makeCoeffList(parameters[3][1:],
                                                                        parameters[3][0],
                                                                        content["species"])
            else:
                r["unsupported"]=parameters
            newReactions[name]=r
        content["reactions"]=newReactions

class BlockMeshUpgradeInfo(DictionaryUpgradeInfo):
    def __init__(self):
        DictionaryUpgradeInfo.__init__(self)

    def name(self):
        return "blockMesh20"

    def location(self):
        return path.join("constant","polyMesh","blockMeshDict")

    def checkUpgrade(self,content):
        return "boundary" not in content

    def manipulate(self,content):
        p=content["patches"]
        bnd=[]
        for t,n,f in zip(p[0::3],p[1::3],p[2::3]):
            bnd+=[ n, { "type" : t,
                        "faces" : f }]
        content["boundary"]=bnd

class ThermophysicalUpgradeInfo(DictionaryUpgradeInfo):
    def __init__(self):
        DictionaryUpgradeInfo.__init__(self)

    def name(self):
        return "thermophysical20"

    def location(self):
        return path.join("constant","thermophysicalProperties")

    def analyzeThermoType(self,content):
        return content["thermoType"].replace('>','').split('<')

    def checkUpgrade(self,content):
        tt=self.analyzeThermoType(content)
        if len(tt)!=6:
            return False

        for nm in content:
            data=content[nm]
            if type(data) in  [tuple,TupleProxy]:
                if len(data)>4: # Maybe there is a better criterium
                    return True

        return False

    def manipulate(self,content):
        what,mix,trans,spec,therm,gas=self.analyzeThermoType(content)
        for nm in content:
            data=content[nm]
            used=0

            if type(data) not in  [tuple,TupleProxy]:
                continue
            if len(data)<5:
                continue

            transDict={}
            if trans=="constTransport":
                transDict["Pr"]=data[-1-used]
                transDict["mu"]=data[-2-used]
                used+=2
            elif trans=="sutherlandTransport":
                transDict["Ts"]=data[-1-used]
                transDict["As"]=data[-2-used]
                used+=2
            else:
                error("Transport type",trans,"not implemented")

            thermDict={}
            if therm=="hConstThermo":
                thermDict["Hf"]=data[-1-used]
                thermDict["Cp"]=data[-2-used]
                used+=2
            elif therm=="eConstThermo":
                thermDict["Hf"]=data[-1-used]
                thermDict["Cv"]=data[-2-used]
                used+=2
            elif therm=="janafThermo":
                thermDict["lowCpCoeffs"]=data[-7-used:-0-used]
                thermDict["highCpCoeffs"]=data[-14-used:-7-used]
                thermDict["Tcommon"]=data[-15-used]
                thermDict["Thigh"]=data[-16-used]
                thermDict["Tlow"]=data[-17-used]
                used+=2*7+3
            else:
                error("Thermodynamics type",therm,"not implemented")

            specDict={}
            if spec=="specieThermo":
                specDict["molWeight"]=data[-1-used]
                specDict["nMoles"]=data[-2-used]
                used+=2
            else:
                error("Specie type",spec,"not implemented")

            if len(data)!=used+1:
                warning("Not all data for",nm,"used")

            comment=self.makeComment(data)
            content[nm]={"specie":specDict,
                         "thermodynamics":thermDict,
                         "transport":transDict}
            content.addDecoration(nm,comment)

##            gasDict={}
##            if gas=="perfectGas":
##                pass
##            else:
##                error("Gas type",gas,"not implemented")

class ThermophysicalDataUpgradeInfo(DictionaryUpgradeInfo):
    def __init__(self):
        DictionaryUpgradeInfo.__init__(self)
        self.listDict=True

    def name(self):
        return "thermophysicalData20"

    def location(self):
        return path.join("constant","thermoData")

    def checkUpgrade(self,content):
        if type(content) in [list]:
            return True
        else:
            return False

    def manipulate(self,content):
        lenData=2+2+(2*7+3)+2
        rawData=zip(*[content[i::lenData] for i in range(lenData)])
        content=DictProxy()
        for d in rawData:
            name=d[0]
            data=d[2:]
            used=0

            specDict={}
            specDict["nMoles"]=data[used]
            specDict["molWeight"]=data[used+1]
            used+=2

            thermDict={}
            thermDict["Tlow"]=data[used]
            thermDict["Thigh"]=data[used+1]
            thermDict["Tcommon"]=data[used+2]
            thermDict["highCpCoeffs"]=list(data[used+3:used+3+7])
            thermDict["lowCpCoeffs"]=list(data[used+3+7:used+3+2*7])
            used+=2*7+3

            transDict={}
            transDict["As"]=data[used]
            transDict["Ts"]=data[used+1]
            used+=2

            if len(data)!=used:
                warning("Not all data for",name,"used:",used,len(data))

            comment=self.makeComment(d)
            content[name]={"specie":specDict,
                           "thermodynamics":thermDict,
                           "transport":transDict}
            content.addDecoration(name,comment)
        return content

class UpgradeDictionariesTo20(UpgradeDictionariesTo17):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Examines dictionaries in a case and tries to upgrade them to a form
that is compatible with OpenFOAM 2.0
        """

        UpgradeDictionariesTo17.__init__(self,
                                         args=args,
                                         description=description,
                                         **kwargs)

    def addDicts(self):
        UpgradeDictionariesTo17.addDicts(self)

        self.dicts.append(BlockMeshUpgradeInfo())
        self.dicts.append(ThermophysicalUpgradeInfo())
        self.dicts.append(ThermophysicalDataUpgradeInfo())
        self.dicts.append(ReactionFileUpgradeInfo())

##    def addOptions(self):
##        UpgradeDictionariesTo17.addOptions(self)

# Should work with Python3 and Python2
