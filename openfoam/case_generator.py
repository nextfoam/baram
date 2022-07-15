#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.cell_zone_db import RegionDB
from coredb.material_db import Phase
from openfoam.constant.thermophysical_properties import ThermophysicalProperties
from openfoam.constant.operating_conditions import OperatingConditions
from openfoam.constant.MRF_properties import MRFProperties
from openfoam.constant.turbulence_properties import TurbulenceProperties
from openfoam.constant.transport_properties import TransportProperties
from openfoam.constant.g import G
from openfoam.boundary_conditions.p import P
from openfoam.boundary_conditions.u import U
from openfoam.boundary_conditions.t import T
from openfoam.boundary_conditions.k import K
from openfoam.boundary_conditions.epsilon import Epsilon
from openfoam.boundary_conditions.omega import Omega
from openfoam.boundary_conditions.nut import Nut
from openfoam.boundary_conditions.nuTilda import NuTilda
from openfoam.boundary_conditions.alphat import Alphat
from openfoam.system.fv_solution import FvSolution
from openfoam.system.control_dict import ControlDict
from openfoam.system.fv_schemes import FvSchemes
from openfoam.polymesh.boundary import Boundary
from openfoam.file_system import FileSystem


class CaseGenerator:
    def __init__(self):
        self._db = coredb.CoreDB()

    def generateFiles(self):
        FileSystem.initCaseDir()

        regions = self._db.getRegions()
        for rname in regions:
            FileSystem.initRegionDirs(rname)

            ThermophysicalProperties(rname).build().write()
            OperatingConditions(rname).build().write()
            MRFProperties(rname).build().write()

            if RegionDB.getPhase(rname) != Phase.SOLID:
                TurbulenceProperties(rname).build().write()

            G(rname).build().write()
            # ToDo: for gravity models, set the file name to "p_rgh", otherwise set it to "p".
            P(rname, 'p_rgh').build().write()
            # Todo: create only if p_rgh is created
            P(rname, 'p', True).build().write()
            U(rname).build().write()

            # if ModelsDB.isEnergyModelOn():
            #     T(rname).build().write()
            #     Alphat(rname).build().write()
            #
            # turbulenceModel = ModelsDB.getTurbulenceModel()
            # if turbulenceModel == TurbulenceModel.K_EPSILON or turbulenceModel == TurbulenceModel.K_OMEGA:
            #     K(rname).build().write()
            #     Nut(rname).build().write()
            #     if turbulenceModel == TurbulenceModel.K_EPSILON:
            #         Epsilon(rname).build().write()
            #     elif turbulenceModel == TurbulenceModel.K_OMEGA:
            #         Omega(rname).build().write()
            # elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
            #     NuTilda(rname).build().write()

            TransportProperties(rname).build().write()

            T(rname).build().write()
            Alphat(rname).build().write()

            K(rname).build().write()
            Nut(rname).build().write()
            Epsilon(rname).build().write()
            Omega(rname).build().write()
            NuTilda(rname).build().write()

            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()

            Boundary(rname).build().write()

        FvSolution().build().write()
        ControlDict().build().write()
