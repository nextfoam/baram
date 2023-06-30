#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Signal, QEvent, QTimer

from app import app
from db.schema import DBError
from db.configurations_schema import ShapeType
from .geometry_dialog_ui import Ui_GeometryDialog

stackPages = {
    ShapeType.HEX: 'hex',
    ShapeType.CYLINDER: 'cylinder',
    ShapeType.SPHERE: 'sphere',
    ShapeType.HEX6: 'hex'
}


class GeometryDialog(QDialog):
    geometryAdded = Signal(int)
    geometryEdited = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_GeometryDialog()
        self._ui.setupUi(self)

        self._dbElement = None
        self._shape = None
        self._creationMode = True

        self._geometryWidgets = {}
        first = self._ui.geometryStack.widget(0)
        while self._ui.geometryStack.count() > 0:
            widget = self._ui.geometryStack.widget(0)
            self._geometryWidgets[widget.objectName()] = widget
            self._ui.geometryStack.removeWidget(widget)
        self._ui.geometryStack.addWidget(first)

    def setupForAdding(self, name, shape):
        self.setWindowTitle(self.tr('Add Geometry'))

        self._dbElement = app.db.newElement('geometry')
        self._shape = shape

        self._dbElement.setValue('name', name)
        self._dbElement.setValue('shape', shape)

        self._load()
        self.adjustSize()

    def _load(self):
        self._ui.name.setText(self._dbElement.getValue('name'))

        if self._shape == ShapeType.HEX.value or self._shape == ShapeType.HEX6.value:
            self._loadHexPage()
        elif self._shape == ShapeType.SPHERE.value:
            self._loadSpherePage()
        elif self._shape == ShapeType.CYLINDER.value:
            self._loadCylinderpage()

    def accept(self):
        try:
            if not self._updateData():
                return

            if self._creationMode:
                db = app.db.checkout()
                gId = db.addElement('geometry', self._dbElement)
                app.db.commit(db)
                self.geometryAdded.emit(gId)

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())

    def _loadHexPage(self):
        self._showGeometryPage('hex')

        x1, y1, z1 = self._dbElement.getVector('point1')
        x2, y2, z2 = self._dbElement.getVector('point2')
        self._ui.minX.setText(x1)
        self._ui.minY.setText(y1)
        self._ui.minZ.setText(z1)
        self._ui.maxX.setText(x2)
        self._ui.maxY.setText(y2)
        self._ui.maxZ.setText(z2)

    def _loadSpherePage(self):
        self._showGeometryPage('sphere')

    def _loadCylinderpage(self):
        self._showGeometryPage('cylinder')

    def _showGeometryPage(self, name):
        widget = self._ui.geometryStack.currentWidget()
        if widget.objectName() == name:
            return

        self._ui.geometryStack.removeWidget(widget)
        self._ui.geometryStack.addWidget(self._geometryWidgets[name])

        self._ui.geometryStack.adjustSize()
        self.adjustSize()

    def _updateData(self):
        name = self._ui.name.text()
        if self._creationMode:
            nameCheck = app.db.getFilteredElements('geometry', lambda i, e: e['name'] == name)
            if nameCheck:
                QMessageBox.information(self, self.tr('Add Geometry Failed'),
                                        self.tr('geometry {0} already exists.').format(name))
                return False

        self._dbElement.setValue('name', name)

        if self._shape == ShapeType.HEX.value or self._shape == ShapeType.HEX6.value:
            self._updateHexData()
        elif self._shape == ShapeType.SPHERE.value:
            self._updateSphereData()
        elif self._shape == ShapeType.CYLINDER.value:
            self._showGeometryPage()

        return True

    def _updateHexData(self):
        self._dbElement.setValue('point1/x', self._ui.minX.text(), self.tr('minX'))
        self._dbElement.setValue('point1/y', self._ui.minY.text(), self.tr('minY'))
        self._dbElement.setValue('point1/z', self._ui.minZ.text(), self.tr('minZ'))
        self._dbElement.setValue('point2/x', self._ui.maxX.text(), self.tr('maxX'))
        self._dbElement.setValue('point2/y', self._ui.maxY.text(), self.tr('maxY'))
        self._dbElement.setValue('point2/z', self._ui.maxZ.text(), self.tr('maxZ'))

    def _updateSphereData(self):
        self._showGeometryPage('sphere')

    def _updateCylinderData(self):
        self._showGeometryPage('cylinder')

    def _showGeometryPage(self, name):
        widget = self._ui.geometryStack.currentWidget()
        if widget.objectName() == name:
            return

        self._ui.geometryStack.removeWidget(widget)
        self._ui.geometryStack.addWidget(self._geometryWidgets[name])

        self._ui.geometryStack.adjustSize()
        self.adjustSize()

    def event(self, ev):
        if ev.type() == QEvent.LayoutRequest:
            QTimer.singleShot(0, self.adjustSize)
        return super().event(ev)
