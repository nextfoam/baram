#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtGui import QIntValidator, QDoubleValidator
from PySide6.QtWidgets import QDialog

from libbaram.validation import ValidationError
from widgets.async_message_box import AsyncMessageBox
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem
from widgets.validation.validation import FormValidator, NotGreaterValidator

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType
from .surface_refinement_dialog_ui import Ui_SurfaceRefinementDialog


baseName = 'Group_'


class SurfaceRefinementDialog(QDialog):
    def __init__(self, parent, db, groupId=None):
        super().__init__(parent)
        self._ui = Ui_SurfaceRefinementDialog()
        self._ui.setupUi(self)

        self._db = db
        self._groupId = groupId
        self._dbElement = None
        self._creationMode = groupId is None
        self._dialog = None
        self._surfaces = None
        self._oldSurfaces = None
        self._availableSurfaces = None

        self._xCellSize = None
        self._yCellSize = None
        self._zCellSize = None

        self._ui.minimumLevel.setValidator(QIntValidator(0, 10))
        self._ui.maximumLevel.setValidator(QIntValidator(1, 10))
        self._ui.featureEdgeRefinementLevel.setValidator(QIntValidator(0, 10))
        self._ui.curvatureNumberOfCells.setValidator(QIntValidator())
        self._ui.curvatureMaximumCellLevel.setValidator(QIntValidator(1, 10))
        self._ui.curvatureMinimumRadius.setValidator(QDoubleValidator())

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

    def _connectSignalsSlots(self):
        self._ui.minimumLevel.editingFinished.connect(self._updateMinimumLevelCellSize)
        self._ui.maximumLevel.editingFinished.connect(self._updateMaximumLevelCellSize)
        self._ui.featureEdgeRefinementLevel.editingFinished.connect(self._updateFeatureEdgeLevelCellSize)
        self._ui.curvatureMaximumCellLevel.editingFinished.connect(self._updateCurvatureMaximumLevelCellSize)
        self._ui.select.clicked.connect(self._selectSurfaces)
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        groupName = self._ui.groupName.text().strip()
        if self._db.getKeys('castellation/refinementSurfaces',
                            lambda i, e: e['groupName'] == groupName and i != self._groupId):
            await AsyncMessageBox().information(self, self.tr('Input Error'),
                                                self.tr('Group name "{0}" already exists.').format(groupName))
            return

        validator = FormValidator()
        validator.addCustomValidation(NotGreaterValidator(self._ui.minimumLevel, self._ui.maximumLevel,
                                                          self.tr('Minimum Level'), self.tr('Maximum Level')))

        valid, msg = validator.validate()
        if not valid:
            await AsyncMessageBox().information(self, self.tr('Input Error'), msg)
            return

        if not self._surfaces:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select surfaces'))
            return

        try:
            self._dbElement.setValue('groupName', groupName, self.tr('Group Name'))
            self._dbElement.setValue('surfaceRefinement/minimumLevel', self._ui.minimumLevel.text(),
                                     self.tr('Surface Refinement Minimum Level'))
            self._dbElement.setValue('surfaceRefinement/maximumLevel', self._ui.maximumLevel.text(),
                                     self.tr('Surface Refinement Maximum Level'))
            self._dbElement.setValue('featureEdgeRefinementLevel', self._ui.featureEdgeRefinementLevel.text(),
                                     self.tr('Feature Edge Refinement Level'))

            if self._ui.curvatureRefinement.isChecked():
                self._dbElement.setValue('curvatureRefinement/disabled', False)
                self._dbElement.setValue('curvatureRefinement/numberOfCells', self._ui.curvatureNumberOfCells.text(),
                                         self.tr('Number of Cells per Radius of Curvature'))
                self._dbElement.setValue('curvatureRefinement/maxLevel', self._ui.curvatureMaximumCellLevel.text(),
                                         self.tr('Curvature Refinement Maximum Level'))
                if self._ui.excludeSharpSurface.isChecked():
                    self._dbElement.setValue('curvatureRefinement/excludeSharpSurface', True)
                    self._dbElement.setValue('curvatureRefinement/minRadius', self._ui.curvatureMinimumRadius.text(),
                                             self.tr('Minimum Radius of Curvature'))
                else:
                    self._dbElement.setValue('curvatureRefinement/excludeSharpSurface', False)
            else:
                self._dbElement.setValue('curvatureRefinement/disabled', True)

            if self._groupId:
                self._db.commit(self._dbElement)
            else:
                self._groupId = self._db.addElement('castellation/refinementSurfaces', self._dbElement)

            surfaces = {gId: None for gId in self._oldSurfaces}
            for gId in self._surfaces:
                if gId in surfaces:
                    surfaces.pop(gId)
                else:
                    surfaces[gId] = self._groupId

            for gId, group in surfaces.items():
                self._db.setValue(f'geometry/{gId}/castellationGroup', group)

            super().accept()
        except ValidationError as error:
            await AsyncMessageBox().information(self, self.tr('Input Error'), error.toMessage())

    def _load(self):
        if self._groupId:
            self._dbElement = self._db.checkout(f'castellation/refinementSurfaces/{self._groupId}')
            name = self._dbElement.getValue('groupName')
        else:
            self._dbElement = self._db.newElement('castellation/refinementSurfaces')
            name = f"{baseName}{self._db.getUniqueSeq('castellation/refinementSurfaces', 'groupName', baseName, 1)}"

        self._ui.groupName.setText(name)
        self._ui.minimumLevel.setText(self._dbElement.getValue('surfaceRefinement/minimumLevel'))
        self._ui.maximumLevel.setText(self._dbElement.getValue('surfaceRefinement/maximumLevel'))
        self._ui.featureEdgeRefinementLevel.setText(self._dbElement.getValue('featureEdgeRefinementLevel'))

        self._ui.curvatureRefinement.setChecked(not self._dbElement.getValue('curvatureRefinement/disabled'))
        self._ui.curvatureNumberOfCells.setText(self._dbElement.getValue('curvatureRefinement/numberOfCells'))
        self._ui.curvatureMaximumCellLevel.setText(self._dbElement.getValue('curvatureRefinement/maxLevel'))
        self._ui.excludeSharpSurface.setChecked(self._dbElement.getValue('curvatureRefinement/excludeSharpSurface'))
        if self._dbElement.getFloat('curvatureRefinement/minRadius') > 0:
            self._ui.curvatureMinimumRadius.setText(self._dbElement.getValue('curvatureRefinement/minRadius'))
        else:
            self._ui.curvatureMinimumRadius.setText(str(min(self._xCellSize, self._yCellSize, self._zCellSize)))

        self._surfaces = []
        self._availableSurfaces = []
        for gId, geometry in self._db.getElements('geometry').items():
            if geometry.value('gType') == GeometryType.SURFACE.value:
                if app.window.geometryManager.isBoundingHex6(gId):
                    continue

                name = geometry.value('name')
                groupId = geometry.value('castellationGroup')
                if groupId is None:
                    self._availableSurfaces.append(SelectorItem(name, name, gId))
                elif groupId == self._groupId:
                    self._availableSurfaces.append(SelectorItem(name, name, gId))
                    self._ui.surfaces.addItem(name)
                    self._surfaces.append(gId)

        self._oldSurfaces = self._surfaces

        self._updateMinimumLevelCellSize()
        self._updateMaximumLevelCellSize()
        self._updateFeatureEdgeLevelCellSize()
        self._updateCurvatureMaximumLevelCellSize()

    def _updateMinimumLevelCellSize(self):
        self._updateCellSize(self._ui.minimumLevel, self._ui.minimumLevelCellSize)

    def _updateMaximumLevelCellSize(self):
        self._updateCellSize(self._ui.maximumLevel, self._ui.maximumLevelCellSzie)

    def _updateFeatureEdgeLevelCellSize(self):
        self._updateCellSize(self._ui.featureEdgeRefinementLevel, self._ui.featureEdgeLevelCellSize)

    def _updateCurvatureMaximumLevelCellSize(self):
        self._updateCellSize(self._ui.curvatureMaximumCellLevel, self._ui.curvatureCellSize)

    def _selectSurfaces(self):
        self._dialog = MultiSelectorDialog(self, self.tr('Select Surfaces'), self._availableSurfaces, self._surfaces)
        self._dialog.itemsSelected.connect(self._setSurfaces)
        self._dialog.open()

    def _setSurfaces(self, items):
        self._surfaces = []
        self._ui.surfaces.clear()
        for gId, name in items:
            self._surfaces.append(gId)
            self._ui.surfaces.addItem(name)

    def _updateCellSize(self, level, cellSize):
        d = 2 ** int(level.text())
        cellSize.setText(
            'cell size <b>({:6g} x {:6g} x {:6g})</b>'.format(
                self._xCellSize / d, self._yCellSize / d, self._zCellSize / d))
