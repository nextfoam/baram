#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QDialog

from widgets.async_message_box import AsyncMessageBox

from baramFlow.base.boundary.ABL_inlet import ABLFlowDirection, Vector, AtmosphericBoundaryLayer
from baramFlow.base.boundary.ABL_inlet import PasquillStability
from baramFlow.base.boundary.boundary_patch import ABLInletPatch
from baramFlow.coredb.libdb import xmlToBool
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, FlowDirectionSpecificationMethod
from baramFlow.coredb.region_db import RegionDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from .ABL_inlet_dialog_ui import Ui_ABLInletDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class ABLInletDialog(QDialog):
    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_ABLInletDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)
        self._generalXPath = BoundaryDB.ABL_INLET_CONDITIONS_XPATH

        self._scalarsWidget = None
        self._speciesWidget = None

        self._ui.flowDirectionSpecMethod.addItem(self.tr('Direct'),
                                                 FlowDirectionSpecificationMethod.DIRECT)
        self._ui.flowDirectionSpecMethod.addItem(self.tr('Surface-Normal'),
                                                 FlowDirectionSpecificationMethod.SURFACE_NORMAL)

        self._ui.stabilityClass.addItem(self.tr('A: Extremely Unstable'),   'A')
        self._ui.stabilityClass.addItem(self.tr('B: Moderately Unstable'),  'B')
        self._ui.stabilityClass.addItem(self.tr('C: Slightly Unstable'),    'C')
        self._ui.stabilityClass.addItem(self.tr('D: Neutral'),              'D')
        self._ui.stabilityClass.addItem(self.tr('E: Slightly Stable'),      'E')
        self._ui.stabilityClass.addItem(self.tr('F: Moderately Stable'),    'F')

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()
        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            specMethod = FlowDirectionSpecificationMethod(self._ui.flowDirectionSpecMethod.currentData())
            if specMethod == FlowDirectionSpecificationMethod.DIRECT:
                flowDirection = ABLFlowDirection(
                    specificationMethod=specMethod,
                    value = Vector(
                        x=self._ui.flowDirectionXComponent.pFloat(self.tr('Flow Direction X-Component')),
                        y=self._ui.flowDirectionYComponent.pFloat(self.tr('Flow Direction Y-Component')),
                        z=self._ui.flowDirectionZComponent.pFloat(self.tr('Flow Direction Z-Component'))))
            else:
                flowDirection = ABLFlowDirection(specificationMethod=specMethod)

            if self._ui.pasquillStability.isChecked():
                pasquillStability = PasquillStability(
                    disabled=False,
                    stabilityClass=self._ui.stabilityClass.currentData(),
                    latitude=self._ui.latitude.pFloat(self.tr('Latitude')),
                    surfaceHeatFlux=self._ui.surfaceHeatFlux.pFloat(self.tr('Surface Heat Flux')),
                    referenceDensity=self._ui.referenceDensity.pFloat(self.tr('Reference Density')),
                    referenceSpecificHeat=self._ui.referenceSpecificHeat.pFloat(self.tr('Reference Specific Heat')),
                    referenceTemperature=self._ui.referenceTemperature.pFloat(self.tr('Reference Temperature')))
            else:
                pasquillStability = PasquillStability(disabled=True)

            data = ABLInletPatch(
                abl= AtmosphericBoundaryLayer(
                    flowDirection=flowDirection,
                    groundNormalDirection=Vector(
                        x=self._ui.groundNormalDirectionXComponent.pFloat(
                            self.tr('Ground-Normal Direction X-Component')),
                        y=self._ui.groundNormalDirectionYComponent.pFloat(
                            self.tr('Ground-Normal Direction Y-Component')),
                        z=self._ui.groundNormalDirectionZComponent.pFloat(
                            self.tr('Ground-Normal Direction Z-Component'))),
                    referenceFlowSpeed=self._ui.referenceFlowSpeed.pFloat(self.tr('Reference Flow Speed')),
                    referenceHeight= self._ui.referenceHeight.pFloat(self.tr('Reference Height')),
                    surfaceRoughnessLength= self._ui.surfaceRoughnessLength.pFloat(self.tr('Surface Roughness Length')),
                    minimumZCoordinate=self._ui.minimumZCoordinate.pFloat(self.tr('Minimum z-coordinate')),
                    pasquillStability=pasquillStability),
                userDefinedScalars=self._scalarsWidget.data(),
                species=self._speciesWidget.data())

            BoundaryService.updateBoundaryCondition(self._bcid, data)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        db = coredb.CoreDB()
        self._ui.flowDirectionSpecMethod.setCurrentIndex(
            self._ui.flowDirectionSpecMethod.findData(
                FlowDirectionSpecificationMethod(db.getValue(self._generalXPath + '/flowDirection/specMethod'))))
        self._ui.flowDirectionXComponent.setText(db.getValue(self._generalXPath + '/flowDirection/value/x'))
        self._ui.flowDirectionYComponent.setText(db.getValue(self._generalXPath + '/flowDirection/value/y'))
        self._ui.flowDirectionZComponent.setText(db.getValue(self._generalXPath + '/flowDirection/value/z'))

        self._ui.groundNormalDirectionXComponent.setText(db.getValue(self._generalXPath + '/groundNormalDirection/x'))
        self._ui.groundNormalDirectionYComponent.setText(db.getValue(self._generalXPath + '/groundNormalDirection/y'))
        self._ui.groundNormalDirectionZComponent.setText(db.getValue(self._generalXPath + '/groundNormalDirection/z'))

        self._ui.referenceFlowSpeed.setText(db.getValue(self._generalXPath + '/referenceFlowSpeed'))
        self._ui.referenceHeight.setText(db.getValue(self._generalXPath + '/referenceHeight'))
        self._ui.surfaceRoughnessLength.setText(db.getValue(self._generalXPath + '/surfaceRoughnessLength'))
        self._ui.minimumZCoordinate.setText(db.getValue(self._generalXPath + '/minimumZCoordinate'))

        self._ui.pasquillStability.setChecked(
            not xmlToBool(db.getAttribute(self._generalXPath + '/pasquillStability', 'disabled')))
        self._ui.stabilityClass.setCurrentIndex(
            self._ui.stabilityClass.findData(db.getValue(self._generalXPath + '/pasquillStability/stabilityClass')))
        self._ui.latitude.setText(db.getValue(self._generalXPath + '/pasquillStability/latitude'))
        self._ui.surfaceHeatFlux.setText(db.getValue(self._generalXPath + '/pasquillStability/surfaceHeatFlux'))
        self._ui.referenceDensity.setText(db.getValue(self._generalXPath + '/pasquillStability/referenceDensity'))
        self._ui.referenceSpecificHeat.setText(db.getValue(
            self._generalXPath + '/pasquillStability/referenceSpecificHeat'))
        self._ui.referenceTemperature.setText(db.getValue(
            self._generalXPath + '/pasquillStability/referenceTemperature'))

        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.flowDirectionSpecMethod.currentIndexChanged.connect(self._onFlowDirectionSpecMethodChanged)
        self._ui.ok.clicked.connect(self._accept)

    def _onFlowDirectionSpecMethodChanged(self):
        self._ui.flowDirection.setEnabled(
            self._ui.flowDirectionSpecMethod.currentData() == FlowDirectionSpecificationMethod.DIRECT)
