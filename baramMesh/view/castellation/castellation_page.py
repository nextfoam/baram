#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtGui import QIntValidator

from libbaram.exception import CanceledException
from libbaram.process import ProcessError
from libbaram.simple_db.simple_schema import ValidationError
from widgets.async_message_box import AsyncMessageBox
from widgets.list_table import ListItemWithButtons

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType
from baramMesh.db.configurations import defaultsDB
from baramMesh.openfoam.utility.snappy_hex_mesh import snappyHexMesh, CASTELLATION_OUTPUT_TIME
from baramMesh.view.main_window.main_window_ui import Ui_MainWindow
from baramMesh.view.step_page import StepPage
from .surface_refinement_dialog import SurfaceRefinementDialog
from .volume_refinement_dialog import VolumeRefinementDialog


class CastellationPage(StepPage):
    OUTPUT_TIME = CASTELLATION_OUTPUT_TIME

    def __init__(self, ui: Ui_MainWindow):
        super().__init__(ui, ui.castellationPage)

        self._ui = ui
        self._db = None
        self._dialog = None
        self._cm = None

        ui.castellationConfigurationHeader.setContents(ui.castellationConfiguration)
        ui.castellationAdvancedHeader.setContents(ui.castellationAdvanced)
        ui.surfaceRefinementHeader.setContents(ui.surfaceRefinement)
        ui.volumeRefinementHeader.setContents(ui.volumeRefinement)

        ui.surfaceRefinement.setBackgroundColor()
        ui.volumeRefinement.setBackgroundColor()
        ui.surfaceRefinement.setHeaderWithWidth([0, 0, 0, 16, 16])
        ui.volumeRefinement.setHeaderWithWidth([0, 0, 16, 16])

        ui.nCellsBetweenLevels.setValidator(QIntValidator(1, 1000000))

        ui.castellationCancel.hide()

        self._connectSignalsSlots()

    async def show(self, isCurrentStep, batchRunning):
        self.load()
        self.updateWorkingStatus()

    async def save(self):
        try:
            castellation = self._db.checkout('castellation')

            castellation.setValue('nCellsBetweenLevels', self._ui.nCellsBetweenLevels.text(),
                              self.tr('Number of Cells between Levels'))
            castellation.setValue('resolveFeatureAngle', self._ui.resolveFeatureAngle.text(),
                              self.tr('Feature Angle Threshold'))
            castellation.setValue('vtkNonManifoldEdges', self._ui.keepNonManifoldEdges.isChecked())
            castellation.setValue('vtkBoundaryEdges', self._ui.keepOpenEdges.isChecked())

            castellation.setValue('maxGlobalCells', self._ui.maxGlobalCells.text(), self.tr('Max. Global Cell Count'))
            castellation.setValue('maxLocalCells', self._ui.maxLocalCells.text(), self.tr('Max. Local Cell Count'))
            castellation.setValue('minRefinementCells', self._ui.minRefinementCells.text(),
                              self.tr('Min.Refinement Cell Count'))
            castellation.setValue('maxLoadUnbalance', self._ui.maxLoadUnbalance.text(), self.tr('Max. Load Unbalance'))
            castellation.setValue('allowFreeStandingZoneFaces', self._ui.allowFreeStandingZoneFaces.isChecked())

            self._db.commit(castellation)
            app.db.commit(self._db)

            self._db = app.db.checkout()

            return True
        except ValidationError as e:
            await AsyncMessageBox().information(self._widget, self.tr('Input Error'), e.toMessage())
            return False

    def load(self):
        self._db = app.db.checkout()

        if self._loaded:
            return

        castellation = self._db.getElement('castellation')
        self._setConfigurastions(castellation)

        self._ui.surfaceRefinement.clear()
        self._ui.volumeRefinement.clear()

        groups = {GeometryType.SURFACE.value: set(), GeometryType.VOLUME.value: set()}
        for gId, geometry in self._db.getElements('geometry').items():
            if group := geometry.value('castellationGroup'):
                groups[geometry.value('gType')].add(group)

        for groupId, element in castellation.elements('refinementSurfaces').items():
            if groupId in groups[GeometryType.SURFACE.value]:
                surfaceRefinement = element.element('surfaceRefinement')
                self._addSurfaceRefinementItem(
                    groupId, element.value('groupName'),
                    surfaceRefinement.value('minimumLevel'), surfaceRefinement.value('maximumLevel'))
            else:
                self._db.removeElement('castellation/refinementSurfaces', groupId)

        for groupId, element in castellation.elements('refinementVolumes').items():
            if groupId in groups[GeometryType.VOLUME.value]:
                self._addVolumeRefinementItem(groupId,
                                              element.value('groupName'), element.value('volumeRefinementLevel'))
            else:
                self._db.removeElement('castellation/refinementVolumes', groupId)

        self._loaded = True

    async def runInBatchMode(self):
        if not await self.save():
            return False

        self._ui.refine.setEnabled(False)

        return await self._run()

    def _connectSignalsSlots(self):
        self._ui.loadCastellationDefaults.clicked.connect(self._loadDefaults)
        self._ui.surfaceRefinementAdd.clicked.connect(lambda: self._openSurfaceRefinementDialog())
        self._ui.volumeRefinementAdd.clicked.connect(lambda: self._openVolumeRefinementDialog())
        self._ui.refine.clicked.connect(self._refine)
        self._ui.castellationCancel.clicked.connect(snappyHexMesh.cancel)
        self._ui.castellationReset.clicked.connect(self._reset)

    @qasync.asyncSlot()
    async def _loadDefaults(self):
        if await AsyncMessageBox().confirm(
                self._widget, self.tr('Reset Settings'),
                self.tr(
                    'Would you like to reset all Castallation settings to default, excluding the Refinement Groups?')):
            self._setConfigurastions(defaultsDB.getElement('castellation'))

    def _setConfigurastions(self, castellation):
        self._ui.nCellsBetweenLevels.setText(castellation.value('nCellsBetweenLevels'))
        self._ui.resolveFeatureAngle.setText(castellation.value('resolveFeatureAngle'))
        self._ui.keepNonManifoldEdges.setChecked(castellation.value('vtkNonManifoldEdges'))
        self._ui.keepOpenEdges.setChecked(castellation.value('vtkBoundaryEdges'))

        self._ui.maxGlobalCells.setText(castellation.value('maxGlobalCells'))
        self._ui.maxLocalCells.setText(castellation.value('maxLocalCells'))
        self._ui.minRefinementCells.setText(castellation.value('minRefinementCells'))
        self._ui.maxLoadUnbalance.setText(castellation.value('maxLoadUnbalance'))
        self._ui.allowFreeStandingZoneFaces.setChecked(castellation.value('allowFreeStandingZoneFaces'))

    def _openSurfaceRefinementDialog(self, groupId=None):
        self._dialog = SurfaceRefinementDialog(self._widget, self._db, groupId)
        if self._locked:
            self._dialog.disableEdit()
        else:
            self._dialog.accepted.connect(self._surfaceRefinementDialogAccepted)
        self._dialog.open()

    def _openVolumeRefinementDialog(self, groupId=None):
        self._dialog = VolumeRefinementDialog(self._widget, self._db, groupId)
        if self._locked:
            self._dialog.disableEdit()
        else:
            self._dialog.accepted.connect(self._volumeRefinementDialogAccepted)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _refine(self):
        if not await self.save():
            return

        self._ui.refine.hide()
        self._ui.castellationCancel.show()
        snappyHexMesh.snappyStarted.emit()

        app.consoleView.clear()

        if await self._run():
            self.stepCompleted.emit()

            await AsyncMessageBox().information(self._widget, self.tr('Complete'),
                                                self.tr('Castellation refinement is completed.'))

        snappyHexMesh.snappyStopped.emit()
        self._enableEdit()
        self._ui.castellationCancel.hide()

        self.updateWorkingStatus()

    def _reset(self):
        self._showPreviousMesh()
        self.clearResult()
        self._updateControlButtons()
        self.stepReset.emit()

    def _surfaceRefinementDialogAccepted(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            self._addSurfaceRefinementItem(self._dialog.groupId(), element.getValue('groupName'),
                                           element.getValue('surfaceRefinement/minimumLevel'),
                                           element.getValue('surfaceRefinement/maximumLevel'))
        else:
            self._ui.surfaceRefinement.item(self._dialog.groupId()).update([
                element.getValue('groupName'),
                element.getValue('surfaceRefinement/minimumLevel'), element.getValue('surfaceRefinement/maximumLevel')])

    def _addSurfaceRefinementItem(self, groupId, name, minLevel, maxLevel):
        item = ListItemWithButtons(groupId, [name, minLevel, maxLevel])
        item.editClicked.connect(lambda: self._openSurfaceRefinementDialog(groupId))
        item.removeClicked.connect(lambda: self._removeSurfaceRefinement(groupId))
        self._ui.surfaceRefinement.addItem(item)

    def _removeSurfaceRefinement(self, groupId):
        self._db.removeElement('castellation/refinementSurfaces', groupId)
        self._db.updateElements('geometry', 'castellationGroup', None,
                                       lambda i, e: e['castellationGroup'] == groupId)

        self._ui.surfaceRefinement.removeItem(groupId)

    def _volumeRefinementDialogAccepted(self):
        element = self._dialog.dbElement()
        if self._dialog.isCreationMode():
            self._addVolumeRefinementItem(self._dialog.groupId(), element.getValue('groupName'),
                                          element.getValue('volumeRefinementLevel'))
        else:
            self._ui.volumeRefinement.item(self._dialog.groupId()).update(
                [element.getValue('groupName'), element.getValue('volumeRefinementLevel')])

    def _addVolumeRefinementItem(self, groupId, name, level):
        item = ListItemWithButtons(groupId, [name, level])
        item.editClicked.connect(lambda: self._openVolumeRefinementDialog(groupId))
        item.removeClicked.connect(lambda: self._removeVolumeRefinement(groupId))
        self._ui.volumeRefinement.addItem(item)

    def _removeVolumeRefinement(self, groupId):
        self._db.removeElement('castellation/refinementVolumes', groupId)
        self._db.updateElements('geometry', 'castellationGroup', None,
                                       lambda i, e: e['castellationGroup'] == groupId)

        self._ui.volumeRefinement.removeItem(groupId)

    def _updateControlButtons(self):
        if self.isNextStepAvailable():
            self._ui.refine.hide()
            self._ui.castellationReset.show()
        else:
            self._ui.refine.show()
            self._ui.refine.setEnabled(True)
            self._ui.castellationReset.hide()

    def _enableStep(self):
        self._enableEdit()
        self._ui.castellationButtons.setEnabled(True)

    def _disableStep(self):
        self._disableEdit()
        self._ui.castellationButtons.setEnabled(False)

    def _enableEdit(self):
        self._ui.loadCastellationDefaults.setEnabled(True)
        self._ui.castellationConfiguration.setEnabled(True)
        self._ui.castellationAdvanced.setEnabled(True)
        self._ui.surfaceRefinementAdd.setEnabled(True)
        self._ui.surfaceRefinement.enableEdit()
        self._ui.volumeRefinementAdd.setEnabled(True)
        self._ui.volumeRefinement.enableEdit()

    def _disableEdit(self):
        self._ui.loadCastellationDefaults.setEnabled(False)
        self._ui.castellationConfiguration.setEnabled(False)
        self._ui.castellationAdvanced.setEnabled(False)
        self._ui.surfaceRefinementAdd.setEnabled(False)
        self._ui.surfaceRefinement.disableEdit()
        self._ui.volumeRefinementAdd.setEnabled(False)
        self._ui.volumeRefinement.disableEdit()

    async def _run(self):
        self._disableEdit()

        result = False
        try:
            await snappyHexMesh.castellation()
            result = True
        except ProcessError as e:
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Castellation refinement Failed [') + str(e.returncode) + ']')
        except CanceledException:
            await AsyncMessageBox().information(self._widget, self.tr('Canceled'),
                                                self.tr('Castellation refinement has been canceled.'))
        except Exception as e:
            await AsyncMessageBox().information(self._widget, self.tr('Error'),
                                                self.tr('Castellation refinement Failed:') + str(e))

        if not result:
            self.clearResult()

        return result
