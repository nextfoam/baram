"""
Application-class that implements pyFoamModifyGGIBoundary.py

Modification of GGI and cyclicGGI interface parameters in
constant/polymesh/boundary file.

Author:
  Martin Beaudoin, Hydro-Quebec, 2009.  All rights reserved

"""

from .PyFoamApplication import PyFoamApplication
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from os import path
import re

from PyFoam.ThirdParty.six import print_

class ModifyGGIBoundary(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Modify GGI boundary condition parameters
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <caseDirectory> ggiPatchName",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=2,
                                   **kwargs)

    def addOptions(self):
        self.parser.add_option("--shadowName",
                               action="store",
                               dest="shadowName",
                               default=None,
                               help='Name of the shadowPatch')
        self.parser.add_option("--patchZoneName",
                               action="store",
                               dest="patchZoneName",
                               default=None,
                               help='Name of the zone for the GGI patch')
        self.parser.add_option("--bridgeOverlapFlag",
                               action="store",
                               dest="bridgeOverlapFlag",
                               default=None,
                               help='bridgeOverlap flag (on/off)')
        self.parser.add_option("--rotationAxis",
                               action="store",
                               dest="rotationAxis",
                               default=None,
                               help='rotation axis for cyclicGgi')
        self.parser.add_option("--rotationAngle",
                               action="store",
                               dest="rotationAngle",
                               default=None,
                               help='rotation axis angle for cyclicGgi')
        self.parser.add_option("--separationOffset",
                               action="store",
                               dest="separationOffset",
                               default=None,
                               help='separation offset for cyclicGgi')

        self.parser.add_option("--test",
                               action="store_true",
                               default=False,
                               dest="test",
                               help="Only print the new boundary file")

    def run(self):
        fName=self.parser.getArgs()[0]
        bName=self.parser.getArgs()[1]

        boundary=ParsedParameterFile(path.join(".",fName,"constant","polyMesh","boundary"),debug=False,boundaryDict=True)

        bnd=boundary.content

        if type(bnd)!=list:
            self.error("Problem with boundary file (not a list)")

        found=False

        for val in bnd:
            if val==bName:
                found=True
            elif found:
                bcType=val["type"]
                if re.match("cyclicGgi", bcType)!= None or re.match("ggi", bcType)!= None:
                    if self.parser.getOptions().shadowName!=None:
                        shadowName=self.parser.getOptions().shadowName
                        val["shadowPatch"]=shadowName
                        if shadowName not in bnd:
                            print_("Warning:  Setting the shadowName option for patch",bName,": there is no patch called",shadowName)
                            print_("          The boundary file was still modified for patch",bName)

                    if self.parser.getOptions().patchZoneName!=None:
                        val["zone"]=self.parser.getOptions().patchZoneName

                    if self.parser.getOptions().bridgeOverlapFlag!=None:
                        val["bridgeOverlap"]=self.parser.getOptions().bridgeOverlapFlag

                    if val["type"]=="cyclicGgi":
                        if self.parser.getOptions().rotationAxis!=None:
                            val["rotationAxis"]=self.parser.getOptions().rotationAxis

                        if self.parser.getOptions().rotationAngle!=None:
                            val["rotationAngle"]=self.parser.getOptions().rotationAngle

                        if self.parser.getOptions().separationOffset!=None:
                            val["separationOffset"]=self.parser.getOptions().separationOffset
                else:
                    print_("Unsupported GGI type '",bcType,"' for patch",bName)
                break

        if not found:
            self.error("Boundary",bName,"not found in",bnd[::2])

        if self.parser.getOptions().test:
            print_(boundary)
        else:
            boundary.writeFile()

# Should work with Python3 and Python2
