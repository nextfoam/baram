#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QDialog, QMessageBox

from app import app
from db.simple_schema import DBError
from db.configurations_schema import CFDType
from view.widgets.radio_group import RadioGroup
from .surface_dialog_ui import Ui_SurfaceDialog


class SurfaceDialog(QDialog):
    _cfdTypes = {
        'none': CFDType.NONE.value,
        'boundary': CFDType.BOUNDARY.value,
        'interface_': CFDType.INTERFACE.value
    }

    def __init__(self, parent, gId):
        super().__init__(parent)
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._typeRadios = RadioGroup(self._ui.typeRadios)

        self._gId = gId
        self._dbElement = None

        self._connectSignalsSlots()
        self._load()

    def gId(self):
        return self._gId

    def accept(self):
        try:
            name = self._ui.name.text()

            if app.db.getElements('geometry', lambda i, e: e['name'] == name and i != self._gId, ['name']):
                QMessageBox.information(
                    self, self.tr('Add Geometry Failed'),
                    self.tr('geometry {0} already exists.').format(name))
                return False

            self._dbElement.setValue('name', name)

            self._dbElement.setValue('cfdType', self._typeRadios.value())
            self._dbElement.setValue('nonConformal', self._ui.nonConformal.isChecked())
            self._dbElement.setValue('interRegion', self._ui.interRegion.isChecked())

            app.db.commit(self._dbElement)

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())

    def _connectSignalsSlots(self):
        self._typeRadios.valueChanged.connect(self._typeChanged)

    def _load(self):
        self._dbElement = app.db.checkout(f'geometry/{self._gId}')

        self._ui.name.setText(self._dbElement.getValue('name'))

        cfdType = self._dbElement.getValue('cfdType')
        self._typeRadios.setObjectMap(self._cfdTypes, cfdType)
        if cfdType == CFDType.INTERFACE.value:
            self._ui.nonConformal.setChecked(self._dbElement.getValue('nonConformal'))
            self._ui.interRegion.setChecked(self._dbElement.getValue('interRegion'))

        self._typeChanged(self._typeRadios.value())

    def _typeChanged(self, value):
        self._ui.interfaceType.setEnabled(value == CFDType.INTERFACE.value)
