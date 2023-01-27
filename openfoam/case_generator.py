#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from coredb import coredb
from coredb.region_db import RegionDB
from coredb.boundary_db import BoundaryDB
from openfoam.constant.dynamic_mesh_dict import DynamicMeshDict
from openfoam.constant.thermophysical_properties import ThermophysicalProperties
from openfoam.constant.operating_conditions import OperatingConditions
from openfoam.constant.MRF_properties import MRFProperties
from openfoam.constant.turbulence_properties import TurbulenceProperties
from openfoam.constant.transport_properties import TransportProperties
from openfoam.constant.g import G
from openfoam.constant.region_properties import RegionProperties
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
from openfoam.system.fv_options import FvOptions
from openfoam.system.decomposePar_dict import DecomposeParDict
from openfoam.system.set_fields_dict import SetFieldsDict
from openfoam.polymesh.boundary import Boundary
from openfoam.file_system import FileSystem


class CaseGenerator:
    def __init__(self):
        self._db = coredb.CoreDB()
        self._errors = None

    def getErrors(self):
        return self._errors

    def generateFiles(self):
        if self._validate():
            return False

        regions = self._db.getRegions()
        for rname in regions:
            region = RegionDB.getRegionProperties(rname)

            FileSystem.initRegionDirs(rname)

            ThermophysicalProperties(rname).build().write()
            OperatingConditions(rname).build().write()
            MRFProperties(rname).build().write()
            DynamicMeshDict(rname).build().write()

            if region.isFluid():
                TurbulenceProperties(rname).build().write()
                TransportProperties(rname).build().write()

            Boundary(rname).build().write()

            processorNo = 0
            while path := FileSystem.processorPath(processorNo):
                Boundary(rname, processorNo).build().write()
                self._generateBoundaryConditionsFiles(region, path, processorNo)
                processorNo += 1

            if processorNo == 0:
                self._generateBoundaryConditionsFiles(region, FileSystem.caseRoot())

            FvSchemes(rname).build().write()
            FvSolution(rname).build().write()
            FvOptions(rname).build().write()
            DecomposeParDict(rname).build().write()
            SetFieldsDict(rname).build().write()

        if len(regions) > 1:
            FvSolution().build().write()
            RegionProperties().build().write()

        G().build().write()

        ControlDict().build().write()

        DecomposeParDict().build().write()

        return True

    @classmethod
    def createCase(cls):
        FileSystem.setupNewCase()
        ControlDict().copyFromResource('openfoam/controlDict')

    def _validate(self):
        self._errors = ''

        regions = self._db.getRegions()
        for rname in regions:
            boundaries = self._db.getBoundaryConditions(rname)
            for bcid, bcname, bctype in boundaries:
                xpath = BoundaryDB.getXPath(bcid)
                if BoundaryDB.needsCoupledBoundary(bctype) and self._db.getValue(xpath + '/coupledBoundary') == '0':
                    self._errors += QCoreApplication.translate(
                        'CaseGenerator',
                        f'{BoundaryDB.dbBoundaryTypeToText(bctype)} boundary "{bcname}" needs a coupled boundary.\n')

        return self._errors

    def _generateBoundaryConditionsFiles(self, region, path, processorNo=None):
        times = [d.name for d in path.glob('[0-9]*')]
        time = max(times, key=lambda x: float(x)) if times else '0'

        Alphat(region, time, processorNo).build().write()

        K(region, time, processorNo).build().write()
        Nut(region, time, processorNo).build().write()
        Epsilon(region, time, processorNo).build().write()
        Omega(region, time, processorNo).build().write()
        NuTilda(region, time, processorNo).build().write()

        P(region, time, processorNo, 'p_rgh').build().write()
        P(region, time, processorNo, 'p').build().write()
        U(region, time, processorNo).build().write()
        T(region, time, processorNo).build().write()
