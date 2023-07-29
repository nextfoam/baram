#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from app import app
from libbaram.run import runUtility
from libbaram.utils import formatWithSignificants
from openfoam.system.block_mesh_dict import BlockMeshDict
from db.simple_schema import DBError
from view.widgets.progress_dialog_simple import ProgressDialogSimple
from view.step_page import StepPage
from .base_grid_page_ui import Ui_BaseGridPage


class BaseGridPage(StepPage):
    def __init__(self):
        super().__init__()
        self._ui = Ui_BaseGridPage()
        self._ui.setupUi(self)

        self._dbElement = None
        self._bounds = None

        self._connectSignalsSlots()

        self._load()

    def showEvent(self, ev):
        if not ev.spontaneous():
            app.window.geometryManager.showActors()

            if app.fileSystem.boundaryFilePath().exists():
                app.window.meshManager.showActors()
            else:
                app.window.meshManager.hideActors()

        return super().showEvent(ev)

    def _connectSignalsSlots(self):
        self._ui.generate.clicked.connect(self._generate)

    def _load(self):
        self._bounds = app.window.geometryManager.getBounds()

        self._ui.xMin.setText(formatWithSignificants(float(self._bounds.xMin), 4))
        self._ui.xMax.setText(formatWithSignificants(float(self._bounds.xMax), 4))
        self._ui.yMin.setText(formatWithSignificants(float(self._bounds.yMin), 4))
        self._ui.yMax.setText(formatWithSignificants(float(self._bounds.yMax), 4))
        self._ui.zMin.setText(formatWithSignificants(float(self._bounds.zMin), 4))
        self._ui.zMax.setText(formatWithSignificants(float(self._bounds.zMax), 4))

        self._dbElement = app.db.checkout('baseGrid')
        self._ui.numCellsX.setText(self._dbElement.getValue('numCellsX'))
        self._ui.numCellsY.setText(self._dbElement.getValue('numCellsY'))
        self._ui.numCellsZ.setText(self._dbElement.getValue('numCellsZ'))

    @qasync.asyncSlot()
    async def _generate(self):
        try:
            db = app.db.checkout('baseGrid')

            db.setValue('numCellsX', self._ui.numCellsX.text(), self.tr('Number of Cells'))
            db.setValue('numCellsY', self._ui.numCellsY.text(), self.tr('Number of Cells'))
            db.setValue('numCellsZ', self._ui.numCellsZ.text(), self.tr('Number of Cells'))

            app.db.commit(db)
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())
            return

        progressDialog = ProgressDialogSimple(self, self.tr('Base Grid Generating'))
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

        self._updateNextStepAvailable()
