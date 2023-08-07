#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from app import app
from libbaram.run import runUtility
from libbaram.utils import rmtree
from openfoam.system.block_mesh_dict import BlockMeshDict
from db.simple_schema import DBError
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from view.step_page import StepPage


class BaseGridPage(StepPage):
    def __init__(self, ui):
        super().__init__(ui, ui.baseGridPage)

        self._bounds = None
        self._loaded = False

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return app.fileSystem.boundaryFilePath().exists()

    def open(self):
        self._load()

    def selected(self):
        if not self._loaded:
            self._load()

        app.window.geometryManager.showActors()

        if app.fileSystem.boundaryFilePath().exists():
            app.window.meshManager.showActors()
        else:
            app.window.meshManager.hideActors()

    def clearResult(self):
        path = app.fileSystem.polyMeshPath()
        if path.exists():
            rmtree(path)

    def save(self):
        try:
            db = app.db.checkout('baseGrid')

            db.setValue('numCellsX', self._ui.numCellsX.text(), self.tr('Number of Cells'))
            db.setValue('numCellsY', self._ui.numCellsY.text(), self.tr('Number of Cells'))
            db.setValue('numCellsZ', self._ui.numCellsZ.text(), self.tr('Number of Cells'))

            app.db.commit(db)

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def _connectSignalsSlots(self):
        self._ui.generate.clicked.connect(self._generate)

    def _load(self):
        self._bounds = app.window.geometryManager.getBounds()

        self._ui.xMin.setText('{:.6g}'.format(self._bounds.xMin))
        self._ui.xMax.setText('{:.6g}'.format(self._bounds.xMax))
        self._ui.yMin.setText('{:.6g}'.format(self._bounds.yMin))
        self._ui.yMax.setText('{:.6g}'.format(self._bounds.yMax))
        self._ui.zMin.setText('{:.6g}'.format(self._bounds.zMin))
        self._ui.zMax.setText('{:.6g}'.format(self._bounds.zMax))

        self._ui.numCellsX.setText(app.db.getValue('baseGrid/numCellsX'))
        self._ui.numCellsY.setText(app.db.getValue('baseGrid/numCellsY'))
        self._ui.numCellsZ.setText(app.db.getValue('baseGrid/numCellsZ'))

        self._loaded = True

    @qasync.asyncSlot()
    async def _generate(self):
        self.save()

        progressDialog = ProgressDialogSimple(self._widget, self.tr('Base Grid Generating'))
        progressDialog.setLabelText(self.tr('Generating Block Mesh'))
        progressDialog.open()

        BlockMeshDict().build().write()
        proc = await runUtility('blockMesh', cwd=app.fileSystem.caseRoot())
        if await proc.wait():
            progressDialog.finish(self.tr('Mesh Generation Failed.'))

        progressDialog.hideCancelButton()
        meshManager = app.window.meshManager
        meshManager.progress.connect(progressDialog.setLabelText)
        await meshManager.load()

        progressDialog.close()

        self._setNextStepEnabled(True)
