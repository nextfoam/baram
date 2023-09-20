#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from libbaram.run import runUtility
from libbaram.utils import rmtree

from baramSnappy.app import app
from baramSnappy.openfoam.system.block_mesh_dict import BlockMeshDict
from baramSnappy.db.simple_schema import DBError
from baramSnappy.view.widgets.progress_dialog_simple import ProgressDialogSimple
from baramSnappy.view.step_page import StepPage


class BaseGridPage(StepPage):
    OUTPUT_TIME = 0

    def __init__(self, ui):
        super().__init__(ui, ui.baseGridPage)

        self._xLen = None
        self._yLen = None
        self._zLen = None
        self._loaded = False

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return app.fileSystem.boundaryFilePath().exists()

    def open(self):
        self._load()
        self._updateControlButtons()

    def selected(self):
        if not self._loaded:
            self._load()

        self._updateControlButtons()
        self._updateMesh()

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
        self._ui.numCellsX.editingFinished.connect(self._updateCellX)
        self._ui.numCellsY.editingFinished.connect(self._updateCellY)
        self._ui.numCellsZ.editingFinished.connect(self._updateCellZ)
        self._ui.generate.clicked.connect(self._generate)
        self._ui.baseGridReset.clicked.connect(self._reset)

    def _load(self):
        bounds = app.window.geometryManager.getBounds()
        self._xLen, self._yLen, self._zLen = bounds.size()

        self._ui.xMin.setText('{:.6g}'.format(bounds.xMin))
        self._ui.xMax.setText('{:.6g}'.format(bounds.xMax))
        self._ui.xLen.setText('{:.6g}'.format(self._xLen))
        self._ui.yMin.setText('{:.6g}'.format(bounds.yMin))
        self._ui.yMax.setText('{:.6g}'.format(bounds.yMax))
        self._ui.yLen.setText('{:.6g}'.format(self._yLen))
        self._ui.zMin.setText('{:.6g}'.format(bounds.zMin))
        self._ui.zMax.setText('{:.6g}'.format(bounds.zMax))
        self._ui.zLen.setText('{:.6g}'.format(self._zLen))

        self._ui.numCellsX.setText(app.db.getValue('baseGrid/numCellsX'))
        self._ui.numCellsY.setText(app.db.getValue('baseGrid/numCellsY'))
        self._ui.numCellsZ.setText(app.db.getValue('baseGrid/numCellsZ'))

        self._updateCellX()
        self._updateCellY()
        self._updateCellZ()

        self._loaded = True

    def _updateCellX(self):
        self._ui.xCell.setText('{:.6g}'.format(self._xLen / int(self._ui.numCellsX.text())))

    def _updateCellY(self):
        self._ui.yCell.setText('{:.6g}'.format(self._yLen / int(self._ui.numCellsY.text())))

    def _updateCellZ(self):
        self._ui.zCell.setText('{:.6g}'.format(self._zLen / int(self._ui.numCellsZ.text())))

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
            self.clearResult()
            return

        progressDialog.close()

        await app.window.meshManager.load(self.OUTPUT_TIME)
        self._updateControlButtons()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.generate.hide()
            self._ui.baseGridReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.generate.show()
            self._ui.baseGridReset.hide()
            self._setNextStepEnabled(False)

    def _showPreviousMesh(self):
        app.window.meshManager.hide()
