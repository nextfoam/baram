#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramMesh.app import app
from baramMesh.db.simple_schema import DBError
from .boundar_layer_advanced_dialog_ui import Ui_BoundaryLayerAdvancedDialog


class BoundaryLayerAdvancedDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_BoundaryLayerAdvancedDialog()
        self._ui.setupUi(self)

        self._dbElement = app.db.checkout('addLayers')

        self._ui.nGrow.setText(self._dbElement.getValue('nGrow'))
        self._ui.maxFaceThicknessRatio.setText(self._dbElement.getValue('maxFaceThicknessRatio'))
        self._ui.nSmoothSurfaceNormals.setText(self._dbElement.getValue('nSmoothSurfaceNormals'))
        self._ui.nSmoothThickness.setText(self._dbElement.getValue('nSmoothThickness'))
        self._ui.minMedialAxisAngle.setText(self._dbElement.getValue('minMedialAxisAngle'))
        self._ui.maxThicknessToMedialRatio.setText(self._dbElement.getValue('maxThicknessToMedialRatio'))
        self._ui.nSmoothNormals.setText(self._dbElement.getValue('nSmoothNormals'))
        self._ui.slipFeatureAngle.setText(self._dbElement.getValue('slipFeatureAngle'))
        self._ui.nRelaxIter.setText(self._dbElement.getValue('nRelaxIter'))
        self._ui.nBufferCellsNoExtrude.setText(self._dbElement.getValue('nBufferCellsNoExtrude'))
        self._ui.nLayerIter.setText(self._dbElement.getValue('nLayerIter'))
        self._ui.nRelaxedIter.setText(self._dbElement.getValue('nRelaxedIter'))

    def accept(self):
        try:
            self._dbElement.setValue('nGrow', self._ui.nGrow.text(), self.tr('Number of Grow'))
            self._dbElement.setValue('maxFaceThicknessRatio', self._ui.maxFaceThicknessRatio.text(),
                                     self.tr('Max. Thickness Ratio'))
            self._dbElement.setValue('nSmoothSurfaceNormals', self._ui.nSmoothSurfaceNormals.text(),
                                     self.tr('Number of Iterations'))
            self._dbElement.setValue('nSmoothThickness', self._ui.nSmoothThickness.text(),
                                     self.tr('Smooth Layer Thickness'))
            self._dbElement.setValue('minMedialAxisAngle', self._ui.minMedialAxisAngle.text(),
                                     self.tr('Min. Axis Angle'))
            self._dbElement.setValue('maxThicknessToMedialRatio', self._ui.maxThicknessToMedialRatio.text(),
                                     self.tr('Max. Thickness Ratio'))
            self._dbElement.setValue('nSmoothNormals', self._ui.nSmoothNormals.text(),
                                     self.tr('Number of Smoothing Iter.'))
            self._dbElement.setValue('slipFeatureAngle', self._ui.slipFeatureAngle.text(),
                                     self.tr('Slip Feature Angle'))
            self._dbElement.setValue('nRelaxIter', self._ui.nRelaxIter.text(),
                                     self.tr('Max. Snapping Relaxation Iter.'))
            self._dbElement.setValue('nBufferCellsNoExtrude', self._ui.nBufferCellsNoExtrude.text(),
                                     self.tr('Nu. of Buffer Cells'))
            self._dbElement.setValue('nLayerIter', self._ui.nLayerIter.text(), self.tr('Max. Layer Addition Iter.'))
            self._dbElement.setValue('nRelaxedIter', self._ui.nRelaxedIter.text(), self.tr('Max. Iter. Before Relax'))

            app.db.commit(self._dbElement)

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())
