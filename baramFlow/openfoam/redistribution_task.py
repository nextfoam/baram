#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from PySide6.QtCore import QObject, Signal

from baramFlow.app import app
from baramFlow.case_manager import BATCH_DIRECTORY_NAME
from baramFlow.coredb.project import Project
from baramFlow.openfoam.openfoam_reader import OpenFOAMReader
from libbaram import utils
from libbaram.openfoam.constants import CASE_DIRECTORY_NAME
from libbaram.run import RunUtility
from libbaram.openfoam.dictionary.decomposePar_dict import DecomposeParDict

from baramFlow.coredb import coredb
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam import parallel
from baramFlow.openfoam.polymesh.polymesh_loader import PolyMeshLoader

logger = logging.getLogger(__name__)


class RedistributionTask(QObject):
    progress = Signal(str)

    def __init__(self):
        super().__init__()

        self._caseName = ''
        self._latestTime = '0'

    async def redistribute(self):
        db = coredb.CoreDB()
        regions = db.getRegions()

        liveCaseFolder = Project.instance().path.joinpath(CASE_DIRECTORY_NAME)
        batchRoot      = Project.instance().path.joinpath(BATCH_DIRECTORY_NAME)  # noqa: E221
        caseFolders = list(batchRoot.iterdir()) if batchRoot.exists() else []
        caseFolders.insert(0, liveCaseFolder)

        numCores = parallel.getNP()

        nProcessorFolders = len(list(liveCaseFolder.glob('processor[0-9]*')))

        if numCores == nProcessorFolders:
            return

        if numCores == 1 and nProcessorFolders == 0:
            return

        try:
            for caseRoot in caseFolders:
                processorFolders = list(caseRoot.glob('processor[0-9]*'))
                nProcessorFolders = len(processorFolders)
                if nProcessorFolders > 0 and len(FileSystem.times(processorFolders[0])) > 0:
                    self.progress.emit(self.tr('Reconstructing the case.'))

                    if caseRoot == liveCaseFolder:
                        self._caseName = ''
                    else:
                        self._caseName = caseRoot.name

                    self._latestTime = FileSystem.latestTime(processorFolders[0])

                    cm = RunUtility('reconstructPar', '-allRegions', '-withZero', '-case', caseRoot, cwd=caseRoot)
                    cm.output.connect(self._reportTimeProgress)
                    await cm.start()
                    result = await cm.wait()
                    if result != 0:
                        raise RuntimeError(self.tr('Reconstruction failed.'))

            for caseRoot in caseFolders:
                processorFolders = list(caseRoot.glob('processor[0-9]*'))
                for folder in processorFolders:
                    utils.rmtree(folder)

            if numCores > 1:
                self.progress.emit(self.tr('Decomposing the case.'))

                for caseRoot in caseFolders:
                    if caseRoot == liveCaseFolder:
                        decomposeParDict = DecomposeParDict(caseRoot, numCores).build()
                        if len(regions) > 1:
                            decomposeParDict.write()
                        for rname in regions:
                            decomposeParDict.setRegion(rname).write()

                        args = ('-allRegions', '-time', '0:', '-case', caseRoot)
                    else:
                        FileSystem.linkLivePolyMeshTo(liveCaseFolder, caseRoot, regions, processorOnly=True)

                        args = ('-allRegions', '-fields', '-time', '0:', '-case', caseRoot)

                    console = app.window.consoleView()
                    cm = RunUtility('decomposePar', *args, cwd=caseRoot)
                    cm.output.connect(console.append)
                    cm.errorOutput.connect(console.append)

                    app.window.showConsoleDock()
                    await cm.start()
                    result = await cm.wait()
                    if result != 0:
                        raise RuntimeError(self.tr('Decomposition failed.'))

                    # Delete time folders in case root
                    #
                    # Do NOT delete the polyMesh in case root
                    # It was decided to be kept
                    #
                    for time in FileSystem.times(caseRoot):
                        utils.rmtree(caseRoot / time)

                self.progress.emit(self.tr(f'Decomposition done.'))

            async with OpenFOAMReader() as reader:
                await reader.setupReader()

            loader = PolyMeshLoader()
            loader.progress.connect(self.progress)
            await loader.loadVtk()

        except Exception as ex:
            logger.info(ex, exc_info=True)
            raise

    def _reportTimeProgress(self, msg):
        if msg.startswith('Time = '):
            self.progress.emit(self.tr(f'Reconstructing the case. {self._caseName} ({msg.strip()}/{self._latestTime})'))
