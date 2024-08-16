#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from .ABL_inlet_dialog_ui import Ui_ABLInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class ABLInletDialog(QDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_ABLInletDialog()
        self._ui.setupUi(self)

        self._xpath = BoundaryDB.ABL_INLET_CONDITIONS_XPATH

        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(BoundaryDB.getBoundaryRegion(bcid),
                                                                               self._ui.dialogContents.layout())

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/flowDirection/x',
                      self._ui.flowDirectionXComponent.text(), self.tr("Flow Direction X-Component"))
        writer.append(self._xpath + '/flowDirection/y',
                      self._ui.flowDirectionYComponent.text(), self.tr("Flow Direction Y-Component"))
        writer.append(self._xpath + '/flowDirection/z',
                      self._ui.flowDirectionZComponent.text(), self.tr("Flow Direction Z-Component"))
        writer.append(self._xpath + '/groundNormalDirection/x',
                      self._ui.groundNormalDirectionXComponent.text(), self.tr("Ground-Normal Direction X-Component"))
        writer.append(self._xpath + '/groundNormalDirection/y',
                      self._ui.groundNormalDirectionYComponent.text(), self.tr("Ground-Normal Direction Y-Component"))
        writer.append(self._xpath + '/groundNormalDirection/z',
                      self._ui.groundNormalDirectionZComponent.text(), self.tr("Ground-Normal Direction Z-Component"))
        writer.append(self._xpath + '/referenceFlowSpeed',
                      self._ui.referenceFlowSpeed.text(), self.tr("Reference Flow Speed"))
        writer.append(self._xpath + '/referenceHeight',
                      self._ui.referenceHeight.text(), self.tr("Reference Height"))
        writer.append(self._xpath + '/surfaceRoughnessLength',
                      self._ui.surfaceRoughnessLength.text(), self.tr("Surface Roughness Length"))
        writer.append(self._xpath + '/minimumZCoordinate',
                      self._ui.minimumZCoordinate.text(), self.tr("Minimum z-coordinate"))

        if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
            return

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().information(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

    def _load(self):
        db = coredb.CoreDB()
        self._ui.flowDirectionXComponent.setText(db.getValue(self._xpath + '/flowDirection/x'))
        self._ui.flowDirectionYComponent.setText(db.getValue(self._xpath + '/flowDirection/y'))
        self._ui.flowDirectionZComponent.setText(db.getValue(self._xpath + '/flowDirection/z'))
        self._ui.groundNormalDirectionXComponent.setText(db.getValue(self._xpath + '/groundNormalDirection/x'))
        self._ui.groundNormalDirectionYComponent.setText(db.getValue(self._xpath + '/groundNormalDirection/y'))
        self._ui.groundNormalDirectionZComponent.setText(db.getValue(self._xpath + '/groundNormalDirection/z'))
        self._ui.referenceFlowSpeed.setText(db.getValue(self._xpath + '/referenceFlowSpeed'))
        self._ui.referenceHeight.setText(db.getValue(self._xpath + '/referenceHeight'))
        self._ui.surfaceRoughnessLength.setText(db.getValue(self._xpath + '/surfaceRoughnessLength'))
        self._ui.minimumZCoordinate.setText(db.getValue(self._xpath + '/minimumZCoordinate'))
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
