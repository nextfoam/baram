#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB, DirectionSpecificationMethod, DirectionSpecificationMethodTexts
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .free_stream_dialog_ui import Ui_FreeStreamDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FreeStreamDialog(ResizableDialog):
    RELATIVE_XPATH = '/freeStream'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FreeStreamDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()

        self._ui.specificationMethod.addItem(DirectionSpecificationMethodTexts[DirectionSpecificationMethod.DIRECT],
                                             DirectionSpecificationMethod.DIRECT)
        self._ui.specificationMethod.addItem(DirectionSpecificationMethodTexts[DirectionSpecificationMethod.AOA_AOS],
                                             DirectionSpecificationMethod.AOA_AOS)

        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        path = self._xpath + self.RELATIVE_XPATH

        writer = CoreDBWriter()

        specificationMethod = self._ui.specificationMethod.currentData()
        writer.append(path + '/flowDirection/specificationMethod', specificationMethod.value, None)
        if specificationMethod == DirectionSpecificationMethod.DIRECT:
            writer.append(path + '/flowDirection/flowDirection/x', self._ui.flowDirectionX.text(),
                          self.tr('Flow Direction'))
            writer.append(path + '/flowDirection/flowDirection/y', self._ui.flowDirectionY.text(),
                          self.tr('Flow Direction'))
            writer.append(path + '/flowDirection/flowDirection/z', self._ui.flowDirectionZ.text(),
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

        writer.append(path + '/speed', self._ui.speed.text(), self.tr('Speed'))
        writer.append(path + '/pressure', self._ui.pressure.text(), self.tr("Pressure"))

        if not self._turbulenceWidget.appendToWriter(writer):
            return

        if not self._temperatureWidget.appendToWriter(writer):
            return

        if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
            return

        if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
            return

        errorCount = writer.write()
        if errorCount > 0:
            self._temperatureWidget.rollbackWriting()
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self._temperatureWidget.completeWriting()
            self.accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentIndex(
            self._ui.specificationMethod.findData(
                DirectionSpecificationMethod(db.getValue(path + '/flowDirection/specificationMethod'))))

        self._ui.flowDirectionX.setText(db.getValue(path + '/flowDirection/flowDirection/x'))
        self._ui.flowDirectionY.setText(db.getValue(path + '/flowDirection/flowDirection/y'))
        self._ui.flowDirectionZ.setText(db.getValue(path + '/flowDirection/flowDirection/z'))
        self._ui.dragDirectionX.setText(db.getValue(path + '/flowDirection/dragDirection/x'))
        self._ui.dragDirectionY.setText(db.getValue(path + '/flowDirection/dragDirection/y'))
        self._ui.dragDirectionZ.setText(db.getValue(path + '/flowDirection/dragDirection/z'))
        self._ui.liftDirectionX.setText(db.getValue(path + '/flowDirection/liftDirection/x'))
        self._ui.liftDirectionY.setText(db.getValue(path + '/flowDirection/liftDirection/y'))
        self._ui.liftDirectionZ.setText(db.getValue(path + '/flowDirection/liftDirection/z'))
        self._ui.AoA.setText(db.getValue(path + '/flowDirection/angleOfAttack'))
        self._ui.AoS.setText(db.getValue(path + '/flowDirection/angleOfSideslip'))

        self._ui.speed.setText(db.getValue(path + '/speed'))
        self._ui.pressure.setText(db.getValue(path + '/pressure'))

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self):
        method = self._ui.specificationMethod.currentData()
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.directFlowDirection.show()
            self._ui.anglesFlowDirection.hide()
        else:
            self._ui.directFlowDirection.hide()
            self._ui.anglesFlowDirection.show()
