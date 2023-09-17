#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFormLayout

from db.configurations_schema import ThicknessModel
from view.widgets.radio_group import RadioGroup


class ThicknessRow(Enum):
    SIZE_SPECIFICATION = 'sizeSpecificationRelative'
    FIRST_LAYER_THICKNESS = 'firstLayerThickness'
    FINAL_LAYER_THICKNESS = 'finalLayerThickness'
    TOTAL_THICKNESS = 'totalThickness'
    EXPANSION_RATIO = 'expansionRatio'


class ThicknessForm(QObject):
    modelChanged = Signal()

    _thicknessModels = {
        'firstAndOverall': ThicknessModel.FIRST_AND_OVERALL.value,
        'firstAndExpansion': ThicknessModel.FIRST_AND_EXPANSION.value,
        'finalAndOverall': ThicknessModel.FINAL_AND_OVERALL.value,
        'finalAndExpansion': ThicknessModel.FINAL_AND_EXPANSION.value,
        'overallAndExpansion': ThicknessModel.OVERALL_AND_EXPANSION.value,
        'firstAndRelativeFinal': ThicknessModel.FIRST_AND_RELATIVE_FINAL.value
    }

    def __init__(self, ui):
        super().__init__()

        self._thicknessModelRadios = RadioGroup(ui.thicknessModelSpecificationRadios)
        self._thicknessRows = {}
        self._ui = ui

        layout = self._ui.thickness.layout()
        for i in range(layout.rowCount()):
            self._thicknessRows[layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget().objectName()] = i

        self._connectSignalsSlots()

    @property
    def ui(self):
        return self._ui

    def model(self):
        return self._thicknessModelRadios.value()

    def save(self, db):
        db.setValue('thicknessModel', self._thicknessModelRadios.value(), self.tr('Thickness Model Specification'))
        db.setValue('relativeSizes', self._ui.sizeSpecificationRelative.isChecked())
        db.setValue('firstLayerThickness', self._ui.firstLayerThickness.text(), self.tr('First Layer Thickness'))
        db.setValue('finalLayerThickness', self._ui.finalLayerThickness.text(), self.tr('Final Layer Thickness'))
        db.setValue('thickness', self._ui.totalThickness.text(), self.tr('Total Thickness'))
        db.setValue('expansionRatio', self._ui.expansionRatio.text(), self.tr('Expansion Ratio'))
        db.setValue('minThickness', self._ui.minTotalTickness.text(), self.tr('Min. Total Thickness'))

    def _connectSignalsSlots(self):
        self._thicknessModelRadios.valueChanged.connect(self._thicknessModelChanged)

    def setData(self, data):
        model = data.getValue('thicknessModel')
        self._thicknessModelRadios.setObjectMap(self._thicknessModels, model)
        self._ui.sizeSpecificationRelative.setChecked(data.getValue('relativeSizes'))
        self._ui.firstLayerThickness.setText(data.getValue('firstLayerThickness'))
        self._ui.finalLayerThickness.setText(data.getValue('finalLayerThickness'))
        self._ui.totalThickness.setText(data.getValue('thickness'))
        self._ui.expansionRatio.setText(data.getValue('expansionRatio'))
        self._ui.minTotalTickness.setText(data.getValue('minThickness'))
        self._thicknessModelChanged(model)

    def copyData(self, form):
        model = form.model()
        self._thicknessModelRadios.setObjectMap(self._thicknessModels, model)
        self._ui.sizeSpecificationRelative.setChecked(form.ui.sizeSpecificationRelative.isChecked())
        self._ui.firstLayerThickness.setText(form.ui.firstLayerThickness.text())
        self._ui.finalLayerThickness.setText(form.ui.finalLayerThickness.text())
        self._ui.totalThickness.setText(form.ui.totalThickness.text())
        self._ui.expansionRatio.setText(form.ui.expansionRatio.text())
        self._ui.minTotalTickness.setText(form.ui.minTotalTickness.text())
        self._thicknessModelChanged(model)

    def _thicknessModelChanged(self, model):
        layout = self._ui.thickness.layout()
        layout.setRowVisible(self._thicknessRows[ThicknessRow.SIZE_SPECIFICATION.value],
                             model != ThicknessModel.FIRST_AND_RELATIVE_FINAL.value)
        layout.setRowVisible(self._thicknessRows[ThicknessRow.FIRST_LAYER_THICKNESS.value],
                             model in (ThicknessModel.FIRST_AND_OVERALL.value,
                                       ThicknessModel.FIRST_AND_EXPANSION.value,
                                       ThicknessModel.FIRST_AND_RELATIVE_FINAL.value))
        layout.setRowVisible(self._thicknessRows[ThicknessRow.FINAL_LAYER_THICKNESS.value],
                             model in (ThicknessModel.FINAL_AND_OVERALL.value,
                                       ThicknessModel.FINAL_AND_EXPANSION.value,
                                       ThicknessModel.FIRST_AND_RELATIVE_FINAL.value))
        layout.setRowVisible(self._thicknessRows[ThicknessRow.TOTAL_THICKNESS.value],
                             model in (ThicknessModel.FIRST_AND_OVERALL.value,
                                       ThicknessModel.FINAL_AND_OVERALL.value,
                                       ThicknessModel.OVERALL_AND_EXPANSION.value))
        layout.setRowVisible(self._thicknessRows[ThicknessRow.EXPANSION_RATIO.value],
                             model in (ThicknessModel.FIRST_AND_EXPANSION.value,
                                       ThicknessModel.FINAL_AND_EXPANSION.value,
                                       ThicknessModel.OVERALL_AND_EXPANSION.value))

        self.modelChanged.emit()
