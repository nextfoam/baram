#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramMesh.app import app
from baramMesh.db.simple_schema import DBError
from baramMesh.db.configurations_schema import CFDType
from baramMesh.view.widgets.multi_selector_dialog import SelectorItem, MultiSelectorDialog
from .thickness_form import ThicknessForm
from .boundary_setting_dialog_ui import Ui_BoundarySettingDialog


baseName = 'Group_'


class BoundarySettingDialog(QDialog):
    def __init__(self, parent, db, groupId=None):
        super().__init__(parent)
        self._ui = Ui_BoundarySettingDialog()
        self._ui.setupUi(self)

        self._thicknessForm = ThicknessForm(self._ui)

        self._groupId = groupId
        self._db = db
        self._dbElement = None
        self._creationMode = groupId is None
        self._dialog = None
        self._boundaries = None
        self._oldBoundaries = None
        self._availableBoundaries = None

        self._connectSignalsSlots()

        self._load()

    def dbElement(self):
        return self._dbElement

    def groupId(self):
        return self._groupId

    def isCreationMode(self):
        return self._creationMode

    def accept(self):
        try:
            groupName = self._ui.groupName.text().strip()
            if self._db.getKeys('addLayers/layers', lambda i, e: e['groupName'] == groupName and i != self._groupId):
                QMessageBox.information(self, self.tr('Input Error'),
                                        self.tr('Group name "{0}" already exists.').format(groupName))
                return

            if not self._boundaries:
                QMessageBox.information(self, self.tr('Input Error'), self.tr('Select boundaries'))
                return

            self._dbElement.setValue('groupName', groupName, self.tr('Group Name'))
            self._dbElement.setValue('nSurfaceLayers', self._ui.numberOfLayers.text(), self.tr('Number of Layers'))
            self._thicknessForm.save(self._dbElement)

            if self._groupId:
                self._db.commit(self._dbElement)
            else:
                self._groupId = self._db.addElement('addLayers/layers', self._dbElement)

            boundaries = {gId: None for gId in self._oldBoundaries}
            for gId in self._boundaries:
                if gId in boundaries:
                    boundaries.pop(gId)
                else:
                    boundaries[gId] = self._groupId

            geometryManager = app.window.geometryManager
            for key, group in boundaries.items():
                gId, isSlave = self._extractSelectorKey(key)
                if isSlave:
                    self._db.setValue(f'geometry/{gId}/slaveLayerGroup', group)
                    geometryManager.updateGeometryProperty(gId, 'slaveLayerGroup', group)
                else:
                    self._db.setValue(f'geometry/{gId}/layerGroup', group)
                    geometryManager.updateGeometryProperty(gId, 'layerGroup', group)

            super().accept()
        except DBError as error:
            QMessageBox.information(self, self.tr("Input Error"), error.toMessage())

    def _connectSignalsSlots(self):
        self._thicknessForm.modelChanged.connect(self.adjustSize)
        self._ui.select.clicked.connect(self._selectBoundaries)

    def _load(self):
        def addAvailableBoundary(name, key):
            self._availableBoundaries.append(SelectorItem(name, name, key))

        def addSelectedBoundary(name, key):
            self._ui.boundaries.addItem(name)
            self._boundaries.append(key)

        if self._groupId:
            self._dbElement = self._db.checkout(f'addLayers/layers/{self._groupId}')
            name = self._dbElement.getValue('groupName')
        else:
            self._dbElement = self._db.newElement('addLayers/layers')
            name = f"{baseName}{self._db.getUniqueSeq('addLayers/layers', 'groupName', baseName, 1)}"

        self._ui.groupName.setText(name)
        self._ui.numberOfLayers.setText(self._dbElement.getValue('nSurfaceLayers'))
        self._thicknessForm.setData(self._dbElement)

        self._boundaries = []
        self._availableBoundaries = []

        meshBoundaries = app.window.meshManager.boundaries()
        for gId, geometry in app.window.geometryManager.geometries().items():
            if geometry['name'] in meshBoundaries:
                cfdType = geometry['cfdType']
                if cfdType == CFDType.BOUNDARY.value or cfdType == CFDType.INTERFACE.value:
                    if app.window.geometryManager.isBoundingHex6(gId):
                        continue

                    name = geometry['name']
                    groupId = geometry['layerGroup']
                    if groupId is None:
                        addAvailableBoundary(name, gId)
                    elif groupId == self._groupId:
                        addAvailableBoundary(name, gId)
                        addSelectedBoundary(name, gId)

                    if cfdType == CFDType.INTERFACE.value:
                        name = f'{name}_slave'
                        sId = f'{gId}s'
                        groupId = geometry['slaveLayerGroup']
                        if groupId is None:
                            addAvailableBoundary(name, sId)
                        elif groupId == self._groupId:
                            addAvailableBoundary(name, sId)
                            addSelectedBoundary(name, sId)

        self._oldBoundaries = self._boundaries

    def _selectBoundaries(self):
        if self._dialog is None:
            self._dialog = MultiSelectorDialog(self, self.tr('Select Boundaries'),
                                               self._availableBoundaries, self._boundaries)
            self._dialog.itemsSelected.connect(self._setBoundaries)
        self._dialog.open()

    def _setBoundaries(self, keys):
        self._boundaries = keys
        self._ui.boundaries.clear()
        for key in keys:
            gId, isSlave = self._extractSelectorKey(key)
            if isSlave:
                self._ui.boundaries.addItem(f"{app.window.geometryManager.geometry(gId)['name']}_slave")
            else:
                self._ui.boundaries.addItem(app.window.geometryManager.geometry(gId)['name'])

    def _extractSelectorKey(self, key):
        if key[-1:] == 's':
            return key[:-1], True

        return key, False