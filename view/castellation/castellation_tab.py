#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QTreeWidgetItem, QMessageBox

from app import app
from db.simple_schema import DBError
from .refinement_item import RefinementItem, Column

DEFAULT_REFINEMENT_SURFACE_LEVEL = '1'
DEFAULT_REFINEMENT_REGION_LEVEL = '1'


class CastellationTab(QObject):
    def __init__(self, ui):
        super().__init__()

        self._ui = ui
        self._widget = ui.castellationTab

        self._surfaceItem = QTreeWidgetItem(self._ui.refinements, [self.tr('Surface')])
        self._volumeItem = QTreeWidgetItem(self._ui.refinements, [self.tr('Volume')])

        self._enabled = True

        self._ui.refinements.header().setStretchLastSection(False)
        self._ui.refinements.setColumnWidth(0, 60)
        self._ui.refinements.setColumnWidth(2, 60)
        self._surfaceItem.setFirstColumnSpanned(True)
        self._surfaceItem.setExpanded(True)
        self._volumeItem.setFirstColumnSpanned(True)
        self._volumeItem.setExpanded(True)

        self._connectSignalsSlots()

    def enable(self):
        self._ui.castellationConfiguration.setEnabled(True)

        for i in range(self._surfaceItem.childCount()):
            self._surfaceItem.child(i).enable()

        for i in range(self._volumeItem.childCount()):
            self._volumeItem.child(i).enable()

        self._ui.castellationButtons.setEnabled(True)
        self._enabled = True

    def disable(self):
        self._ui.castellationConfiguration.setEnabled(False)

        for i in range(self._surfaceItem.childCount()):
            self._surfaceItem.child(i).disable()

        for i in range(self._volumeItem.childCount()):
            self._volumeItem.child(i).disable()

        self._ui.castellationButtons.setEnabled(False)
        self._enabled = False

    def save(self):
        try:
            db = app.db.checkout('castellation')

            db.setValue('nCellsBetweenLevels', self._ui.nCellsBetweenLevels.text(),
                              self.tr('Number of Cells between Levels'))
            db.setValue('resolveFeatureAngle', self._ui.resolveFeatureAngle.text(),
                              self.tr('Feature Angle Threshold'))
            db.setValue('vtkNonManifoldEdges', self._ui.keepNonManifoldEdges.isChecked())
            db.setValue('vtkBoundaryEdges', self._ui.keepOpenEdges.isChecked())

            db.removeAllElements('refinementSurfaces')
            for i in range(self._surfaceItem.childCount()):
                item = self._surfaceItem.child(i)
                e = db.newElement('refinementSurfaces')
                e.setValue('level', item.level(), item.name() + self.tr(' Refinement Level'))
                db.addElement('refinementSurfaces', e, item.type())

            db.removeAllElements('refinementRegions')
            for i in range(self._volumeItem.childCount()):
                item = self._volumeItem.child(i)
                e = db.newElement('refinementRegions')
                e.setValue('level', item.level(), item.name() + self.tr(' Refinement Level'))
                db.addElement('refinementRegions', e, item.type())

            app.db.commit(db)

            return True
        except DBError as e:
            QMessageBox.information(self._widget, self.tr("Input Error"), e.toMessage())

            return False

    def load(self, surfaces, volumes):
        def level(gId, refinements, default):
            return refinements[gId]['level'] if gId in refinements else default

        self._ui.nCellsBetweenLevels.setText(app.db.getValue('castellation/nCellsBetweenLevels'))
        self._ui.resolveFeatureAngle.setText(app.db.getValue('castellation/resolveFeatureAngle'))
        self._ui.keepNonManifoldEdges.setChecked(app.db.getValue('castellation/vtkNonManifoldEdges'))
        self._ui.keepOpenEdges.setChecked(app.db.getValue('castellation/vtkBoundaryEdges'))

        refinementSurfaces = app.db.getElements('castellation/refinementSurfaces')
        refinementRegions = app.db.getElements('castellation/refinementRegions')

        self._surfaceItem.takeChildren()
        self._volumeItem.takeChildren()

        for geometry in surfaces:
            item = RefinementItem(geometry['gId'], geometry['name'],
                                  level(geometry['gId'], refinementSurfaces, DEFAULT_REFINEMENT_SURFACE_LEVEL))
            item.addAsChild(self._surfaceItem)

        for geometry in volumes:
            item = RefinementItem(geometry['gId'], geometry['name'],
                                  level(geometry['gId'], refinementRegions, DEFAULT_REFINEMENT_REGION_LEVEL))
            item.addAsChild(self._volumeItem)

    def _connectSignalsSlots(self):
        self._ui.refinements.itemClicked.connect(self._refinementItemClicked)

    def _refinementItemClicked(self, item, column):
        if self._enabled and column == Column.LEVEL_COLUMN.value:
            self._ui.refinements.editItem(item, column)
