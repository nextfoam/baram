#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from app import app
from db.simple_schema import DBError
from view.widgets.multi_selector_dialog import MultiSelectorDialog
from .volume_refinement_dialog_ui import Ui_VolumeeRefinementDialog


class VolumeRefinementDialog(QDialog):

    def __init__(self, parent, availableVolumes, dbElement=None, groupId=None):
        super().__init__(parent)
        self._ui = Ui_VolumeeRefinementDialog()
        self._ui.setupUi(self)

        self._dbElement = None
        self._creationMode = True
        self._accepted = False
        self._dialog = None
        self._volumes = None
        self._groupId = groupId
        self._availableVolumes = availableVolumes

        self._connectSignalsSlots()

        self._load(dbElement)

    def dbElement(self):
        return self._dbElement

    def groupId(self):
        return self._groupId

    def isCreationMode(self):
        return self._creationMode

    def accept(self):
        try:
            self._dbElement.setValue('groupName', self._ui.groupName.text(), self.tr('Group Name'))
            self._dbElement.setValue('volumeRefinementLevel', self._ui.volumeRefinementLevel.text(),
                                     self.tr('Volume Refinement Level'))
            if not self._volumes:
                QMessageBox.information(self, self.tr('Input Error'), self.tr('Select volumes'))
                return

            self._dbElement.setValue('volumes', self._volumes)

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr('Input Error'), e.toMessage())

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectVolumes)

    def _load(self, dbElement):
        if dbElement:
            self._dbElement = dbElement
            self._creationMode = False
        else:
            self._dbElement = app.db.newElement('castellation/refinementVolumes')

        self._ui.groupName.setText(self._dbElement.getValue('groupName'))
        self._ui.volumeRefinementLevel.setText(self._dbElement.getValue('volumeRefinementLevel'))

        self._setVolumes(self._dbElement.getValue('volumes'))

    def _selectVolumes(self):
        self._dialog = MultiSelectorDialog(self, self.tr('Select Volumes'), self._availableVolumes, self._volumes)
        self._dialog.itemsSelected.connect(self._setVolumes)
        self._dialog.open()

    def _setVolumes(self, gIds):
        self._volumes = gIds
        self._ui.volumes.clear()
        for gId in gIds:
            self._ui.volumes.addItem(app.window.geometryManager.geometry(gId)['name'])
