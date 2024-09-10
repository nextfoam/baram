#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from libbaram.run import RunUtility, RunParallelUtility
from libbaram.simple_db.simple_schema import DBError
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType, Shape, CFDType
from baramMesh.openfoam.redistribution_task import RedistributionTask
from baramMesh.openfoam.system.block_mesh_dict import BlockMeshDict
from baramMesh.view.step_page import StepPage


class BaseGridPage(StepPage):
    OUTPUT_TIME = 0

    def __init__(self, ui):
        super().__init__(ui, ui.baseGridPage)

        self._xLen = None
        self._yLen = None
        self._zLen = None
        self._boundingHex6 = None
        self._loaded = False

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        return app.fileSystem.boundaryFilePath().exists()

    def open(self):
        self._load()
        self._updatePage()

    async def selected(self):
        if not self._loaded:
            self._load()

        self._updatePage()
        self.updateMesh()

    async def save(self):
        try:
            db = app.db.checkout('baseGrid')

            if self._ui.useHex6.isChecked():
                name = self._ui.boundingHex6.currentText()
                gId, _ = self._getHex6ByName(name)
                if gId is not None:
                    db.setValue('boundingHex6', gId, self.tr('Hex6 for Base Grid'))
            else:  # not self._ui.useHex6.isChecked():
                db.setValue('boundingHex6', None, self.tr('Hex6 for Base Grid'))

            db.setValue('numCellsX', self._ui.numCellsX.text(), self.tr('Number of Cells'))
            db.setValue('numCellsY', self._ui.numCellsY.text(), self.tr('Number of Cells'))
            db.setValue('numCellsZ', self._ui.numCellsZ.text(), self.tr('Number of Cells'))

            app.db.commit(db)

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def _outputPath(self):
        return app.fileSystem.polyMeshPath()

    def _connectSignalsSlots(self):
        self._ui.useHex6.toggled.connect(self._useHex6Toggled)
        self._ui.boundingHex6.currentTextChanged.connect(self._boundingHex6Changed)

        self._ui.numCellsX.editingFinished.connect(self._updateCellX)
        self._ui.numCellsY.editingFinished.connect(self._updateCellY)
        self._ui.numCellsZ.editingFinished.connect(self._updateCellZ)
        self._ui.generate.clicked.connect(self._generate)
        self._ui.baseGridReset.clicked.connect(self._reset)

    def _updateBoundingBox(self, x1, x2, y1, y2, z1, z2):
        self._xLen = x2 - x1
        self._yLen = y2 - y1
        self._zLen = z2 - z1

        self._ui.xMin.setText('{:.6g}'.format(x1))
        self._ui.xMax.setText('{:.6g}'.format(x2))
        self._ui.xLen.setText('{:.6g}'.format(self._xLen))
        self._ui.yMin.setText('{:.6g}'.format(y1))
        self._ui.yMax.setText('{:.6g}'.format(y2))
        self._ui.yLen.setText('{:.6g}'.format(self._yLen))
        self._ui.zMin.setText('{:.6g}'.format(z1))
        self._ui.zMax.setText('{:.6g}'.format(z2))
        self._ui.zLen.setText('{:.6g}'.format(self._zLen))

        self._updateCellX()
        self._updateCellY()
        self._updateCellZ()

    def _load(self):
        self._boundingHex6 = app.db.getValue('baseGrid/boundingHex6')  # can be "None"

        self._ui.numCellsX.setText(app.db.getValue('baseGrid/numCellsX'))
        self._ui.numCellsY.setText(app.db.getValue('baseGrid/numCellsY'))
        self._ui.numCellsZ.setText(app.db.getValue('baseGrid/numCellsZ'))

        self._loaded = True

    def _useHex6Toggled(self, checked):
        if checked:
            name = self._ui.boundingHex6.currentText()
            gId, geometry = self._getHex6ByName(name)
            if geometry is None:
                QMessageBox.information(self._widget, self.tr('Error'), self.tr('Cannot find Hex6 of the name ') + name )
                return
            self._boundingHex6 = gId
            x1, y1, z1 = geometry.vector('point1')
            x2, y2, z2 = geometry.vector('point2')
        else:
            self._boundingHex6 = None
            x1, x2, y1, y2, z1, z2 = app.window.geometryManager.getBounds().toTuple()

        self._updateBoundingBox(x1, x2, y1, y2, z1, z2)

    def _boundingHex6Changed(self, name):
        if not self._ui.useHex6.isChecked():
            return

        gId, geometry = self._getHex6ByName(name)
        if geometry is None:
            QMessageBox.information(self._widget, self.tr('Error'), self.tr('Cannot find Hex6 of the name ') + name)
            return

        self._boundingHex6 = gId

        x1, y1, z1 = geometry.vector('point1')
        x2, y2, z2 = geometry.vector('point2')

        self._updateBoundingBox(x1, x2, y1, y2, z1, z2)

    def _updateCellX(self):
        count = int(self._ui.numCellsX.text())
        if count == 0:
            return
        self._ui.xCell.setText('{:.6g}'.format(self._xLen / count))

    def _updateCellY(self):
        count = int(self._ui.numCellsY.text())
        if count == 0:
            return
        self._ui.yCell.setText('{:.6g}'.format(self._yLen / count))

    def _updateCellZ(self):
        count = int(self._ui.numCellsZ.text())
        if count == 0:
            return
        self._ui.zCell.setText('{:.6g}'.format(self._zLen / count))

    def _validate(self) -> (bool, str):
        if int(self._ui.numCellsX.text()) < 2 \
                or int(self._ui.numCellsY.text()) < 2 \
                or int(self._ui.numCellsZ.text()) < 2:
            return False, self.tr('Number of Cells per Direction should be greater than 1')

        return True, ''

    @qasync.asyncSlot()
    async def _generate(self):
        valid, msg = self._validate()
        if not valid:
            await AsyncMessageBox().warning(self._widget, self.tr('Warning'), msg)
            return

        await self.save()

        progressDialog = ProgressDialog(self._widget, self.tr('Base Grid Generating'))
        progressDialog.setLabelText(self.tr('Generating Block Mesh'))
        progressDialog.open()

        console = app.consoleView
        console.clear()

        BlockMeshDict().build().write()
        cm = RunUtility('blockMesh', cwd=app.fileSystem.caseRoot())
        cm.output.connect(console.append)
        cm.errorOutput.connect(console.appendError)
        await cm.start()
        result = await cm.wait()

        if result != 0:
            progressDialog.finish(self.tr('Mesh Generation Failed.'))
            self.clearResult()
            return

        numCores = app.project.parallelCores()
        if numCores > 1:
            progressDialog.setLabelText('Decomposing Case')

            redistributionTask = RedistributionTask(app.fileSystem)
            redistributionTask.progress.connect(progressDialog.setLabelText)

            await redistributionTask.decompose(numCores)

        progressDialog.setLabelText('Collecting Mesh Info.')
        cm = RunParallelUtility('checkMesh', '-allRegions', '-writeFields', '(cellAspectRatio cellVolume nonOrthoAngle skewness)', '-time', str(self.OUTPUT_TIME), '-case', app.fileSystem.caseRoot(),
                                cwd=app.fileSystem.caseRoot(), parallel=app.project.parallelEnvironment())
        cm.output.connect(console.append)
        cm.errorOutput.connect(console.appendError)
        await cm.start()
        await cm.wait()

        progressDialog.close()

        await app.window.meshManager.load(self.OUTPUT_TIME)
        self._updatePage()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updatePage()

    def _updatePage(self):
        self._ui.useHex6.toggled.disconnect(self._useHex6Toggled)
        self._ui.boundingHex6.currentTextChanged.disconnect(self._boundingHex6Changed)

        self._ui.boundingHex6.clear()
        if hex6List := self._getHex6List():
            self._ui.boundingHex6.addItems(hex6List)
            self._ui.boundingHex6.setCurrentIndex(0)
            self._ui.useHex6.setEnabled(True)
        else:
            self._ui.useHex6.setEnabled(False)

        if geometry := self._getHex6ById(self._boundingHex6):
            self._ui.useHex6.setChecked(True)
            self._ui.boundingHex6.setCurrentText(geometry.value('name'))
            x1, y1, z1 = geometry.vector('point1')
            x2, y2, z2 = geometry.vector('point2')
        else:
            self._boundingHex6 = None
            self._ui.useHex6.setChecked(False)
            x1, x2, y1, y2, z1, z2 = app.window.geometryManager.getBounds().toTuple()

        self._updateBoundingBox(x1, x2, y1, y2, z1, z2)

        self._ui.useHex6.toggled.connect(self._useHex6Toggled)
        self._ui.boundingHex6.currentTextChanged.connect(self._boundingHex6Changed)

        if self.isNextStepAvailable():
            self._ui.generate.hide()
            self._ui.baseGridReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.generate.show()
            self._ui.baseGridReset.hide()
            self._setNextStepEnabled(False)

    def _showPreviousMesh(self):
        app.window.meshManager.unload()

    def _getHex6ByName(self, name):
        gId, geometry = app.db.findElement('geometry', lambda i, e: e['name'] == name)
        if self._isHex6(gId, geometry):
            return gId, geometry

        return None

    def _getHex6ById(self, gId):
        if gId is None:
            return None

        geometry = app.db.getElement('geometry', gId)
        if self._isHex6(gId, geometry):
            return geometry

        return None

    def _getHex6List(self):
        names = []
        for gId, geometry in app.db.getElements(
                'geometry',
                lambda i, e: e['gType'] == GeometryType.VOLUME.value and e['shape'] == Shape.HEX6.value).items():
            if self._isHex6(gId, geometry):
                names.append(geometry.value('name'))

        return sorted(names)

    def _isHex6(self, gId, geometry):
        if geometry is None:
            return False

        if geometry.value('gType') != GeometryType.VOLUME.value and geometry.value('shape') != Shape.HEX6.value:
            return False

        if app.db.getKeys('geometry', lambda i, e: e['volume'] == gId and e['cfdType'] != CFDType.BOUNDARY.value):
            return False

        return True
