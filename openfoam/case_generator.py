#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Optional

from PySide6.QtCore import QCoreApplication, QObject, Signal

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

    def getErrors(self):
        return self._errors

    def _generateFiles(self):
        if errors := self._validate():
            return errors

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

        return errors

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
