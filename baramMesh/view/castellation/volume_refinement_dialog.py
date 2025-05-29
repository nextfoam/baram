#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QDialog

from libbaram.simple_db.simple_schema import DBError
from widgets.async_message_box import AsyncMessageBox
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType, GapRefinementMode
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

        self._ui.direction.addItem(self.tr('Mixed'),    GapRefinementMode.MIXED)
        self._ui.direction.addItem(self.tr('Inside'),   GapRefinementMode.INSIDE)
        self._ui.direction.addItem(self.tr('Outside'),  GapRefinementMode.OUTSIDE)

        self._xCellSize = None
        self._yCellSize = None
        self._zCellSize = None

        self._ui.volumeRefinementLevel.setValidator(QIntValidator(0, 100))

        self._xCellSize, self._yCellSize, self._zCellSize = app.window.geometryManager.getCellSize()

        self._connectSignalsSlots()

        self._load()

    def dbElement(self):
        return self._dbElement

    def groupId(self):
        return self._groupId

    def isCreationMode(self):
        return self._creationMode

    def disableEdit(self):
        self._ui.parameters.setEnabled(False)
        self._ui.select.setEnabled(False)
        self._ui.ok.hide()
        self._ui.cancel.setText(self.tr('Close'))

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            groupName = self._ui.groupName.text().strip()
            if self._db.getKeys('castellation/refinementVolumes',
                                lambda i, e: e['groupName'] == groupName and i != self._groupId):
                await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                    self.tr('Group name "{0}" already exists.').format(groupName))
                return

            if not self._volumes:
                await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select volumes'))
                return

            self._dbElement.setValue('groupName', groupName, self.tr('Group Name'))
            self._dbElement.setValue('volumeRefinementLevel', self._ui.volumeRefinementLevel.text(),
                                     self.tr('Volume Refinement Level'))

            if self._ui.gapRefinement.isChecked():
                try:
                    startLevel = int(self._ui.detectionStartLevel.text())
                    maxLevel = int(self._ui.maxRefinementLevel.text())

                    if startLevel >= maxLevel:
                        await AsyncMessageBox().information(
                            self, self.tr('Input Error'),
                            self.tr('Maximum Refinement Level must be greater than Gap Detection Start Level.'))

                        return
                except ValueError:
                    pass

                self._dbElement.setValue('gapRefinement/minCellLayers', self._ui.minCellLayers.text(),
                                         self.tr('Min. Cell Layers in a gap'))
                self._dbElement.setValue('gapRefinement/detectionStartLevel', self._ui.detectionStartLevel.text(),
                                         self.tr('Gap Detection Start Level'))
                self._dbElement.setValue('gapRefinement/maxRefinementLevel', self._ui.maxRefinementLevel.text(),
                                         self.tr('Max. Refinement Level'))
                self._dbElement.setValue('gapRefinement/direction', self._ui.direction.currentData())
                self._dbElement.setValue('gapRefinement/gapSelf', self._ui.gapSelf.isChecked())
            else:
                self._dbElement.setValue('gapRefinement/direction', GapRefinementMode.NONE)

            if self._ui.levelIncrement.isChecked():
                self._dbElement.setValue('levelIncrement/disabled', False)
                self._dbElement.setValue('levelIncrement/splitCountX', self._ui.splitCountX.text(),
                                         self.tr('Splict Count per Direction'))
                self._dbElement.setValue('levelIncrement/splitCountY', self._ui.splitCountY.text(),
                                         self.tr('Splict Count per Direction'))
                self._dbElement.setValue('levelIncrement/splitCountZ', self._ui.splitCountZ.text(),
                                         self.tr('Splict Count per Direction'))
                self._dbElement.setValue('levelIncrement/minLevel', self._ui.directionalMinLevel.text(),
                                         self.tr('Min. Level'))
                self._dbElement.setValue('levelIncrement/maxLevel', self._ui.directionalMaxLevel.text(),
                                         self.tr('Max. Level'))
            else:
                self._dbElement.setValue('levelIncrement/disabled', True)

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

            for gId, group in volumes.items():
                self._db.setValue(f'geometry/{gId}/castellationGroup', group)

            super().accept()
        except DBError as error:
            await AsyncMessageBox().information(self, self.tr('Input Error'), error.toMessage())

    def _connectSignalsSlots(self):
        self._ui.volumeRefinementLevel.editingFinished.connect(self._updateCellSize)
        self._ui.select.clicked.connect(self._selectVolumes)
        self._ui.ok.clicked.connect(self._accept)
        self._ui.cancel.clicked.connect(self.close)

    def _load(self):
        if self._groupId:
            self._dbElement = self._db.checkout(f'castellation/refinementVolumes/{self._groupId}')
            name = self._dbElement.getValue('groupName')
        else:
            self._dbElement = self._db.newElement('castellation/refinementVolumes')
            name = f"{baseName}{self._db.getUniqueSeq('castellation/refinementVolumes', 'groupName', baseName, 1)}"

        self._ui.groupName.setText(name)
        self._ui.volumeRefinementLevel.setText(self._dbElement.getValue('volumeRefinementLevel'))

        direction = self._dbElement.getEnum('gapRefinement/direction')
        self._ui.gapRefinement.setChecked(direction != GapRefinementMode.NONE)
        self._ui.minCellLayers.setText(self._dbElement.getValue('gapRefinement/minCellLayers'))
        self._ui.detectionStartLevel.setText(self._dbElement.getValue('gapRefinement/detectionStartLevel'))
        self._ui.maxRefinementLevel.setText(self._dbElement.getValue('gapRefinement/maxRefinementLevel'))
        if direction != GapRefinementMode.NONE:
            self._ui.direction.setCurrentIndex(self._ui.direction.findData(direction))
        self._ui.gapSelf.setChecked(self._dbElement.getValue('gapRefinement/gapSelf'))

        self._ui.levelIncrement.setChecked(not self._dbElement.getValue('levelIncrement/disabled'))
        self._ui.splitCountX.setText(self._dbElement.getValue('levelIncrement/splitCountX'))
        self._ui.splitCountY.setText(self._dbElement.getValue('levelIncrement/splitCountY'))
        self._ui.splitCountZ.setText(self._dbElement.getValue('levelIncrement/splitCountZ'))
        self._ui.directionalMinLevel.setText(self._dbElement.getValue('levelIncrement/minLevel'))
        self._ui.directionalMaxLevel.setText(self._dbElement.getValue('levelIncrement/maxLevel'))

        self._volumes = []
        self._availableVolumes = []
        for gId, geometry in self._db.getElements('geometry').items():
            if geometry.value('gType') != GeometryType.VOLUME.value:
                continue

            if app.window.geometryManager.isBoundingHex6(gId):
                continue

            name = geometry.value('name')
            groupId = geometry.value('castellationGroup')
            if groupId is None:
                self._availableVolumes.append(SelectorItem(name, name, gId))
            elif groupId == self._groupId:
                self._availableVolumes.append(SelectorItem(name, name, gId))
                self._ui.volumes.addItem(name)
                self._volumes.append(gId)

        self._oldVolumes = self._volumes

        self._updateCellSize()

    def _updateCellSize(self):
        d = 2 ** int(self._ui.volumeRefinementLevel.text())
        self._ui.cellSize.setText(
            'cell size <b>({:g} x {:g} x {:g})</b>'.format(
                self._xCellSize / d, self._yCellSize / d, self._zCellSize / d))

    def _selectVolumes(self):
        self._dialog = MultiSelectorDialog(self, self.tr('Select Volumes'), self._availableVolumes, self._volumes)
        self._dialog.itemsSelected.connect(self._setVolumes)
        self._dialog.open()

    def _setVolumes(self, items):
        self._volumes = []
        self._ui.volumes.clear()
        for gId, name in items:
            self._volumes.append(gId)
            self._ui.volumes.addItem(name)
