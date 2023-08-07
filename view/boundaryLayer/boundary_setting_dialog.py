#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from app import app
from db.simple_schema import DBError
from .thickness_form import ThicknessForm
from .boundary_setting_dialog_ui import Ui_BoundarySettingDialog


class BoundarySettingDialog(QDialog):
    def __init__(self, parent, gID, globalForm):
        super().__init__(parent)
        self._ui = Ui_BoundarySettingDialog()
        self._ui.setupUi(self)

        self._thicknessForm = ThicknessForm(self._ui)

        self._gID = gID
        self._dbElement = app.db.checkout(f'addLayers/layers/{self._gID}')

        self._connectSignalsSlots()

        useLocalSetting = self._dbElement.getValue('useLocalSetting')
        self._ui.localSetting.setChecked(useLocalSetting)
        self._ui.numberOfLayers.setText(self._dbElement.getValue('nSurfaceLayers'))
        if useLocalSetting:
            self._thicknessForm.setData(self._dbElement)
        else:
            self._thicknessForm.copyData(globalForm)

    def gID(self):
        return self._gID

    def accept(self):
        try:
            self._dbElement.setValue('useLocalSetting', self._ui.localSetting.isChecked())
            self._dbElement.setValue('nSurfaceLayers', self._ui.numberOfLayers.text(), self.tr('Number of Layers'))
            self._thicknessForm.save(self._dbElement)

            app.db.commit(self._dbElement)

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())

    def _connectSignalsSlots(self):
        self._thicknessForm.modelChanged.connect(self.adjustSize)
