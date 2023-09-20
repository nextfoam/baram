#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio

from PySide6.QtCore import QObject, Signal

from baram.coredb import coredb
from libbaram import utils
from baram.openfoam import parallel
from baram.openfoam.file_system import FileSystem
from baram.openfoam.polymesh.polymesh_loader import PolyMeshLoader
from libbaram.run import runUtility
from baram.openfoam.system.decomposePar_dict import DecomposeParDict

logger = logging.getLogger(__name__)


class RedistributionTask(QObject):
    progress = Signal(str)

    async def redistribute(self):
        caseRoot = FileSystem.caseRoot()
        db = coredb.CoreDB()

        numCores = parallel.getNP()

        processorFolders = FileSystem.processorFolders()
        nProcessorFolders = len(processorFolders)

        if numCores == nProcessorFolders:
            return

        if numCores == 1 and nProcessorFolders == 0:
            return

        try:
            if nProcessorFolders > 0 and len(FileSystem.times()) > 0:
                self.progress.emit(self.tr('Reconstructing the case.'))

                latestTime = FileSystem.latestTime()
                proc = await runUtility('reconstructPar', '-allRegions', '-withZero', '-case', caseRoot,
                                        cwd=caseRoot, stdout=asyncio.subprocess.PIPE)

                # This loop will end if the PIPE is closed (i.e. the process terminates)
                async for line in proc.stdout:
                    log = line.decode('utf-8')
                    if log.startswith('Time = '):
                        self.progress.emit(self.tr(f'Reconstructing the case. ({log.strip()}/{latestTime})'))

                result = await proc.wait()
                if result != 0:
                    raise RuntimeError(self.tr('Reconstruction failed.'))

            for folder in processorFolders:
                utils.rmtree(folder)

            if numCores > 1:
                self.progress.emit(self.tr('Decomposing the case.'))

                regions = db.getRegions()
                for rname in regions:
                    DecomposeParDict(rname).build().write()
                if len(regions) > 1:
                    DecomposeParDict().build().write()

                proc = await runUtility('decomposePar', '-allRegions', '-time', '0:', '-case', caseRoot, cwd=caseRoot)

                result = await proc.wait()
                if result != 0:
                    raise RuntimeError(self.tr('Decomposition failed.'))

                # Delete time folders in case root
                #
                # Do NOT delete the polyMesh in case root
                # It was decided to be kept
                #
                for time in FileSystem.times(parent=caseRoot):
                    utils.rmtree(caseRoot / time)

                self.progress.emit(self.tr(f'Decomposition done.'))

            loader = PolyMeshLoader()
            loader.progress.connect(self.progress)
            await loader.loadVtk()

        except Exception as ex:
            logger.info(ex, exc_info=True)
            raise
