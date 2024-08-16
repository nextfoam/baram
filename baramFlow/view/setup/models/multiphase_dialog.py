#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.models_db import ModelsDB, MultiphaseModel
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .multiphase_dialog_ui import Ui_MultiphaseDialog


class MultiphaseModelDialog(ResizableDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_MultiphaseDialog()
        self._ui.setupUi(self)

        self._modelRadios = {
            self._ui.modelRadioGroup.id(self._ui.off): MultiphaseModel.OFF.value,
            self._ui.modelRadioGroup.id(self._ui.volumeOfFluid): MultiphaseModel.VOLUME_OF_FLUID.value,
        }

        self._xpath = ModelsDB.MULTIPHASE_MODELS_XPATH

        self._ui.volumeOfFluid.hide()
        self._ui.mixture.hide()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._getRadio(
            self._ui.modelRadioGroup, self._modelRadios, coredb.CoreDB().getValue(self._xpath + '/model')
        ).setChecked(True)

        return super().showEvent(ev)

    def accept(self):
        writer = CoreDBWriter()
        writer.append(self._xpath + '/model', self._getRadioValue(self._ui.modelRadioGroup, self._modelRadios), None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _getRadio(self, group, radios, value):
        return group.button(list(radios.keys())[list(radios.values()).index(value)])

    def _getRadioValue(self, group, radios):
        return radios[group.id(group.checkedButton())]
