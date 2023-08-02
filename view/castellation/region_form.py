#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from app import app
from db.configurations_schema import RegionType
from db.simple_schema import DBError
from view.widgets.radio_group import RadioGroup


class RegionForm(QObject):
    regionAdded = Signal(str)
    regionEdited = Signal(str)
    pointChanged = Signal()

    _types = {
        'fluid': RegionType.FLUID.value,
        'solid': RegionType.SOLID.value
    }

    def __init__(self, ui):
        super().__init__()
        self._ui = ui
        self._widget = ui.regionForm
        self._id = None
        self._dbElement = None
        self._typeRadios = RadioGroup(self._ui.regionTypeRadios)

        self._typeRadios.setObjectMap(self._types)

        self._connectSignalsSlots()

    def setupForAdding(self):
        self._id = None
        self._dbElement = app.db.newElement('region')

        self._ui.regionForm.setTitle(self.tr('Add Region'))
        self._ui.name.clear()
        self._ui.ok.setText(self.tr('Add'))

    def setupForEditing(self, id_):
        self._id = id_
        self._dbElement = app.db.checkout(f'region/{id_}')

        self._ui.regionForm.setTitle(self.tr('Edit Region'))
        self._ui.name.setText(self._dbElement.getValue('name'))
        self._typeRadios.setValue(self._dbElement.getValue('type'))
        x, y, z = self._dbElement.getVector('point')
        self._ui.x.setText(x)
        self._ui.y.setText(y)
        self._ui.z.setText(z)
        self.pointChanged.emit()
        self._ui.ok.setText(self.tr('Update'))

    def disable(self):
        self._widget.setEnabled(False)

    def enable(self):
        self._widget.setEnabled(True)

    def _connectSignalsSlots(self):
        self._ui.name.textChanged.connect(self._validate)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self.setupForAdding)

    def _validate(self):
        self._ui.ok.setEnabled(self._ui.name.text().strip() != '')

    def _accept(self):
        name = self._ui.name.text()
        if app.db.getElements('region', lambda i, e: e['name'] == name and i != self._id, []):
            QMessageBox.information(self._widget, self.tr('Fail to Add Region'),
                                    self.tr('Region {0} already exists.').format(name))
            return

        try:
            self._dbElement.setValue('name', name)
            self._dbElement.setValue('type', self._typeRadios.value())
            self._dbElement.setValue('point/x', self._ui.x.text(), self.tr('Point'))
            self._dbElement.setValue('point/y', self._ui.y.text(), self.tr('Point'))
            self._dbElement.setValue('point/z', self._ui.z.text(), self.tr('Point'))

            if self._id:    # Edit
                app.db.commit(self._dbElement)
                self.regionEdited.emit(self._id)
            else:           # Add
                db = app.db.checkout()
                id_ = db.addElement('region', self._dbElement)
                app.db.commit(db)

                self.regionAdded.emit(id_)

            self.setupForAdding()
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

