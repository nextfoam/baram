#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from app import app
from db.simple_schema import DBError
from openfoam.system.snappy_hex_mesh_dict import SnappyHexMeshDict
from libbaram.run import runUtility
from view.step_page import StepPage
from view.widgets.progress_dialog_simple import ProgressDialogSimple


class SnapPage(StepPage):
    OUTPUT_TIME = 2

    def __init__(self, ui):
        super().__init__(ui, ui.snapPage)

        self._loaded = False

        self._connectSignalsSlots()

    def selected(self):
        if not self._loaded:
            self._load()

    def _connectSignalsSlots(self):
        self._ui.snap.clicked.connect(self._snap)
        self._ui.snapReset.clicked.connect(self._reset)

    def _load(self):
        self._ui.smootingForSurface.setText(app.db.getValue('snap/nSmoothPatch'))
        self._ui.smootingForInternal.setText(app.db.getValue('snap/nSmoothInternal'))
        self._ui.meshDisplacementRelaxation.setText(app.db.getValue('snap/nSolveIter'))
        self._ui.globalSnappingRelaxation.setText(app.db.getValue('snap/nRelaxIter'))
        self._ui.featureSnappingRelaxation.setText(app.db.getValue('snap/nFeatureSnapIter'))
        self._ui.multiSurfaceFeatureSnap.setChecked(app.db.getBool('snap/multiRegionFeatureSnap'))
        self._ui.tolerance.setText(app.db.getValue('snap/tolerance'))
        self._ui.concaveAngle.setText(app.db.getValue('snap/concaveAngle'))
        self._ui.minAreaRatio.setText(app.db.getValue('snap/minAreaRation'))

        self._checkSnapped()

    @qasync.asyncSlot()
    async def _snap(self):
        progressDialog = ProgressDialogSimple(self._widget, self.tr('Snapping'), True)
        progressDialog.setLabelText(self.tr('Updating Configurations'))
        progressDialog.open()

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
            db.setValue('minAreaRation', self._ui.minAreaRatio.text(), self.tr('Min. Area Ratio'))

            app.db.commit(db)
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

        SnappyHexMeshDict(snap=True).build().write()

        progressDialog.setLabelText(self.tr('Snapping'))
        proc = await runUtility('snappyHexMesh', cwd=app.fileSystem.caseRoot())
        if await proc.wait():
            progressDialog.finish(self.tr('Snapping Failed.'))
            return

        progressDialog.hideCancelButton()
        meshManager = app.window.meshManager
        meshManager.clear()
        meshManager.progress.connect(progressDialog.setLabelText)
        await meshManager.load()

        progressDialog.close()

        self._checkSnapped()

    def _reset(self):
        self.clearResult()
        self._checkSnapped()

    def _checkSnapped(self):
        if self.isNextStepAvailable():
            self._ui.snap.hide()
            self._ui.snapReset.show()
            self._setNextStepEnabled(True)
        else:
            self._ui.snap.show()
            self._ui.snapReset.hide()
            self._setNextStepEnabled(False)
