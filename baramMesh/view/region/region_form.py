#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QMessageBox

from libbaram.simple_db.simple_schema import ValidationError
from widgets.radio_group import RadioGroup
from widgets.rendering.point_widget import PointWidget
from widgets.selector_dialog import SelectorDialog, SelectorItem as SingleSelectorItem
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations_schema import RegionType, GeometryType
from .region_form_ui import Ui_RegionForm
from .region_point_finder import getVolumePolyData, findInteriorPoint


class RegionForm(QWidget):
    regionAdded = Signal(str)
    regionEdited = Signal(str)
    canceled = Signal()

    _types = {
        'fluid': RegionType.FLUID.value,
        'solid': RegionType.SOLID.value
    }
    
    _baseName = 'Region_'

    def __init__(self, renderingView, owner):
        super().__init__()
        self._ui = Ui_RegionForm()
        self._ui.setupUi(self)

        self._id = None
        self._dbElement = None
        self._typeRadios = RadioGroup(self._ui.typeRadios)
        self._pointWidget = PointWidget(renderingView)
        self._owner = owner
        self._defaultPoint = None

        self._pointWidget.off()
        self._typeRadios.setObjectMap(self._types)

        self.hide()

        self._connectSignalsSlots()

    def setBounds(self, bounds):
        self._defaultPoint = self._pointWidget.setBounds(bounds)

    def setOwner(self, widget):
        self._owner = widget

    def owner(self):
        return self._owner

    def setupForAdding(self):
        self._id = None
        self._dbElement = app.db.newElement('region')

        self._ui.regionForm.setTitle(self.tr('Add Region'))
        self._ui.name.setText(f"{self._baseName}{app.db.getUniqueSeq('region', 'name', self._baseName, 1)}")
        self._setPoint(self._defaultPoint)
        self._ui.ok.setText(self.tr('Add'))

        self._ui.name.setFocus()
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

        self._pointWidget.on()

    def cancel(self):
        self._pointWidget.off()
        self.canceled.emit()

    def _connectSignalsSlots(self):
        self._ui.x.editingFinished.connect(self._movePointWidget)
        self._ui.y.editingFinished.connect(self._movePointWidget)
        self._ui.z.editingFinished.connect(self._movePointWidget)
        self._pointWidget.pointMoved.connect(self._setPoint)

        self._ui.name.textChanged.connect(self._validate)
        self._ui.selectFromVolume.clicked.connect(self._selectFromVolume)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self.cancel)

    def _movePointWidget(self):
        self._setPoint(
            self._pointWidget.setPosition(
                float(self._ui.x.text()), float(self._ui.y.text()), float(self._ui.z.text())
            )
        )

    def _setPoint(self, point):
        x, y, z = point
        self._ui.x.setText('{:.6g}'.format(x))
        self._ui.y.setText('{:.6g}'.format(y))
        self._ui.z.setText('{:.6g}'.format(z))

    def _validate(self):
        self._ui.ok.setEnabled(self._ui.name.text().strip() != '')

    def _selectFromVolume(self):
        geometries = app.db.getElements('geometry')
        volumes = {
            gId: g for gId, g in geometries.items()
            if g.value('gType') == GeometryType.VOLUME.value
        }

        if not volumes:
            QMessageBox.information(
                self,
                self.tr('No Volumes'),
                self.tr('No volume geometries are available.\n'
                        'Please add volume geometries in the Geometry step first.')
            )
            return

        # --- Step 1: select target volume (single select) ---
        targetItems = [
            SingleSelectorItem(label=g.value('name'), text=g.value('name'), data=gId)
            for gId, g in volumes.items()
        ]

        targetDialog = SelectorDialog(
            self,
            self.tr('Select Target Volume'),
            self.tr('Select the volume that will contain the region point:'),
            targetItems
        )

        if targetDialog.exec() != SelectorDialog.Accepted:
            return

        targetId = targetDialog.selectedItem()

        # --- Step 2: select exclusion volumes (multi select) ---
        excludeItems = [
            SelectorItem(label=g.value('name'), text=g.value('name'), value=gId)
            for gId, g in volumes.items()
            if gId != targetId
        ]

        excludeIds = []
        if excludeItems:
            excludeDialog = MultiSelectorDialog(
                self,
                self.tr('Select Volumes to Exclude'),
                excludeItems,
                []
            )

            excludeDialog.itemsSelected.connect(lambda items: excludeIds.extend(v for v, _ in items))

            if excludeDialog.exec() != MultiSelectorDialog.Accepted:
                return

        # --- Step 3: resolve polyDatas and find interior point ---
        geometryManager = app.window.geometryManager

        targetPolyData = getVolumePolyData(targetId, geometryManager, geometries)
        if targetPolyData is None:
            QMessageBox.warning(
                self,
                self.tr('Geometry Error'),
                self.tr('Could not retrieve surface data for the selected volume.')
            )
            return

        exclusionPolyDatas = []
        for exId in excludeIds:
            exPoly = getVolumePolyData(exId, geometryManager, geometries)
            if exPoly is not None:
                exclusionPolyDatas.append(exPoly)

        point = findInteriorPoint(targetPolyData, exclusionPolyDatas)

        if point is None:
            QMessageBox.warning(
                self,
                self.tr('Point Not Found'),
                self.tr('Could not find a valid interior point for the selected volume '
                        'with the given exclusion constraints.\n'
                        'Try reducing the number of excluded volumes or enter coordinates manually.')
            )
            return

        self._setPoint(point)
        self._movePointWidget()

    def _accept(self):
        name = self._ui.name.text()
        if app.db.getElements('region', lambda i, e: e['name'] == name and i != self._id):
            QMessageBox.information(self, self.tr('Input Error'), self.tr('Region "{0}" already exists.').format(name))
            return

        x = self._ui.x.text()
        y = self._ui.y.text()
        z = self._ui.z.text()

        if not self._pointWidget.bounds().includes((float(x), float(y), float(z))):
            QMessageBox.information(self, self.tr('Input Error'),
                                    self.tr('Invalid Point - outside bounding box').format(name))
            return

        try:
            self._dbElement.setValue('name', name)
            self._dbElement.setValue('type', self._typeRadios.value())
            self._dbElement.setValue('point/x', x, self.tr('Point'))
            self._dbElement.setValue('point/y', y, self.tr('Point'))
            self._dbElement.setValue('point/z', z, self.tr('Point'))

            if self._id:    # Edit
                app.db.commit(self._dbElement)
                self.regionEdited.emit(self._id)
            else:           # Add
                db = app.db.checkout()
                id_ = db.addElement('region', self._dbElement)
                app.db.commit(db)

                self.regionAdded.emit(id_)

            self._pointWidget.off()
        except ValidationError as e:
            QMessageBox.information(self, self.tr("Input Error"), e.toMessage())
