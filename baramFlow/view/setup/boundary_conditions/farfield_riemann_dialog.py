#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, DirectionSpecificationMethod
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .farfield_riemann_dialog_ui import Ui_FarfieldRiemannDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FarfieldRiemannDialog(ResizableDialog):
    RELATIVE_XPATH = '/farFieldRiemann'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FarfieldRiemannDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        self._ui.specificationMethod.addEnumItems({
            DirectionSpecificationMethod.DIRECT:    self.tr('Direct'),
            DirectionSpecificationMethod.AOA_AOS:   self.tr('AOA and AOS')
        })

        layout = self._ui.dialogContents.layout()
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)

        self._connectSignalsSlots()
        self._load()

    def accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()

        specificationMethod = self._ui.specificationMethod.currentData()
        writer.append(path + '/flowDirection/specificationMethod', specificationMethod.value, None)
        if specificationMethod == DirectionSpecificationMethod.DIRECT:
            writer.append(path + '/flowDirection/dragDirection/x', self._ui.flowDirectionX.text(),
                          self.tr('Flow Direction'))
            writer.append(path + '/flowDirection/dragDirection/y', self._ui.flowDirectionY.text(),
                          self.tr('Flow Direction'))
            writer.append(path + '/flowDirection/dragDirection/z', self._ui.flowDirectionZ.text(),
                          self.tr('Flow Direction'))
        else:
            writer.append(path + '/flowDirection/dragDirection/x', self._ui.dragDirectionX.text(),
                          self.tr('Drag Direction'))
            writer.append(path + '/flowDirection/dragDirection/y', self._ui.dragDirectionY.text(),
                          self.tr('Drag Direction'))
            writer.append(path + '/flowDirection/dragDirection/z', self._ui.dragDirectionZ.text(),
                          self.tr('Drag Direction'))
            writer.append(path + '/flowDirection/liftDirection/x', self._ui.liftDirectionX.text(),
                          self.tr('Lift Direction'))
            writer.append(path + '/flowDirection/liftDirection/y', self._ui.liftDirectionY.text(),
                          self.tr('Lift Direction'))
            writer.append(path + '/flowDirection/liftDirection/z', self._ui.liftDirectionZ.text(),
                          self.tr('Lift Direction'))
            writer.append(path + '/flowDirection/angleOfAttack', self._ui.AoA.text(), self.tr('Angle of Attack'))
            writer.append(path + '/flowDirection/angleOfSideslip', self._ui.AoS.text(), self.tr('Angle of Sideslip'))
        writer.append(path + '/machNumber', self._ui.machNumber.text(), self.tr('Mach Number'))
        writer.append(path + '/staticPressure', self._ui.staticPressure.text(), self.tr('Static Pressure'))
        writer.append(path + '/staticTemperature', self._ui.staticTemperature.text(), self.tr('Static Temperature'))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
        else:
            super().accept()

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentData(
            DirectionSpecificationMethod(db.getValue(path + '/flowDirection/specificationMethod')))

        self._ui.flowDirectionX.setText(db.getValue(path + '/flowDirection/dragDirection/x'))
        self._ui.flowDirectionY.setText(db.getValue(path + '/flowDirection/dragDirection/y'))
        self._ui.flowDirectionZ.setText(db.getValue(path + '/flowDirection/dragDirection/z'))
        self._ui.dragDirectionX.setText(db.getValue(path + '/flowDirection/dragDirection/x'))
        self._ui.dragDirectionY.setText(db.getValue(path + '/flowDirection/dragDirection/y'))
        self._ui.dragDirectionZ.setText(db.getValue(path + '/flowDirection/dragDirection/z'))
        self._ui.liftDirectionX.setText(db.getValue(path + '/flowDirection/liftDirection/x'))
        self._ui.liftDirectionY.setText(db.getValue(path + '/flowDirection/liftDirection/y'))
        self._ui.liftDirectionZ.setText(db.getValue(path + '/flowDirection/liftDirection/z'))
        self._ui.AoA.setText(db.getValue(path + '/flowDirection/angleOfAttack'))
        self._ui.AoS.setText(db.getValue(path + '/flowDirection/angleOfSideslip'))

        self._ui.machNumber.setText(db.getValue(path + '/machNumber'))
        self._ui.staticPressure.setText(db.getValue(path + '/staticPressure'))
        self._ui.staticTemperature.setText(db.getValue(path + '/staticTemperature'))

        self._turbulenceWidget.load()

    def _specificationMethodChanged(self, method):
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.directFlowDirection.show()
            self._ui.anglesFlowDirection.hide()
        else:
            self._ui.directFlowDirection.hide()
            self._ui.anglesFlowDirection.show()
