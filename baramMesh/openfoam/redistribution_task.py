#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import shutil

from PySide6.QtCore import QObject, Signal

from baramMesh.openfoam.file_system import FileSystem
from libbaram import utils
from libbaram.run import RunUtility
from libbaram.openfoam.dictionary.decomposePar_dict import DecomposeParDict

from baramMesh.app import app

logger = logging.getLogger(__name__)


class RedistributionTask(QObject):
    progress = Signal(str)

    def __init__(self, fileSystem: FileSystem):
        super().__init__()

        self._fileSystem = fileSystem
        self._latestTime = fileSystem.latestTime(fileSystem.processorPath(0))
        self._reconstructMessage = ''

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
            self.progress.emit(self.tr('Reconstructing Case'))
            cm = RunUtility('reconstructParMesh', '-allRegions', '-constant', '-case', caseRoot, cwd=caseRoot)
            cm.output.connect(self._reportTimeProgress)
            self._reconstructMessage = 'Reconstructing Mesh'
            await cm.start()
            result = await cm.wait()
            if result != 0:
                raise RuntimeError(self.tr('Mesh Reconstruction failed.'))

            # Rebuild mesh quality information
            if self._fileSystem.times():  # Exported cases do not have time folders and "reconstructPar" fails
                cm = RunUtility('checkMesh', '-allRegions', '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)',
                                '-case', caseRoot, cwd=caseRoot)
                cm.output.connect(self._reportTimeProgress)
                self._reconstructMessage = 'Rebuilding Mesh Quality Info.'
                await cm.start()
                result = await cm.wait()
                if result != 0:
                    raise RuntimeError(self.tr('Rebuilding Mesh Quality Info. failed.'))

        for folder in processorFolders:
            utils.rmtree(folder)

    async def decompose(self, numCores):
        if numCores > 1 and self._fileSystem.boundaryFilePath().exists():
            caseRoot = self._fileSystem.caseRoot()

            self.progress.emit(self.tr('Decomposing Case'))

            tempPath = self._fileSystem.caseRoot() / 'decomposing'
            if tempPath.exists():
                utils.rmtree(tempPath)

            tempPath.mkdir()

            DecomposeParDict(self._fileSystem.caseRoot(), '', numCores).build().write()
            cm = RunUtility('decomposePar', '-time', 'none', '-case', caseRoot, cwd=caseRoot)
            await cm.start()
            result = await cm.wait()
            if result != 0:
                raise RuntimeError(self.tr('Decomposition failed.'))

            for i in range(numCores):
                p = self._fileSystem.processorPath(i)
                p.rename(tempPath / p.name)

            t = 1
            while self._fileSystem.timePath(t).is_dir():
                time = str(t)
                cm = RunUtility('decomposePar', '-time', time, '-case', caseRoot, cwd=caseRoot)
                await cm.start()
                result = await cm.wait()
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

    def _reportTimeProgress(self, msg):
        if msg.startswith('Time = constant'):
            self.progress.emit(self.tr(f'{self._reconstructMessage} (constant)'))
        elif msg.startswith('Time = '):
            self.progress.emit(self.tr(f'{self._reconstructMessage} ({msg.strip()}/{self._latestTime})'))
