#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import shutil

from PySide6.QtCore import QObject, Signal

from libbaram import utils
from libbaram.run import runUtility
from libbaram.openfoam.dictionary.decomposePar_dict import DecomposeParDict

from baramSnappy.app import app

logger = logging.getLogger(__name__)


class RedistributionTask(QObject):
    progress = Signal(str)

    def __init__(self, fileSystem):
        super().__init__()

        self._fileSystem = fileSystem

    async def redistribute(self, numCores):
        processorFolders = self._fileSystem.processorFolders()
        nProcessorFolders = len(processorFolders)

        if numCores == nProcessorFolders:
            return

        if numCores == 1 and nProcessorFolders == 0:
            return

        try:
            await self.reconstruct()
            await self.decompose(numCores)
            await app.window.meshManager.load()

        except Exception as ex:
            logger.info(ex, exc_info=True)
            raise

    async def reconstruct(self):
        caseRoot = self._fileSystem.caseRoot()

        processorFolders = self._fileSystem.processorFolders()
        nProcessorFolders = len(processorFolders)

        if nProcessorFolders > 0:
            self.progress.emit(self.tr('Reconstructing the case.'))

            latestTime = self._fileSystem.latestTime(self._fileSystem.processorPath(0))
            proc = await runUtility('reconstructParMesh', '-allRegions', '-constant', '-case', caseRoot,
                                    cwd=caseRoot, stdout=asyncio.subprocess.PIPE)

            # This loop will end if the PIPE is closed (i.e. the process terminates)
            async for line in proc.stdout:
                log = line.decode('utf-8')
                if log.startswith('Time = constant'):
                    self.progress.emit(self.tr(f'Reconstructing the case. (constant)'))
                elif log.startswith('Time = '):
                    self.progress.emit(self.tr(f'Reconstructing the case. ({log.strip()}/{latestTime})'))

            result = await proc.wait()
            if result != 0:
                raise RuntimeError(self.tr('Reconstruction failed.'))

        for folder in processorFolders:
            utils.rmtree(folder)

    async def decompose(self, numCores):
        if numCores > 1 and self._fileSystem.boundaryFilePath().exists():
            caseRoot = self._fileSystem.caseRoot()

            self.progress.emit(self.tr('Decomposing the case.'))

            tempPath = self._fileSystem.caseRoot() / 'decomposing'
            if tempPath.exists():
                utils.rmtree(tempPath)

            tempPath.mkdir()

            DecomposeParDict(self._fileSystem.caseRoot(), numCores).build().write()
            proc = await runUtility('decomposePar', '-time', 'none', '-case', caseRoot, cwd=caseRoot)

            result = await proc.wait()
            if result != 0:
                raise RuntimeError(self.tr('Decomposition failed.'))

            for i in range(numCores):
                p = self._fileSystem.processorPath(i)
                p.rename(tempPath / p.name)

            t = 1
            while self._fileSystem.timePath(t).is_dir():
                time = str(t)
                proc = await runUtility('decomposePar', '-time', time, '-case', caseRoot, cwd=caseRoot)

                result = await proc.wait()
                if result != 0:
                    raise RuntimeError(self.tr('Decomposition failed.'))

                for i in range(numCores):
                    processorFolder = self._fileSystem.processorPath(i)
                    timeFolder = processorFolder / time
                    timeFolder.rename(tempPath / processorFolder.name / time)
                    shutil.rmtree(processorFolder)

                t += 1

            for i in range(numCores):
                folderName = f'processor{i}'
                p = tempPath / folderName
                p.rename(caseRoot / folderName)

            shutil.rmtree(tempPath)

            # Delete time folders in case root
            #
            # Do NOT delete the polyMesh in case root
            # It was decided to be kept
            #
            for time in self._fileSystem.times(parent=caseRoot):
                utils.rmtree(caseRoot / time)

            self.progress.emit(self.tr(f'Decomposition done.'))
