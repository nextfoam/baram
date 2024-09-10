#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging

from PySide6.QtCore import QCoreApplication, QObject, Signal

from libbaram import utils
from libbaram.exception import CanceledException
from libbaram.run import RunUtility, RunParallelUtility

from baramFlow.app import app
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.openfoam import parallel
from baramFlow.openfoam.constant.dynamic_mesh_dict import DynamicMeshDict
from baramFlow.openfoam.constant.g import G
from baramFlow.openfoam.constant.MRF_properties import MRFProperties
from baramFlow.openfoam.constant.operating_conditions import OperatingConditions
from baramFlow.openfoam.constant.region_properties import RegionProperties
from baramFlow.openfoam.constant.thermophysical_properties import ThermophysicalProperties
from baramFlow.openfoam.constant.transport_properties import TransportProperties
from baramFlow.openfoam.constant.turbulence_properties import TurbulenceProperties
from baramFlow.openfoam.boundary_conditions.alpha import Alpha
from baramFlow.openfoam.boundary_conditions.alphat import Alphat
from baramFlow.openfoam.boundary_conditions.epsilon import Epsilon
from baramFlow.openfoam.boundary_conditions.k import K
from baramFlow.openfoam.boundary_conditions.nut import Nut
from baramFlow.openfoam.boundary_conditions.nuTilda import NuTilda
from baramFlow.openfoam.boundary_conditions.omega import Omega
from baramFlow.openfoam.boundary_conditions.p import P
from baramFlow.openfoam.boundary_conditions.scalar import Scalar
from baramFlow.openfoam.boundary_conditions.specie import Specie
from baramFlow.openfoam.boundary_conditions.t import T
from baramFlow.openfoam.boundary_conditions.u import U
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.polymesh.boundary import Boundary
from baramFlow.openfoam.solver import findSolver
from baramFlow.openfoam.system.control_dict import ControlDict
from baramFlow.openfoam.system.fv_options import FvOptions
from baramFlow.openfoam.system.fv_schemes import FvSchemes
from baramFlow.openfoam.system.fv_solution import FvSolution
from baramFlow.openfoam.system.set_fields_dict import SetFieldsDict

logger = logging.getLogger(__name__)


