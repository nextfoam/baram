#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

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
from .dictionary_file import DictionaryFile


class CaseGenerator:
    def __init__(self, path):
        self._caseRoot = path
        self._db = coredb.CoreDB()

        self._constantPath = os.path.join(self._caseRoot, DictionaryFile.CONSTANT_DIRECTORY_NAME)
        self._boundaryPath = os.path.join(self._caseRoot, DictionaryFile.BOUNDARY_DIRECTORY_NAME)
        self._systemPath = os.path.join(self._caseRoot, DictionaryFile.SYSTEM_DIRECTORY_NAME)

    def _initCaseDir(self):
        # shutil.rmtree(self._caseRoot)
        if not os.path.exists(self._constantPath):
            os.mkdir(self._constantPath)
        if not os.path.exists(self._boundaryPath):
            os.mkdir(self._boundaryPath)
        if not os.path.exists(self._systemPath):
            os.mkdir(self._systemPath)

    def generateFiles(self, constantLoadingDir):
        self._initCaseDir()

        regions = self._db.getRegions()
        for rname in regions:
            cpath = os.path.join(self._constantPath, rname)
            if not os.path.exists(cpath):
                os.mkdir(cpath)

            bpath = os.path.join(self._boundaryPath, rname)
            if not os.path.exists(bpath):
                os.mkdir(bpath)

            spath = os.path.join(self._systemPath, rname)
            if not os.path.exists(spath):
                os.mkdir(spath)

            ppath = os.path.join(cpath, DictionaryFile.POLYMESH_DIRECTORY_NAME)
            if not os.path.exists(ppath):
                os.mkdir(ppath)

            ThermophysicalProperties(rname).build().write(self._caseRoot)
            OperatingConditions(rname).build().write(self._caseRoot)
            MRFProperties(rname).build().write(self._caseRoot)

            if RegionDB.getPhase(rname) != Phase.SOLID:
                TurbulenceProperties(rname).build().write(self._caseRoot)

            G(rname).build().write(self._caseRoot)
            # ToDo: for gravity models, set the file name to "p_rgh", otherwise set it to "p".
            P(rname, 'p_rgh').build().write(self._caseRoot)
            # Todo: create only if p_rgh is created
            P(rname, 'p', True).build().write(self._caseRoot)
            U(rname).build().write(self._caseRoot)

            # if ModelsDB.isEnergyModelOn():
            #     T(rname).build().write(self._caseRoot)
            #     Alphat(rname).build().write(self._caseRoot)
            #
            # turbulenceModel = ModelsDB.getTurbulenceModel()
            # if turbulenceModel == TurbulenceModel.K_EPSILON or turbulenceModel == TurbulenceModel.K_OMEGA:
            #     K(rname).build().write(self._caseRoot)
            #     Nut(rname).build().write(self._caseRoot)
            #     if turbulenceModel == TurbulenceModel.K_EPSILON:
            #         Epsilon(rname).build().write(self._caseRoot)
            #     elif turbulenceModel == TurbulenceModel.K_OMEGA:
            #         Omega(rname).build().write(self._caseRoot)
            # elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
            #     NuTilda(rname).build().write(self._caseRoot)

            TransportProperties(rname).build().write(self._caseRoot)

            T(rname).build().write(self._caseRoot)
            Alphat(rname).build().write(self._caseRoot)

            K(rname).build().write(self._caseRoot)
            Nut(rname).build().write(self._caseRoot)
            Epsilon(rname).build().write(self._caseRoot)
            Omega(rname).build().write(self._caseRoot)
            NuTilda(rname).build().write(self._caseRoot)

            FvSchemes(rname).build().write(self._caseRoot)
            FvSolution(rname).build().write(self._caseRoot)

            Boundary(rname).build(constantLoadingDir, self._caseRoot).write(self._caseRoot)

        FvSolution().build().write(self._caseRoot)
        ControlDict().build().write(self._caseRoot)
