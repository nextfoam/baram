#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QMessageBox

from app import app
from db.simple_schema import DBError
from view.widgets.multi_selector_dialog import MultiSelectorDialog
from .surface_refinement_dialog_ui import Ui_SurfaceRefinementDialog


class SurfaceRefinementDialog(QDialog):

    def __init__(self, parent, availableSurfaces, dbElement=None, groupId=None):
        super().__init__(parent)
        self._ui = Ui_SurfaceRefinementDialog()
        self._ui.setupUi(self)

        self._dbElement = None
        self._creationMode = True
        self._accepted = False
        self._dialog = None
        self._surfaces = None
        self._groupId = groupId
        self._availableSurfaces = availableSurfaces

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
            self._dbElement.setValue('surfaceRefinementLevel', self._ui.surfaceRefinementLevel.text(),
                                     self.tr('Surface Refinement Level'))
            self._dbElement.setValue('featureEdgeRefinementLevel', self._ui.featureEdgeRefinementLevel.text(),
                                     self.tr('Feature Edge Refinement Level'))
            if not self._surfaces:
                QMessageBox.information(self, self.tr('Input Error'), self.tr('Select surfaces'))
                return

            self._dbElement.setValue('surfaces', self._surfaces)

            super().accept()
        except DBError as e:
            QMessageBox.information(self, self.tr('Input Error'), e.toMessage())

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectSurfaces)

    def _load(self, dbElement):
        if dbElement:
            self._dbElement = dbElement
            self._creationMode = False
        else:
            self._dbElement = app.db.newElement('castellation/refinementSurfaces')

        self._ui.groupName.setText(self._dbElement.getValue('groupName'))
        self._ui.surfaceRefinementLevel.setText(self._dbElement.getValue('surfaceRefinementLevel'))
        self._ui.featureEdgeRefinementLevel.setText(self._dbElement.getValue('featureEdgeRefinementLevel'))

        self._setSurfaces(self._dbElement.getValue('surfaces'))

    def _selectSurfaces(self):
        self._dialog = MultiSelectorDialog(self, self.tr('Select Surfaces'), self._availableSurfaces, self._surfaces)
        self._dialog.itemsSelected.connect(self._setSurfaces)
        self._dialog.open()

    def _setSurfaces(self, gIds):
        self._surfaces = gIds
        self._ui.surfaces.clear()
        for gId in gIds:
            self._ui.surfaces.addItem(app.window.geometryManager.geometry(gId)['name'])
