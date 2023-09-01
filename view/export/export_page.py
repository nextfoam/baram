#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from pathlib import Path

import qasync
from PySide6.QtWidgets import QMessageBox, QFileDialog

from app import app
from libbaram.run import runUtility
from libbaram.process import Processor, ProcessError
from libbaram.utils import rmtree
from openfoam.file_system import FileSystem
from openfoam.system.topo_set_dict import TopoSetDict
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from view.step_page import StepPage


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

                await app.fileSystem.copyTimeDrectory(self.OUTPUT_TIME - 1, self.OUTPUT_TIME)

                progressDialog.close()

            TopoSetDict().build(TopoSetDict.Mode.CREATE_CELL_ZONES).write()
            proc = await runUtility('toposet', cwd=app.fileSystem.caseRoot(),
                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            processor = Processor(proc)
            processor.outputLogged.connect(console.append)
            processor.errorLogged.connect(console.appendError)
            await processor.run()

            path.mkdir(parents=True, exist_ok=True)
            outputPath.rename(path / FileSystem.CONSTANT_DIRECTORY_NAME)
        except ProcessError as e:
            self.clearResult()
            QMessageBox.information(self._widget, self.tr('Error'),
                                    self.tr('Castellation Refinement Failed. [') + str(e.returncode) + ']')
        finally:
            self.unlock()
