#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync

from baramFlow.base.base import DirectionSpecificationMethod, DirectionSpecificationMethodTexts, Vector
from baramFlow.base.boundary.boundary_patch import FreeStreamUpdate
from baramFlow.base.boundary.free_stream import FlowDirection, FreeStream
from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.services.boundary.boundary_service import BoundaryService
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox
from .free_stream_dialog_ui import Ui_FreeStreamDialog
from .conditional_widget_helper import ConditionalWidgetHelper


class FreeStreamDialog(ResizableDialog):
    RELATIVE_XPATH = '/freeStream'

    def __init__(self, parent, bcid):
        super().__init__(parent)
        self._ui = Ui_FreeStreamDialog()
        self._ui.setupUi(self)

        self._bcid = bcid
        self._xpath = BoundaryDB.getXPath(bcid)

        self._turbulenceWidget = None
        self._temperatureWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        layout = self._ui.dialogContents.layout()
        rname = BoundaryDB.getBoundaryRegion(bcid)
        self._turbulenceWidget = ConditionalWidgetHelper.turbulenceWidget(self._xpath, layout)
        self._temperatureWidget = ConditionalWidgetHelper.temperatureWidget(self._xpath, bcid, layout)
        self._scalarsWidget = ConditionalWidgetHelper.userDefinedScalarsWidget(rname, layout)
        self._speciesWidget = ConditionalWidgetHelper.speciesWidget(RegionDB.getMaterial(rname), layout)

        self._connectSignalsSlots()

        self._ui.specificationMethod.addItem(DirectionSpecificationMethodTexts[DirectionSpecificationMethod.DIRECT],
                                             DirectionSpecificationMethod.DIRECT)
        self._ui.specificationMethod.addItem(DirectionSpecificationMethodTexts[DirectionSpecificationMethod.AOA_AOS],
                                             DirectionSpecificationMethod.AOA_AOS)

        self._load()

    @qasync.asyncSlot()
    async def _accept(self):
        try:
            specificationMethod = self._ui.specificationMethod.currentData()
            flowDirection = FlowDirection(specificationMethod=specificationMethod)
            if specificationMethod == DirectionSpecificationMethod.DIRECT:
                flowDirection.flowDirection = Vector(x=PFloat(self._ui.flowDirectionX.text(), self.tr('Flow Direction')),
                                                     y=PFloat(self._ui.flowDirectionY.text(), self.tr('Flow Direction')),
                                                     z=PFloat(self._ui.flowDirectionZ.text(), self.tr('Flow Direction')))
            else:
                flowDirection.dragDirection = Vector(x=PFloat(self._ui.dragDirectionX.text(), self.tr('Drag Direction')),
                                                     y=PFloat(self._ui.dragDirectionY.text(), self.tr('Drag Direction')),
                                                     z=PFloat(self._ui.dragDirectionZ.text(), self.tr('Drag Direction')))
                flowDirection.liftDirection = Vector(x=PFloat(self._ui.liftDirectionX.text(), self.tr('Lift Direction')),
                                                     y=PFloat(self._ui.liftDirectionY.text(), self.tr('Lift Direction')),
                                                     z=PFloat(self._ui.liftDirectionZ.text(), self.tr('Lift Direction')))
                flowDirection.angleOfAttack = PFloat(self._ui.AoA.text(), self.tr('Angle of Attack'))
                flowDirection.angleOfSideslip = PFloat(self._ui.AoS.text(), self.tr('Angle of Sideslip'))

            writer = CoreDBWriter()

            if not self._turbulenceWidget.appendToWriter(writer):
                return

            if not self._temperatureWidget.appendToWriter(writer):
                return

            if not self._scalarsWidget.appendToWriter(writer, self._xpath + '/userDefinedScalars'):
                return

            if not await self._speciesWidget.appendToWriter(writer, self._xpath + '/species'):
                return

            data = FreeStreamUpdate(
                freeStream=FreeStream(
                    flowDirection=flowDirection,
                    speed=str(PFloat(self._ui.speed.text(), self.tr('Speed'))),
                    pressure=str(PFloat(self._ui.pressure.text(), self.tr('Pressure')))),
                turbulence=self._turbulenceWidget.data())

            BoundaryService.updateBoundaryCondition(self._bcid, data, writer)
        except ValueError as e:
            await AsyncMessageBox().information(self, self.tr('Input Error'), str(e))
            return

        self.accept()

    def _load(self):
        db = coredb.CoreDB()
        path = self._xpath + self.RELATIVE_XPATH

        self._ui.specificationMethod.setCurrentIndex(
            self._ui.specificationMethod.findData(
                DirectionSpecificationMethod(db.getValue(path + '/flowDirection/specificationMethod'))))

        self._ui.flowDirectionX.setText(db.getValue(path + '/flowDirection/flowDirection/x'))
        self._ui.flowDirectionY.setText(db.getValue(path + '/flowDirection/flowDirection/y'))
        self._ui.flowDirectionZ.setText(db.getValue(path + '/flowDirection/flowDirection/z'))
        self._ui.dragDirectionX.setText(db.getValue(path + '/flowDirection/dragDirection/x'))
        self._ui.dragDirectionY.setText(db.getValue(path + '/flowDirection/dragDirection/y'))
        self._ui.dragDirectionZ.setText(db.getValue(path + '/flowDirection/dragDirection/z'))
        self._ui.liftDirectionX.setText(db.getValue(path + '/flowDirection/liftDirection/x'))
        self._ui.liftDirectionY.setText(db.getValue(path + '/flowDirection/liftDirection/y'))
        self._ui.liftDirectionZ.setText(db.getValue(path + '/flowDirection/liftDirection/z'))
        self._ui.AoA.setText(db.getValue(path + '/flowDirection/angleOfAttack'))
        self._ui.AoS.setText(db.getValue(path + '/flowDirection/angleOfSideslip'))

        self._ui.speed.setText(db.getValue(path + '/speed'))
        self._ui.pressure.setText(db.getValue(path + '/pressure'))

        self._turbulenceWidget.load()
        self._temperatureWidget.load()
        self._temperatureWidget.freezeProfileToConstant()
        self._scalarsWidget.load(self._xpath + '/userDefinedScalars')
        self._speciesWidget.load(self._xpath + '/species')

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)
        self._ui.specificationMethod.currentIndexChanged.connect(self._specificationMethodChanged)

    def _specificationMethodChanged(self):
        method = self._ui.specificationMethod.currentData()
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.directFlowDirection.show()
            self._ui.anglesFlowDirection.hide()
        else:
            self._ui.directFlowDirection.hide()
            self._ui.anglesFlowDirection.show()
