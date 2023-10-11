#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from widgets.radio_group import RadioGroup

from baramMesh.app import app
from baramMesh.db.simple_schema import DBError
from baramMesh.db.configurations_schema import CFDType
from .surface_dialog_ui import Ui_SurfaceDialog


class SurfaceDialog(QDialog):
    _cfdTypes = {
        'none': CFDType.NONE.value,
        'boundary': CFDType.BOUNDARY.value,
        'interface_': CFDType.INTERFACE.value
    }

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_SurfaceDialog()
        self._ui.setupUi(self)

        self._typeRadios = RadioGroup(self._ui.typeRadios)

        self._gIds = None
        self._dbElement = None

        self._connectSignalsSlots()

    def gIds(self):
        return self._gIds

    def setGIds(self, gIds):
        self._gIds = gIds
        self._load()

    def accept(self):
        try:
            db = app.db.checkout()

            if len(self._gIds) == 1:
                name = self._ui.name.text()

                if app.db.getElements('geometry', lambda i, e: e['name'] == name and i != self._gIds[0], ['name']):
                    QMessageBox.information(
                        self, self.tr('Fail to modify geometry name'),
                        self.tr('geometry {0} already exists.').format(name))

                    return False

                db.setValue(f'geometry/{self._gIds[0]}/name', name)

            for gId in self._gIds:
                element = db.checkout(f'geometry/{gId}')

                cfdType = self._typeRadios.value()
                element.setValue('cfdType', cfdType)
                element.setValue('nonConformal', self._ui.nonConformal.isChecked())
                element.setValue('interRegion', self._ui.interRegion.isChecked())

                if cfdType != CFDType.INTERFACE.value:
                    element.setValue('slaveLayerGroup', None)
                    if cfdType != CFDType.BOUNDARY.value:
                        element.setValue('layerGroup', None)

                db.commit(element)

            app.db.commit(db)
            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())

    def _connectSignalsSlots(self):
        self._typeRadios.valueChanged.connect(self._typeChanged)

    def _load(self):
        surfaces = app.db.getElements('geometry',
                                      lambda i, e: i in self._gIds, ['name', 'cfdType', 'nonConformal', 'interRegion'])

        first = surfaces[self._gIds[0]]
        if len(surfaces) > 1:
            self._ui.nameSetting.hide()
        else:
            self._ui.name.setText(first['name'])
            self._ui.nameSetting.show()

        cfdType = first['cfdType']
        nonConformal = None
        interRegion = None
        self._typeRadios.setObjectMap(self._cfdTypes, cfdType)
        if cfdType == CFDType.INTERFACE.value:
            nonConformal = first['nonConformal']
            interRegion = first['interRegion']
            self._ui.nonConformal.setChecked(nonConformal)
            self._ui.interRegion.setChecked(interRegion)

        for gId, s in surfaces.items():
            if cfdType != s['cfdType'] or cfdType == CFDType.INTERFACE.value:
                if cfdType != s['cfdType'] or nonConformal != s['nonConformal'] or interRegion != s['interRegion']:
                    self._typeRadios.setValue(CFDType.BOUNDARY.value)
                    break

        self._typeChanged(self._typeRadios.value())

    def _typeChanged(self, value):
        self._ui.interfaceType.setEnabled(value == CFDType.INTERFACE.value)
