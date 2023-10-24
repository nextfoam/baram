#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio

import qasync
from PySide6.QtWidgets import QMessageBox

from libbaram.run import runParallelUtility
from libbaram.process import Processor, ProcessError

from baramMesh.app import app
from baramMesh.db.simple_schema import DBError
from baramMesh.db.configurations_schema import CFDType
from baramMesh.openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from baramMesh.openfoam.system.topo_set_dict import TopoSetDict
from baramMesh.view.step_page import StepPage


class SnapPage(StepPage):
    OUTPUT_TIME = 2

    def __init__(self, ui):
        super().__init__(ui, ui.snapPage)

        self._processor = None

        self._connectSignalsSlots()

    def selected(self):
        if not self._loaded:
            self._load()

        self._updateMesh()

    def save(self):
        try:
            db = app.db.checkout('snap')

            db.setValue('nSmoothPatch', self._ui.smootingForSurface.text(), self.tr('Smoothing for Surface'))
            db.setValue('nSmoothInternal', self._ui.smootingForInternal.text(), self.tr('Smoothing for Internal'))
            db.setValue('nSolveIter', self._ui.meshDisplacementRelaxation.text(),
                        self.tr('Mesh Displacement Relaxation'))
            db.setValue('nRelaxIter', self._ui.globalSnappingRelaxation.text(), self.tr('Global Snapping Relaxation'))
            db.setValue('nFeatureSnapIter', self._ui.featureSnappingRelaxation.text(),
                        self.tr('Feature Snapping Relaxation'))
            db.setValue('multiRegionFeatureSnap', self._ui.multiSurfaceFeatureSnap.isChecked())
            db.setValue('tolerance', self._ui.tolerance.text(), self.tr('Tolerance'))
            db.setValue('concaveAngle', self._ui.concaveAngle.text(), self.tr('Concave Angle'))
            db.setValue('minAreaRatio', self._ui.minAreaRatio.text(), self.tr('Min. Area Ratio'))

            app.db.commit(db)

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def _connectSignalsSlots(self):
        self._ui.snap.clicked.connect(self._snap)
        self._ui.snapReset.clicked.connect(self._reset)

    def _load(self):
        dbElement = app.db.checkout('snap')
        self._ui.smootingForSurface.setText(dbElement.getValue('nSmoothPatch'))
        self._ui.smootingForInternal.setText(dbElement.getValue('nSmoothInternal'))
        self._ui.meshDisplacementRelaxation.setText(dbElement.getValue('nSolveIter'))
        self._ui.globalSnappingRelaxation.setText(dbElement.getValue('nRelaxIter'))
        self._ui.featureSnappingRelaxation.setText(dbElement.getValue('nFeatureSnapIter'))
        self._ui.multiSurfaceFeatureSnap.setChecked(dbElement.getValue('multiRegionFeatureSnap'))
        self._ui.tolerance.setText(dbElement.getValue('tolerance'))
        self._ui.concaveAngle.setText(dbElement.getValue('concaveAngle'))
        self._ui.minAreaRatio.setText(dbElement.getValue('minAreaRatio'))

        self._updateControlButtons()

    @qasync.asyncSlot()
    async def _snap(self):
        if self._processor:
            self._processor.cancel()
            return

        buttonText = self._ui.snap.text()
        try:
            if not self.save():
                return

            self._ui.snapContents.setEnabled(False)
            self._ui.snap.setText(self.tr('Cancel'))

            console = app.consoleView
            console.clear()

            parallel = app.project.parallelEnvironment()

            snapDict = SnappyHexMeshDict(snap=True).build()
            if app.db.elementCount('region') > 1:
                snapDict.write()
            else:
                snapDict.updateForCellZoneInterfacesSnap().write()

            proc = await runParallelUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot(), parallel=parallel,
                                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            self._processor = Processor(proc)
            self._processor.outputLogged.connect(console.append)
            self._processor.errorLogged.connect(console.appendError)
            await self._processor.run()

            if app.db.elementCount('region') > 1:
                TopoSetDict().build(TopoSetDict.Mode.CREATE_REGIONS).write()
                proc = await runParallelUtility('topoSet', cwd=app.fileSystem.caseRoot(), parallel=parallel,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                self._processor = Processor(proc)
                self._processor.outputLogged.connect(console.append)
                self._processor.errorLogged.connect(console.appendError)
                await self._processor.run()

                if app.db.elementCount('geometry', lambda i, e: e['cfdType'] == CFDType.CELL_ZONE.value):
                    snapDict.updateForCellZoneInterfacesSnap().write()
                    proc = await runParallelUtility('snappyHexMesh', '-overwrite', cwd=app.fileSystem.caseRoot(),
                                                    parallel=parallel,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    self._processor = Processor(proc)
                    self._processor.outputLogged.connect(console.append)
                    self._processor.errorLogged.connect(console.appendError)
                    await self._processor.run()

            await app.window.meshManager.load(self.OUTPUT_TIME)
            self._updateControlButtons()

            QMessageBox.information(self._widget, self.tr('Complete'), self.tr('Snapping is completed.'))
        except ProcessError as e:
            self.clearResult()

            if self._processor.isCanceled():
                QMessageBox.information(self._widget, self.tr('Canceled'), self.tr('Snapping has been canceled.'))
            else:
                QMessageBox.information(self._widget, self.tr('Error'),
                                        self.tr('Snapping Failed. [') + str(e.returncode) + ']')
        finally:
            self._ui.snapContents.setEnabled(True)
            self._ui.snap.setText(buttonText)
            self._processor = None

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.snap.hide()
            self._ui.snapReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.snap.show()
            self._ui.snapReset.hide()
            self._setNextStepEnabled(False)
