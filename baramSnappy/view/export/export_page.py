#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from pathlib import Path

import qasync
from PySide6.QtWidgets import QMessageBox, QFileDialog

from libbaram.process import Processor, ProcessError
from libbaram.run import runUtility
from libbaram.utils import rmtree

from baramSnappy.app import app
from baramSnappy.openfoam.file_system import FileSystem
from baramSnappy.openfoam.constant.region_properties import RegionProperties
from baramSnappy.openfoam.system.topo_set_dict import TopoSetDict
from baramSnappy.view.widgets.progress_dialog_simple import ProgressDialogSimple
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
        # self._ui.export_.clicked.connect(self._export)

    def _openFileDialog(self):
        self._dialog = QFileDialog(self._widget, self.tr('Select Location'))
        self._dialog.setFileMode(QFileDialog.FileMode.Directory)
        self._dialog.fileSelected.connect(self._pathSelected)
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self._dialog.open()

    def _pathSelected(self, path):
        self._export(Path(path))

    @qasync.asyncSlot()
    async def _export(self, path: Path):
        try:
            self.lock()

            outputPath = app.fileSystem.timePath(self.OUTPUT_TIME)
            if outputPath.exists():
                rmtree(outputPath)

            console = app.consoleView
            console.clear()

            if app.db.elementCount('region') > 1:
                proc = await runUtility('splitMeshRegions', '-cellZonesOnly', cwd=app.fileSystem.caseRoot(),
                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                processor = Processor(proc)
                processor.outputLogged.connect(console.append)
                processor.errorLogged.connect(console.appendError)
                await processor.run()

            if not outputPath.exists():
                progressDialog = ProgressDialogSimple(self._widget, self.tr('Base Grid Generating'))
                progressDialog.setLabelText(self.tr('Generating Block Mesh'))
                progressDialog.open()

                if not await app.fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 1, self.OUTPUT_TIME):
                    await app.fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 2, self.OUTPUT_TIME)

                progressDialog.close()

            toposetDict = TopoSetDict().build(TopoSetDict.Mode.CREATE_CELL_ZONES)
            if toposetDict.isBuilt():
                regions = app.db.getElements('region', None, ['name'])
                if len(regions) == 1:
                    toposetDict.write()
                    proc = await runUtility('topoSet', cwd=app.fileSystem.caseRoot(),
                                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    processor = Processor(proc)
                    processor.outputLogged.connect(console.append)
                    processor.errorLogged.connect(console.appendError)
                    await processor.run()
                else:
                    for region in regions.values():
                        rname = region['name']
                        toposetDict.writeByRegion(rname)
                        proc = await runUtility('topoSet', '-region', rname, cwd=app.fileSystem.caseRoot(),
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        processor = Processor(proc)
                        processor.outputLogged.connect(console.append)
                        processor.errorLogged.connect(console.appendError)
                        await processor.run()

            path.mkdir(parents=True, exist_ok=True)
            fileSystem = FileSystem(path)
            fileSystem.createBaramCase()
            outputPath.rename(fileSystem.constantPath())
            RegionProperties(fileSystem).build().write()
        except ProcessError as e:
            self.clearResult()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Castellation Refinement Failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()
