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
        'interface_': 'interface'
    }

    _interfaceTypes = {
        'conformalMesh': CFDType.CONFORMAL_MESH.value,
        'nonConformalMesh': CFDType.NON_CONFORMAL_MESH.value
    }

    def __init__(self, parent, gId):
        super().__init__(parent)
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._typeRadios = RadioGroup(self._ui.typeRadios)
        self._interfaceRadios = RadioGroup(self._ui.interfaceRadios)

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

            cfdType = self._typeRadios.value()
            if cfdType == 'interface':
                cfdType = self._interfaceRadios.value()

            self._dbElement.setValue('cfdType', cfdType)

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
        if cfdType in self._interfaceTypes.values():
            cfdType = 'interface'
            self._ui.interfaceType.setEnabled(True)

        self._typeRadios.setObjectMap(self._cfdTypes, cfdType)
        self._interfaceRadios.setObjectMap(self._interfaceTypes, self._dbElement.getValue('cfdType'))

    def _typeChanged(self, value):
        self._ui.interfaceType.setEnabled(value == 'interface')