class CaseGenerator(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()
        self._db = CoreDBReader()
        self._errors = None
        self._cm = None
        self._canceled: bool = False
        self._files = None

    def getErrors(self):
        return self._errors

    def _gatherFiles(self):
        solver = findSolver()
        if errors := self._validate(solver):
            return errors

        # Files that can be in case root folder or region folders

        regions = self._db.getRegions()
        self._files = []
        for rname in regions:
            region = self._db.getRegionProperties(rname)

            FileSystem.initRegionDirs(rname)

            self._files.append(ThermophysicalProperties(rname))
            self._files.append(OperatingConditions(rname))
            self._files.append(MRFProperties(rname))
            self._files.append(DynamicMeshDict(rname))

            if region.isFluid():
                self._files.append(TurbulenceProperties(rname))
                self._files.append(TransportProperties(rname))

            self._files.append(Boundary(rname))

            processorNo = 0
            while path := FileSystem.processorPath(processorNo):
                self._files.append(Boundary(rname, processorNo))
                processorNo += 1

            self._gatherBoundaryConditionsFiles(region, FileSystem.caseRoot())

            self._files.append(FvSchemes(rname))
            self._files.append(FvSolution(rname))
            self._files.append(FvOptions(rname))
            self._files.append(SetFieldsDict(region))

        # Files that should be created in case root folder in addition to the region folders.

        if len(regions) > 1:
            self._files.append(FvSolution())
            self._files.append(RegionProperties())

        # Files that should be in case root folder only

        self._files.append(G())

        self._files.append(ControlDict())

        return errors

    def _generateFiles(self):
        for file in self._files:
            if self._canceled:
                return
            file.build().write()

    def _validate(self, solver):
        if not GeneralDB.isTimeTransient():
            if solver == 'interPhaseChangeFoam':
                return QCoreApplication.translate('CaseGenerator',
                                                     'interPhaseChangeFoam supports time transient calculation only.')
            if solver == 'multiphaseInterFoam':
                return QCoreApplication.translate('CaseGenerator',
                                                  'multiphaseInterFoam supports time transient calculation only.')

        errors = ''
        regions = self._db.getRegions()
        for rname in regions:
            boundaries = self._db.getBoundaryConditions(rname)
            for bcid, bcname, bctype in boundaries:
                xpath = BoundaryDB.getXPath(bcid)
                if BoundaryDB.needsCoupledBoundary(bctype) and self._db.getValue(xpath + '/coupledBoundary') == '0':
                    errors += QCoreApplication.translate(
                        'CaseGenerator',
                        f'{BoundaryDB.dbBoundaryTypeToText(bctype)} boundary "{bcname}" needs a coupled boundary.\n')

        return errors

    def _gatherBoundaryConditionsFiles(self, region, path, processorNo=None):
        times = [d.name for d in path.glob('[0-9]*')]
        time = max(times, key=lambda x: float(x)) if times else '0'

        self._files.append(Alphat(region, time, processorNo))

        self._files.append(K(region, time, processorNo))
        self._files.append(Nut(region, time, processorNo))
        self._files.append(Epsilon(region, time, processorNo))
        self._files.append(Omega(region, time, processorNo))
        self._files.append(NuTilda(region, time, processorNo))

        self._files.append(P(region, time, processorNo, 'p_rgh'))
        self._files.append(P(region, time, processorNo, 'p'))
        self._files.append(U(region, time, processorNo))
        self._files.append(T(region, time, processorNo))

        if ModelsDB.isMultiphaseModelOn():
            for mid in region.secondaryMaterials:
                self._files.append(Alpha(region, time, processorNo, mid))
            if findSolver() == 'multiphaseInterFoam':  # multiphaseInterFoam requires field file for all the phases
                self._files.append(Alpha(region, time, processorNo, region.mid))

        elif ModelsDB.isSpeciesModelOn():
            for mid, name in MaterialDB.getSpecies(region.mid).items():
                self._files.append(Specie(region, time, processorNo, mid, name))

        for scalarID, fieldName in self._db.getUserDefinedScalarsInRegion(region.rname):
            self._files.append(Scalar(region, time, processorNo, scalarID, fieldName))

    async def setupCase(self):
        self._canceled = False
        self.progress.emit(self.tr('Generating case'))

        caseRoot = FileSystem.caseRoot()

        processorFolders = FileSystem.processorFolders()
        nProcessorFolders = len(processorFolders)

        if nProcessorFolders > 0 and len(FileSystem.times()) > 0:
            self.progress.emit(self.tr(f'Reconstructing Field Data...'))

            if FileSystem.latestTime() == '0':
                self._cm = RunUtility('reconstructPar', '-allRegions', '-withZero', '-case', caseRoot, cwd=caseRoot)
            else:
                self._cm = RunUtility('reconstructPar', '-allRegions', '-latestTime', '-case', caseRoot, cwd=caseRoot)
            await self._cm.start()
            result = await self._cm.wait()
            self._cm = None
            if result != 0:
                raise RuntimeError(self.tr('Reconstructing Field Data failed. 0'))

        self.progress.emit(self.tr(f'Generating Files...'))

        if errors := self._gatherFiles():
            raise RuntimeError(errors)

        errors = await asyncio.to_thread(self._generateFiles)
        if self._canceled:
            raise CanceledException
        if errors:
            raise RuntimeError(self.tr('Case generating fail. - ') + errors)

        if nProcessorFolders > 1:
            self.progress.emit(self.tr('Decomposing Field Data...'))

            console = app.window.dockView.consoleView()
            self._cm = RunUtility('decomposePar', '-allRegions', '-fields', '-latestTime', '-case', caseRoot, cwd=caseRoot)
            self._cm.output.connect(console.append)
            self._cm.errorOutput.connect(console.append)

            await self._cm.start()
            result = await self._cm.wait()

            self._cm = None
            if self._canceled:
                raise CanceledException
            if result != 0:
                raise RuntimeError(self.tr('Decomposing Field Data failed.'))

            self.progress.emit(self.tr(f'Field Data Decomposition Done'))

            for time in FileSystem.times(parent=caseRoot):
                utils.rmtree(caseRoot / time)

    async def initialize(self):
        self._canceled = False

        for rname in self._db.getRegions():
            if await self._initializeRegion(rname) != 0:
                raise RuntimeError
            if self._canceled:
                raise CanceledException

    def cancel(self):
        self._canceled = True
        if self._cm is not None:
            self._cm.cancel()

    async def _initializeRegion(self, rname):
        sectionNames: [str] = coredb.CoreDB().getList(
            f'.//regions/region[name="{rname}"]/initialization/advanced/sections/section/name')
        if len(sectionNames) > 0:
            self.progress.emit(self.tr('Setting Section Values'))

            caseRoot = FileSystem.caseRoot()
            if rname:
                self._cm = RunParallelUtility('setFields', '-writeBoundaryFields', '-case', caseRoot, '-region', rname,
                                              cwd=caseRoot, parallel=parallel.getEnvironment())
            else:
                self._cm = RunParallelUtility('setFields', '-writeBoundaryFields', '-case', caseRoot,
                                              cwd=caseRoot, parallel=parallel.getEnvironment())

            await self._cm.start()

            return await self._cm.wait()

        return 0
