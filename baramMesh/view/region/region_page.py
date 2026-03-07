#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QVBoxLayout, QMenu, QMessageBox

from baramMesh.app import app
from baramMesh.view.step_page import StepPage
from baramMesh.db.configurations_schema import CFDType, GeometryType, Shape
from .region_form import RegionForm
from .region_card import RegionCard
from .region_point_finder import getVolumePolyData, findInteriorPoint
from widgets.multi_selector_dialog import MultiSelectorDialog, SelectorItem


class RegionPage(StepPage):
    OUTPUT_TIME = 0

    def __init__(self, ui):
        super().__init__(ui, ui.regionPage)

        self._ui = ui
        self._form = None
        self._regions = {}
        self._bounds = None

        self._form = RegionForm(self._ui.renderingView, self)
        self._focusing = self._form

        layout = QVBoxLayout(self._ui.regionList)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self._ui.regionList.layout().insertWidget(0, self._form)

        self._connectSignalsSlots()

    def isNextStepAvailable(self):
        if not self._regions:
            if app.db.elementCount('region') > 0:
                return True

            self._ui.regionEmptyMessage.setVisible(True)
            self._ui.regionValidationMessage.hide()
            return False

        self._ui.regionEmptyMessage.setVisible(False)

        # hasFluid = False
        available = True
        for card in self._regions.values():
            # hasFluid = hasFluid or card.type() == RegionType.FLUID.value
            if not self._bounds.includes(card.point()):
                card.showWarning()
                available = False
            else:
                card.hideWarning()

        multiRegion = len(self._regions) > 1
        hasInterRegionInterface = app.db.elementCount(
            'geometry', lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and e['interRegion']) > 0

        if multiRegion == hasInterRegionInterface:
            self._ui.regionValidationMessage.hide()
            return available

        if multiRegion:
            self._ui.regionValidationMessage.setText(self.tr(
                'No Inter-Region Interface is configured while Region points are configured.'))
        else:
            self._ui.regionValidationMessage.setText(self.tr(
                'Only one Region Point is configured while Inter-Region Interface is configured in Geometry Step.'))
        self._ui.regionValidationMessage.show()

        return False

    def open(self):
        if self._loaded:
            self._updateBounds()
        else:
            self.load()

    async def show(self, isCurrentStep, batchRunning):
        if not self._loaded:
            self.load()

        app.window.meshManager.unload()

    async def hide(self):
        self._form.cancel()
        self._ui.regionValidationMessage.hide()

        return True

    def removeForm(self, form):
        self._ui.regionList.layout().removeWidget(self._form)
        self._form.setOwner(None)

    def _outputPath(self):
        return None

    def _enableStep(self):
        self._ui.regionAdd.setEnabled(True)
        self._ui.regionMenuButton.setEnabled(True)

        for card in self._regions.values():
            card.setEnabled(True)

    def _disableStep(self):
        self._ui.regionAdd.setEnabled(False)
        self._ui.regionMenuButton.setEnabled(False)

        for card in self._regions.values():
            card.setEnabled(False)

    def _clear(self):
        for card in self._regions.values():
            self._ui.regionList.layout().removeWidget(card)
            card.deleteLater()

        self._regions = {}

    def _connectSignalsSlots(self):
        self._ui.regionArea.verticalScrollBar().rangeChanged.connect(self._focus)
        self._ui.regionAdd.clicked.connect(self._showFormForAdding)
        self._ui.regionMenuButton.clicked.connect(self._showRegionMenu)

        self._form.regionAdded.connect(self._add)
        self._form.regionEdited.connect(self._update)
        self._form.canceled.connect(self._formCanceled)

    def load(self):
        self._updateBounds()

        regions = app.db.getElements('region')
        for id_ in regions:
            self._add(id_)

        self._loaded = True

    def _updateBounds(self):
        bounds = app.window.geometryManager.getBounds()
        if bounds is not None:
            self._bounds = bounds
            self._form.setBounds(self._bounds)

    def _showFormForAdding(self):
        layout = self._ui.regionList.layout()
        if self._form.owner() == self:
            if index := layout.indexOf(self._form):
                layout.takeAt(index)
                layout.insertWidget(0, self._form)
        else:
            self._form.owner().removeForm(self._form)
            layout.insertWidget(0, self._form)

        self._form.setupForAdding()
        self._form.setOwner(self)
        self._showForm()

    def _showFormForEditing(self, id_):
        self._form.owner().removeForm(self._form)
        self._regions[id_].addForm(self._form)
        self._form.setupForEditing(id_)
        self._form.setOwner(self._regions[id_])
        self._showForm()

    def _add(self, id_):
        card = RegionCard(id_)
        self._regions[id_] = card
        card.editClicked.connect(self._showFormForEditing)
        card.removeClicked.connect(self._remove)
        self._ui.regionList.layout().insertWidget(0, card)

        self._moveFocus(card)
        self._updateNextStepAvailable()
        self._form.hide()

    def _update(self, id_):
        self._regions[id_].load()
        self._hideForm()

    def _remove(self, id_):
        db = app.db.checkout()
        db.removeElement('region', id_)
        app.db.commit(db)

        card = self._regions[id_]
        self._ui.regionList.layout().removeWidget(card)
        card.deleteLater()
        del self._regions[id_]

        self._updateNextStepAvailable()

    def _formCanceled(self):
        self._hideForm()

    def _hideForm(self):
        if owner := self._form.owner():
            owner.removeForm(self._form)

        self._ui.regionList.layout().insertWidget(0, self._form)
        self._form.setOwner(self)
        self._form.hide()
        self._updateNextStepAvailable()

    def _showForm(self):
        self._form.show()
        self._moveFocus(self._form)
        self.stepReset.emit()

    def _moveFocus(self, widget):
        self._focusing = widget
        self._focus()

    def _focus(self):
        if self._focusing.isVisible():
            self._ui.regionArea.ensureWidgetVisible(self._focusing)

    def _showRegionMenu(self):
        menu = QMenu(self._widget)

        batchAction = QAction(self.tr('Batch Add from Volumes'), menu)
        batchAction.triggered.connect(self._autoAddRegions)
        menu.addAction(batchAction)

        btn = self._ui.regionMenuButton
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _autoAddRegions(self):
        geometries = app.db.getElements('geometry')

        if not geometries:
            QMessageBox.information(
                self._widget, 
                self.tr('No Geometries'),
                self.tr('No geometries available. Please add geometries in the Geometry step first.')
            )
            return

        items = []
        for gId, geometry in geometries.items():
            name = geometry.value('name')
            gType = geometry.value('gType')

            if gType == GeometryType.VOLUME.value:
                items.append(SelectorItem(
                    label=f"{name} (Volume)",
                    text=name,
                    value=gId,
                    removable=True
                ))

        if not items:
            QMessageBox.information(
                self._widget,
                self.tr('No Valid Geometries'),
                self.tr('No valid geometries found. Only volumes and closed surfaces can be used for auto region creation.')
            )
            return

        dialog = MultiSelectorDialog(
            self._widget,
            self.tr('Select Geometries for Auto Region Creation'),
            items,
            []
        )

        dialog.itemsSelected.connect(self._createRegionsFromGeometries)
        dialog.exec()

    def _createRegionsFromGeometries(self, selectedItems):
        if not selectedItems:
            return

        geometryManager = app.window.geometryManager
        geometries = app.db.getElements('geometry')

        created_count = 0
        skipped_count = 0
        skipped_names = []

        for gId, label in selectedItems:
            geometry = geometries.get(gId)
            if not geometry:
                continue

            name = geometry.value('name')
            gType = geometry.value('gType')

            try:
                polyData = getVolumePolyData(gId, geometryManager, geometries)
                point = findInteriorPoint(polyData)

                if point is None:
                    skipped_count += 1
                    skipped_names.append(name)
                    continue

                self._createRegion(name, point)
                created_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_names.append(name)
                print(f"Error creating region for {name}: {e}")

        message = self.tr(f'Successfully created {created_count} region(s).')
        if skipped_count > 0:
            message += self.tr(f'\n\nSkipped {skipped_count} geometry(ies):')
            for name in skipped_names:
                message += f'\n  - {name}'
            message += self.tr('\n\n(Surfaces must be closed to create regions automatically)')

        QMessageBox.information(self._widget, self.tr('Auto Region Creation'), message)

    def _createRegion(self, baseName, point):
        db = app.db.checkout()

        regionName = f"{baseName}_Region"
        seq = db.getUniqueSeq('region', 'name', regionName, '')
        uniqueName = regionName + seq

        element = db.newElement('region')
        element.setValue('name', uniqueName)
        element.setValue('type', 'fluid')  # Default to fluid
        element.setValue('point/x', '{:.6g}'.format(point[0]))
        element.setValue('point/y', '{:.6g}'.format(point[1]))
        element.setValue('point/z', '{:.6g}'.format(point[2]))

        regionId = db.addElement('region', element)
        app.db.commit(db)

        self._add(regionId)
