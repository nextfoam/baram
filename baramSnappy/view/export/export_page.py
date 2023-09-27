#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import shutil
from pathlib import Path

import qasync
from PySide6.QtWidgets import QMessageBox, QFileDialog

from libbaram.openfoam.constants import Directory
from libbaram.process import Processor, ProcessError
from libbaram.run import runParallelUtility
from resources import resource
from widgets.progress_dialog import ProgressDialog

from baramSnappy.app import app
from baramSnappy.openfoam.file_system import FileSystem
from baramSnappy.openfoam.constant.region_properties import RegionProperties
from baramSnappy.openfoam.redistribution_task import RedistributionTask
from baramSnappy.openfoam.system.topo_set_dict import TopoSetDict
from baramSnappy.view.step_page import StepPage


class ExportPage(StepPage):
    OUTPUT_TIME = 4

    def __init__(self, ui):
        super().__init__(ui, ui.exportPage)

        self._dialog = None
        # self._fileDialog = QFileDialog(self._widget, Qt.WindowType.Widget)
        # self._fileDialog.setWindowFlags(self._fileDialog.windowFlags() & ~Qt.Dialog)
        # self._fileDialog.setFileMode(QFileDialog.FileMode.Directory)
        # self._fileDialog.setViewMode(QFileDialog.ViewMode.List)
        # self._widget.layout().addWidget(self._fileDialog)

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return False

    def _connectSignalsSlots(self):
        self._ui.export_.clicked.connect(self._openFileDialog)

    @qasync.asyncSlot()
    async def _openFileDialog(self):
        self._dialog = QFileDialog(self._widget, self.tr('Select Folder'))
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        self._dialog.fileSelected.connect(self._export)
        self._dialog.rejected.connect(self._ui.menubar.repaint)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _export(self, file):
        path = Path(file)
        try:
            self.lock()

            self.clearResult()

            console = app.consoleView
            console.clear()

            fileSystem = app.fileSystem
            parallel = app.project.parallelEnvironment()

            if app.db.elementCount('region') > 1:
                proc = await runParallelUtility('splitMeshRegions', '-cellZonesOnly', cwd=fileSystem.caseRoot(),
                                                parallel=parallel,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                processor = Processor(proc)
                processor.outputLogged.connect(console.append)
                processor.errorLogged.connect(console.appendError)
                await processor.run()

            if not fileSystem.timePathExists(self.OUTPUT_TIME, parallel.isParallelOn()):
                progressDialog = ProgressDialog(self._widget, self.tr('Mesh Exporting'))
                progressDialog.setLabelText(self.tr('Copying Files'))
                progressDialog.open()

                if parallel.isParallelOn():
                    for n in range(parallel.np()):
                        if not await fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 1, self.OUTPUT_TIME, n):
                            await fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 2, self.OUTPUT_TIME, n)
                elif not await fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 1, self.OUTPUT_TIME):
                    await fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 2, self.OUTPUT_TIME)

                progressDialog.close()

            toposetDict = TopoSetDict().build(TopoSetDict.Mode.CREATE_CELL_ZONES)
            regions = app.db.getElements('region', None, ['name'])
            if toposetDict.isBuilt():
                if len(regions) == 1:
                    toposetDict.write()
                    proc = await runParallelUtility('topoSet', cwd=fileSystem.caseRoot(), parallel=parallel,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    processor = Processor(proc)
                    processor.outputLogged.connect(console.append)
                    processor.errorLogged.connect(console.appendError)
                    await processor.run()
                else:
                    for region in regions.values():
                        rname = region['name']
                        toposetDict.setRegion(rname).write()
                        proc = await runParallelUtility('topoSet', '-region', rname, cwd=fileSystem.caseRoot(),
                                                        parallel=parallel,
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        processor = Processor(proc)
                        processor.outputLogged.connect(console.append)
                        processor.errorLogged.connect(console.appendError)
                        await processor.run()

            path.mkdir(parents=True, exist_ok=True)
            baramSystem = FileSystem(path)
            baramSystem.createCase(resource.file('openfoam/case'))

            if len(regions) > 1:
                RegionProperties(baramSystem.caseRoot()).build().write()

            if parallel.isParallelOn():
                progressDialog = ProgressDialog(self._widget, self.tr('Mesh Exporting'))
                progressDialog.setLabelText(self.tr('Copying Files'))
                progressDialog.open()

                for n in range(parallel.np()):
                    p = baramSystem.processorPath(n, False)
                    p.mkdir()
                    shutil.move(fileSystem.timePath(self.OUTPUT_TIME, n), p / Directory.CONSTANT_DIRECTORY_NAME)

                redistributionTask = RedistributionTask(baramSystem)
                redistributionTask.progress.connect(progressDialog.setLabelText)

                await redistributionTask.reconstruct()

                progressDialog.finish(self.tr('Export is complete.'))
            else:
                shutil.move(self._outputPath() / Directory.POLY_MESH_DIRECTORY_NAME, baramSystem.polyMeshPath())
                QMessageBox.information(self._widget, self.tr('Mesh Exporting'), self.tr('Export is complete.'))
        except ProcessError as e:
            self.clearResult()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Export failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()
