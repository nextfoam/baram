#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramMesh.app import app
from baramMesh.db.simple_schema import DBError
from baramMesh.db.configurations_schema import GeometryType
from baramMesh.view.widgets.multi_selector_dialog import MultiSelectorDialog
from baramMesh.view.widgets.multi_selector_dialog import SelectorItem
from .volume_refinement_dialog_ui import Ui_VolumeeRefinementDialog


baseName = 'Group_'


class VolumeRefinementDialog(QDialog):

    def __init__(self, parent, db, groupId=None):
        super().__init__(parent)
        self._ui = Ui_VolumeeRefinementDialog()
        self._ui.setupUi(self)

        self._db = db
        self._dbElement = None
        self._creationMode = groupId is None
        self._accepted = False
        self._dialog = None
        self._volumes = None
        self._oldVolumes = None
        self._groupId = groupId
        self._availableVolumes = None

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
            if self._db.getKeys('castellation/refinementVolumes',
                                lambda i, e: e['groupName'] == groupName and i != self._groupId):
                QMessageBox.information(self, self.tr('Input Error'),
                                        self.tr('Group name "{0}" already exists.').format(groupName))
                return

            if not self._volumes:
                QMessageBox.information(self, self.tr('Input Error'), self.tr('Select volumes'))
                return

            self._dbElement.setValue('groupName', groupName, self.tr('Group Name'))
            self._dbElement.setValue('volumeRefinementLevel', self._ui.volumeRefinementLevel.text(),
                                     self.tr('Volume Refinement Level'))

            if self._groupId:
                self._db.commit(self._dbElement)
            else:
                self._groupId = self._db.addElement('castellation/refinementVolumes', self._dbElement)

            volumes = {gId: None for gId in self._oldVolumes}
            for gId in self._volumes:
                if gId in volumes:
                    volumes.pop(gId)
                else:
                    volumes[gId] = self._groupId

            geometryManager = app.window.geometryManager
            for gId, group in volumes.items():
                self._db.setValue(f'geometry/{gId}/castellationGroup', group)
                geometryManager.updateGeometryProperty(gId, 'castellationGroup', group)

            super().accept()
        except DBError as error:
            QMessageBox.information(self, self.tr('Input Error'), error.toMessage())

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectVolumes)

    def _load(self):
        if self._groupId:
            self._dbElement = self._db.checkout(f'castellation/refinementVolumes/{self._groupId}')
            name = self._dbElement.getValue('groupName')
        else:
            self._dbElement = self._db.newElement('castellation/refinementVolumes')
            name = f"{baseName}{self._db.getUniqueSeq('castellation/refinementVolumes', 'groupName', baseName, 1)}"

        self._ui.groupName.setText(name)
        self._ui.volumeRefinementLevel.setText(self._dbElement.getValue('volumeRefinementLevel'))

        self._volumes = []
        self._availableVolumes = []
        for gId, geometry in app.window.geometryManager.geometries().items():
            if geometry['gType'] != GeometryType.VOLUME.value:
                continue

            if app.window.geometryManager.isBoundingHex6(gId):
                continue

            name = geometry['name']
            groupId = geometry['castellationGroup']
            if groupId is None:
                self._availableVolumes.append(SelectorItem(name, name, gId))
            elif groupId == self._groupId:
                self._availableVolumes.append(SelectorItem(name, name, gId))
                self._ui.volumes.addItem(name)
                self._volumes.append(gId)

        self._oldVolumes = self._volumes

    def _selectVolumes(self):
        self._dialog = MultiSelectorDialog(self, self.tr('Select Volumes'), self._availableVolumes, self._volumes)
        self._dialog.itemsSelected.connect(self._setVolumes)
        self._dialog.open()

    def _setVolumes(self, gIds):
        self._volumes = gIds
        self._ui.volumes.clear()
        for gId in gIds:
            self._ui.volumes.addItem(app.window.geometryManager.geometry(gId)['name'])
