#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from libbaram.simple_db.simple_schema import ValidationError

from baramMesh.app import app
from .mesh_quality_parameters_dialog_ui import Ui_MeshQualityParametersDialog


class MeshQualityParametersDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MeshQualityParametersDialog()
        self._ui.setupUi(self)

        self._dbElement = app.db.checkout('meshQuality')

        self._ui.maxNonOrtho.setText(self._dbElement.getValue('maxNonOrtho'))
        self._ui.maxNonOrthoRelaxed.setText(self._dbElement.getValue('relaxed/maxNonOrtho'))
        self._ui.maxBoundarySkewness.setText(self._dbElement.getValue('maxBoundarySkewness'))
        self._ui.maxInternalSkewness.setText(self._dbElement.getValue('maxInternalSkewness'))
        self._ui.maxConcave.setText(self._dbElement.getValue('maxConcave'))
        self._ui.minVol.setText(self._dbElement.getValue('minVol'))
        self._ui.minTetQuality.setText(self._dbElement.getValue('minTetQuality'))
        self._ui.minVolCollapseRatio.setText(self._dbElement.getValue('minVolCollapseRatio'))
        self._ui.minArea.setText(self._dbElement.getValue('minArea'))
        self._ui.minTwist.setText(self._dbElement.getValue('minTwist'))
        self._ui.minDeterminant.setText(self._dbElement.getValue('minDeterminant'))
        self._ui.minFaceWeight.setText(self._dbElement.getValue('minFaceWeight'))
        self._ui.minFaceFlatness.setText(self._dbElement.getValue('minFaceFlatness'))
        self._ui.minVolRatio.setText(self._dbElement.getValue('minVolRatio'))
        self._ui.minTriangleTwist.setText(self._dbElement.getValue('minTriangleTwist'))
        self._ui.nSmoothScale.setText(self._dbElement.getValue('nSmoothScale'))
        self._ui.errorReduction.setText(self._dbElement.getValue('errorReduction'))
        self._ui.mergeTolerance.setText(self._dbElement.getValue('mergeTolerance'))

    def accept(self):
        try:
            self._dbElement.setValue('maxNonOrtho', self._ui.maxNonOrtho.text(), self.tr('Max. Face non-ortho'))
            self._dbElement.setValue('relaxed/maxNonOrtho', self._ui.maxNonOrthoRelaxed.text(),
                                     self.tr('Max. Relaxed Face non-ortho'))
            self._dbElement.setValue('maxBoundarySkewness', self._ui.maxBoundarySkewness.text(),
                                     self.tr('Max. Boundary Skewness'))
            self._dbElement.setValue('maxInternalSkewness', self._ui.maxInternalSkewness.text(),
                                     self.tr('Max. Internal Face Skewness'))
            self._dbElement.setValue('maxConcave', self._ui.maxConcave.text(), self.tr('Max. Cell Concavity'))
            self._dbElement.setValue('minVol', self._ui.minVol.text(), self.tr('Min. Cell Pyramid Volume'))
            self._dbElement.setValue('minTetQuality', self._ui.minTetQuality.text(),
                                     self.tr('Min. Tetrahedron Quality'))
            self._dbElement.setValue('minVolCollapseRatio', self._ui.minVolCollapseRatio.text(),
                                     self.tr('Min. Volume Collapse Ratio'))
            self._dbElement.setValue('minArea', self._ui.minArea.text(), self.tr('Min. Face Area'))
            self._dbElement.setValue('minTwist', self._ui.minTwist.text(), self.tr('Min. Twist'))
            self._dbElement.setValue('minDeterminant', self._ui.minDeterminant.text(), self.tr('Min. Cell Determinant'))
            self._dbElement.setValue('minFaceWeight', self._ui.minFaceWeight.text(),
                                     self.tr('Min. Face Interpolation Weight'))
            self._dbElement.setValue('minFaceFlatness', self._ui.minFaceFlatness.text(), self.tr('Min. Face Flatness'))
            self._dbElement.setValue('minVolRatio', self._ui.minVolRatio.text(), self.tr('Min .Volume Ratio'))
            self._dbElement.setValue('minTriangleTwist', self._ui.minTriangleTwist.text(),
                                     self.tr('Min. Triangle Twist'))
            self._dbElement.setValue('nSmoothScale', self._ui.nSmoothScale.text(), self.tr('Smoothing Iteration'))
            self._dbElement.setValue('errorReduction', self._ui.errorReduction.text(), self.tr('Error reduction'))
            self._dbElement.setValue('mergeTolerance', self._ui.mergeTolerance.text(), self.tr('Merge Tolerance'))

            app.db.commit(self._dbElement)

            super().accept()
        except ValidationError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())
