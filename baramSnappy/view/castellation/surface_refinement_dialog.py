#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from baramSnappy.app import app
from baramSnappy.db.simple_schema import DBError
from baramSnappy.db.configurations_schema import GeometryType
from baramSnappy.view.widgets.multi_selector_dialog import MultiSelectorDialog
from baramSnappy.view.widgets.multi_selector_dialog import SelectorItem
from .surface_refinement_dialog_ui import Ui_SurfaceRefinementDialog


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
            if self._db.getKeys('castellation/refinementSurfaces',
                                lambda i, e: e['groupName'] == groupName and i != self._groupId):
                QMessageBox.information(self, self.tr('Input Error'),
                                        self.tr('Group name "{0}" already exists.').format(groupName))
                return

            if not self._surfaces:
                QMessageBox.information(self, self.tr('Input Error'), self.tr('Select surfaces'))
                return

            self._dbElement.setValue('groupName', groupName, self.tr('Group Name'))
            self._dbElement.setValue('surfaceRefinementLevel', self._ui.surfaceRefinementLevel.text(),
                                     self.tr('Surface Refinement Level'))
            self._dbElement.setValue('featureEdgeRefinementLevel', self._ui.featureEdgeRefinementLevel.text(),
                                     self.tr('Feature Edge Refinement Level'))

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

            geometryManager = app.window.geometryManager
            for gId, group in surfaces.items():
                self._db.setValue(f'geometry/{gId}/castellationGroup', group)
                geometryManager.updateGeometryProperty(gId, 'castellationGroup', group)

            super().accept()
        except DBError as error:
            QMessageBox.information(self, self.tr('Input Error'), error.toMessage())

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurfaces)

    def _load(self):
        if self._groupId:
            self._dbElement = self._db.checkout(f'castellation/refinementSurfaces/{self._groupId}')
        else:
            self._dbElement = self._db.newElement('castellation/refinementSurfaces')

        self._ui.groupName.setText(self._dbElement.getValue('groupName'))
        self._ui.surfaceRefinementLevel.setText(self._dbElement.getValue('surfaceRefinementLevel'))
        self._ui.featureEdgeRefinementLevel.setText(self._dbElement.getValue('featureEdgeRefinementLevel'))

        self._surfaces = []
        self._availableSurfaces = []
        for gId, geometry in app.window.geometryManager.geometries().items():
            if geometry['gType'] == GeometryType.SURFACE.value:
                if app.window.geometryManager.isBoundingHex6(gId):
                    continue

                name = geometry['name']
                groupId = geometry['castellationGroup']
                if groupId is None:
                    self._availableSurfaces.append(SelectorItem(name, name, gId))
                elif groupId == self._groupId:
                    self._availableSurfaces.append(SelectorItem(name, name, gId))
                    self._ui.surfaces.addItem(name)
                    self._surfaces.append(gId)

        self._oldSurfaces = self._surfaces

    def _selectSurfaces(self):
        self._dialog = MultiSelectorDialog(self, self.tr('Select Surfaces'), self._availableSurfaces, self._surfaces)
        self._dialog.itemsSelected.connect(self._setSurfaces)
        self._dialog.open()

    def _setSurfaces(self, gIds):
        self._surfaces = gIds
        self._ui.surfaces.clear()
        for gId in gIds:
            self._ui.surfaces.addItem(app.window.geometryManager.geometry(gId)['name'])
