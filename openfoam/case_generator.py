#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Optional

from PySide6.QtCore import QCoreApplication, QObject, Signal

from coredb import coredb
from coredb.region_db import RegionDB
from coredb.boundary_db import BoundaryDB
from coredb.models_db import ModelsDB
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
from openfoam.boundary_conditions.alpha import Alpha
from openfoam.run import runUtility
from openfoam.system.fv_solution import FvSolution
from openfoam.system.control_dict import ControlDict
from openfoam.system.fv_schemes import FvSchemes
from openfoam.system.fv_options import FvOptions
from openfoam.system.decomposePar_dict import DecomposeParDict
from openfoam.system.set_fields_dict import SetFieldsDict
from openfoam.polymesh.boundary import Boundary
from openfoam.file_system import FileSystem
from libbaram import utils


logger = logging.getLogger(__name__)


class CaseGenerator(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()
        self._db = coredb.CoreDB()
        self._errors = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._cancelled: bool = False
        self._files = None

    def getErrors(self):
        return self._errors

    def _gatherFiles(self):
        if errors := self._validate():
            return errors

        regions = self._db.getRegions()
        self._files = []
        for rname in regions:
            region = RegionDB.getRegionProperties(rname)

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
                self._gatherBoundaryConditionsFiles(region, path, processorNo)
                processorNo += 1

            if processorNo == 0:
                self._gatherBoundaryConditionsFiles(region, FileSystem.caseRoot())

            self._files.append(FvSchemes(rname))
            self._files.append(FvSolution(rname))
            self._files.append(FvOptions(rname))
            self._files.append(DecomposeParDict(rname))
            self._files.append(SetFieldsDict(rname))

        if len(regions) > 1:
            self._files.append(FvSolution())
            self._files.append(RegionProperties())

        self._files.append(G())

        self._files.append(ControlDict())

        self._files.append(DecomposeParDict())

        return errors

    def _generateFiles(self):
        for file in self._files:
            if self._cancelled:
                return
            file.build().write()

    @classmethod
    def createCase(cls):
        FileSystem.setupNewCase()
        ControlDict().copyFromResource('openfoam/controlDict')

    def _validate(self):
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

    async def setupCase(self):
        self._cancelled = False
        self.progress.emit(self.tr('Generating case'))

        caseRoot = FileSystem.caseRoot()

        numCores = int(self._db.getValue('.//runCalculation/parallel/numberOfCores'))
        processorFolders = list(caseRoot.glob('processor[0-9]*'))
        nProcessorFolders = len(processorFolders)

        try:
            # Reconstruct the case if necessary.
            if nProcessorFolders > 0 and nProcessorFolders != numCores:
                latestTime = max([f.name for f in (caseRoot / 'processor0').glob('[0-9.]*') if f.name.count('.') < 2],
                                 key=lambda x: float(x))
                self._proc = await runUtility('reconstructPar', '-allRegions', '-newTimes', '-case', caseRoot, cwd=caseRoot)

                self.progress.emit(self.tr('Reconstructing the case.'))

                # This loop will end if the PIPE is closed (i.e. the process terminates)
                async for line in self._proc.stdout:
                    log = line.decode('utf-8')
                    if log.startswith('Time = '):
                        self.progress.emit(self.tr(f'Reconstructing the case. ({log.strip()}/{latestTime})'))

                result = await self._proc.wait()
                self._proc = None
                if self._cancelled:
                    return self._cancelled
                elif result != 0:
                    raise RuntimeError(self.tr('Reconstruction failed.'))

                nProcessorFolders = 0

                for folder in processorFolders:
                    utils.rmtree(folder)

            self.progress.emit(self.tr(f'Generating Files...'))

            self._gatherFiles()
            errors = await asyncio.to_thread(self._generateFiles)
            if self._cancelled:
                return self._cancelled
            elif errors:
                raise RuntimeError(self.tr('Case generating fail. - ' + errors))

            # Decompose the case if necessary.
            if numCores > 1 and nProcessorFolders == 0:
                self._proc = await runUtility('decomposePar', '-allRegions', '-case', caseRoot, cwd=caseRoot)

                self.progress.emit(self.tr('Decomposing the case.'))

                result = await self._proc.wait()
                self._proc = None
                if self._cancelled:
                    return self._cancelled
                elif result != 0:
                    raise RuntimeError(self.tr('Decomposing failed.'))

            return self._cancelled

        except Exception as ex:
            logger.info(ex, exc_info=True)
            raise

    def cancel(self):
        self._cancelled = True
        if self._proc is not None:
            self._proc.terminate()
