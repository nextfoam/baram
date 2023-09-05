#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QMessageBox

from app import app
from db.configurations_schema import RegionType
from db.simple_schema import DBError
from rendering.point_widget import PointWidget
from view.widgets.radio_group import RadioGroup
from .region_form_ui import Ui_RegionForm


class RegionForm(QWidget):
    regionAdded = Signal(str)
    regionEdited = Signal(str)

    _types = {
        'fluid': RegionType.FLUID.value,
        'solid': RegionType.SOLID.value
    }

    def __init__(self, renderingView):
        super().__init__()
        self._ui = Ui_RegionForm()
        self._ui.setupUi(self)

        self._id = None
        self._dbElement = None
        self._typeRadios = RadioGroup(self._ui.typeRadios)
        self._pointWidget = PointWidget(renderingView)

        self._pointWidget.off()
        self._typeRadios.setObjectMap(self._types)

        self._connectSignalsSlots()

    def setBounds(self, bounds):
        point = self._pointWidget.setBounds(bounds)
        self._setPoint(point)

    def setupForAdding(self):
        self._id = None
        self._dbElement = app.db.newElement('region')

        self._ui.regionForm.setTitle(self.tr('Add Region'))
        self._ui.name.clear()
        self._ui.ok.setText(self.tr('Add'))

        self._ui.name.setFocus()
        self.show()
        self._pointWidget.on()

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
        self._movePointWidget()
        self._ui.ok.setText(self.tr('Update'))

        self.show()
        self._pointWidget.on()

    def _connectSignalsSlots(self):
        self._ui.x.editingFinished.connect(self._movePointWidget)
        self._ui.y.editingFinished.connect(self._movePointWidget)
        self._ui.z.editingFinished.connect(self._movePointWidget)
        self._pointWidget.pointMoved.connect(self._setPoint)

        self._ui.name.textChanged.connect(self._validate)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self._cancel)

    def _movePointWidget(self):
        self._setPoint(
            self._pointWidget.setPosition(float(self._ui.x.text()), float(self._ui.y.text()), float(self._ui.z.text())))

    def _setPoint(self, point):
        x, y, z = point
        self._ui.x.setText('{:.6g}'.format(x))
        self._ui.y.setText('{:.6g}'.format(y))
        self._ui.z.setText('{:.6g}'.format(z))

    def _validate(self):
        self._ui.ok.setEnabled(self._ui.name.text().strip() != '')

    def _accept(self):
        name = self._ui.name.text()
        if app.db.getElements('region', lambda i, e: e['name'] == name and i != self._id, []):
            QMessageBox.information(self, self.tr('Fail to Add Region'),
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

            self._pointWidget.off()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())

    def _cancel(self):
        self._pointWidget.off()
        self.hide()
