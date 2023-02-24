#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from typing import Optional

import re

import qasync

from PySide6.QtWidgets import QSizePolicy, QRadioButton, QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter

from view.widgets.resizable_dialog import ResizableDialog
from view.widgets.volume_fraction_widget import VolumeFractionWidget

from .section_dialog_ui import Ui_sectionDialog


class SectionType(Enum):
    # value comes from "index" in sectionStack
    HEX = 0
    CYLINDER = 1
    SPHERE = 2
    CELL_ZONE = 3


class PageType(Enum):
    # value comes from "index" in stackedWidget
    CREATE = 0
    EDIT = 1


class SectionDialog(ResizableDialog):
    def __init__(self, parent=None, rname='', name=None):
        super().__init__(parent)
        self._ui = Ui_sectionDialog()
        self._ui.setupUi(self)

        self._rname = rname
        self._sectionName = name
        self._sectionType: Optional[SectionType] = None
        self._cellZoneRadio = {}

        self._db = coredb.CoreDB()

        self._connectSignalsToSlots()

        if name is not None:  # Open Edit page with the parameters from coreDB
            self._pageType = PageType.EDIT
            sectionPath = f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{name}"]'

            self._ui.sectionName.setText(name)

            typeString = self._db.getValue(sectionPath+'/type')
            if typeString == 'hex':
                self._sectionType = SectionType.HEX
                self._ui.minPointX.setText(self._db.getValue(sectionPath+'/point1/x'))
                self._ui.minPointY.setText(self._db.getValue(sectionPath+'/point1/y'))
                self._ui.minPointZ.setText(self._db.getValue(sectionPath+'/point1/z'))
                self._ui.maxPointX.setText(self._db.getValue(sectionPath+'/point2/x'))
                self._ui.maxPointY.setText(self._db.getValue(sectionPath+'/point2/y'))
                self._ui.maxPointZ.setText(self._db.getValue(sectionPath+'/point2/z'))
            elif typeString == 'cylinder':
                self._sectionType = SectionType.CYLINDER
                self._ui.p1x.setText(self._db.getValue(sectionPath+'/point1/x'))
                self._ui.p1y.setText(self._db.getValue(sectionPath+'/point1/y'))
                self._ui.p1z.setText(self._db.getValue(sectionPath+'/point1/z'))
                self._ui.p2x.setText(self._db.getValue(sectionPath+'/point2/x'))
                self._ui.p2y.setText(self._db.getValue(sectionPath+'/point2/y'))
                self._ui.p2z.setText(self._db.getValue(sectionPath+'/point2/z'))
                self._ui.cylinderRadius.setText(self._db.getValue(sectionPath+'/radius'))
            elif typeString == 'sphere':
                self._sectionType = SectionType.SPHERE
                self._ui.cx.setText(self._db.getValue(sectionPath+'/point1/x'))
                self._ui.cy.setText(self._db.getValue(sectionPath+'/point1/y'))
                self._ui.cz.setText(self._db.getValue(sectionPath+'/point1/z'))
                self._ui.sphereRadius.setText(self._db.getValue(sectionPath+'/radius'))
            elif typeString == 'cellZone':
                self._sectionType = SectionType.CELL_ZONE
                savedId = self._db.getValue(sectionPath+'/cellZone')
                cellZones = self._db.getCellZones(self._rname)
                for czid, czname in cellZones:
                    if czname == 'All':
                        continue
                    radio = QRadioButton(czname)
                    if str(czid) == savedId:
                        radio.setChecked(True)
                    self._ui.cellZoneGroupLayout.addWidget(radio)
                    self._cellZoneRadio[str(czid)] = radio
            else:
                raise AssertionError

            self._ui.ux.setText(self._db.getValue(sectionPath+'/velocity/x'))
            self._ui.uy.setText(self._db.getValue(sectionPath+'/velocity/y'))
            self._ui.uz.setText(self._db.getValue(sectionPath+'/velocity/z'))
            if self._db.getAttribute(sectionPath+'/velocity', 'disabled') == 'false':
                self._ui.velocityGroup.setChecked(True)

            self._ui.pressure.setText(self._db.getValue(sectionPath+'/pressure'))
            if self._db.getAttribute(sectionPath+'/pressure', 'disabled') == 'false':
                self._ui.pressureCheckBox.setChecked(True)

            self._ui.temperature.setText(self._db.getValue(sectionPath+'/temperature'))
            if self._db.getAttribute(sectionPath+'/temperature', 'disabled') == 'false':
                self._ui.temperatureCheckBox.setChecked(True)

            self._volumeFractionWidget = VolumeFractionWidget(self._rname, sectionPath)
            if self._volumeFractionWidget.on():
                self._volumeFractionWidget.load()
                self._volumeFractionWidget.setCheckable(True)
                if self._db.getAttribute(sectionPath+'/volumeFractions', 'disabled') == 'false':
                    self._volumeFractionWidget.setChecked(True)
                self._ui.initialValuesLayout.addWidget(self._volumeFractionWidget)

            if self._db.getValue(sectionPath+'/overrideBoundaryValue') == 'true':
                self._ui.overrideBoundaryValue.setChecked(True)
            else:
                self._ui.overrideBoundaryValue.setChecked(False)

            self._showEditPage()
        else:
            self._pageType = PageType.CREATE
            self._showCreatePage()

    def _connectSignalsToSlots(self):
        self._ui.nextButton.clicked.connect(self.nextButtonClicked)
        self._ui.cancelButton.clicked.connect(self.cancelButtonClicked)

    @property
    def sectionName(self):
        return self._sectionName

    @qasync.asyncSlot()
    async def nextButtonClicked(self):
        if not re.match(r'^\w+$', self._ui.sectionNameInput.text()):
            QMessageBox.warning(self, self.tr('Warning'), self.tr('Section name can only contain letters, numbers, and underscores'))
            return

        self._sectionName = self._ui.sectionNameInput.text()

        # Check if the name already exists
        sectionPath = f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{self._sectionName}"]'
        try:
            _ = self._db.getValue(sectionPath + '/type')
        except LookupError:  # Ok, No Duplication
            pass
        else:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('Section with same name already exists'))
            return

        self._ui.sectionName.setText(self._sectionName)

        if self._ui.hexType.isChecked():
            self._sectionType = SectionType.HEX
        elif self._ui.cylinderType.isChecked():
            self._sectionType = SectionType.CYLINDER
        elif self._ui.sphereType.isChecked():
            self._sectionType = SectionType.SPHERE
        elif self._ui.cellZoneType.isChecked():
            self._sectionType = SectionType.CELL_ZONE
            cellZones = self._db.getCellZones(self._rname)
            if len(cellZones) == 1:  # 'All' only
                QMessageBox.warning(self, self.tr('Warning'), self.tr('No Cell Zone found in the region'))
                return

            for czid, czname in cellZones:
                if czname == 'All':
                    continue
                radio = QRadioButton(czname)
                self._ui.cellZoneGroupLayout.addWidget(radio)
                self._cellZoneRadio[str(czid)] = radio

            # set default Cell Zone
            self._ui.cellZoneGroupLayout.itemAt(0).widget().setChecked(True)
        else:
            raise AssertionError

        self._volumeFractionWidget = VolumeFractionWidget(self._rname, sectionPath)
        if self._volumeFractionWidget.on():
            self._volumeFractionWidget.setCheckable(True)
            self._volumeFractionWidget.setChecked(False)
            self._ui.initialValuesLayout.addWidget(self._volumeFractionWidget)

        self._showEditPage()

    @qasync.asyncSlot()
    async def cancelButtonClicked(self):
        self.close()

    def accept(self) -> None:
        writer = CoreDBWriter()

        if self._pageType == PageType.CREATE:
            # Create an element with given name and default values
            writer.addElement(f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections',
                              f'''
                                <section xmlns="http://www.baramcfd.org/baram">
                                    <name>{self._sectionName}</name>
                                    <type>hex</type>
                                    <point1><x>0</x><y>0</y><z>0</z></point1>
                                    <point2><x>0</x><y>0</y><z>0</z></point2>
                                    <radius>0</radius>
                                    <cellZone>1</cellZone>
                                    <velocity disabled="true"><x>0</x><y>0</y><z>0</z></velocity>
                                    <pressure disabled="true">0</pressure>
                                    <temperature disabled="true">300</temperature>
                                    <volumeFractions disabled="true"></volumeFractions>
                                    <overrideBoundaryValue>false</overrideBoundaryValue>
                                </section>
                            ''', '')

        sectionPath = f'.//regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{self._sectionName}"]'

        if self._sectionType == SectionType.HEX:
            try:  # ensure input text as decimal number
                minX = float(self._ui.minPointX.text())
                minY = float(self._ui.minPointY.text())
                minZ = float(self._ui.minPointZ.text())
                maxX = float(self._ui.maxPointX.text())
                maxY = float(self._ui.maxPointY.text())
                maxZ = float(self._ui.maxPointZ.text())
            except ValueError:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            if maxX <= minX or maxY <= minY or maxZ <= minZ:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            writer.append(sectionPath + '/type', 'hex', self.tr("Section Type"))
            writer.append(sectionPath + '/point1/x', self._ui.minPointX.text(), self.tr("Min X"))
            writer.append(sectionPath + '/point1/y', self._ui.minPointY.text(), self.tr("Min Y"))
            writer.append(sectionPath + '/point1/z', self._ui.minPointZ.text(), self.tr("Min Z"))
            writer.append(sectionPath + '/point2/x', self._ui.maxPointX.text(), self.tr("Max X"))
            writer.append(sectionPath + '/point2/y', self._ui.maxPointY.text(), self.tr("Max Y"))
            writer.append(sectionPath + '/point2/z', self._ui.maxPointZ.text(), self.tr("Max Z"))

        elif self._sectionType == SectionType.CYLINDER:
            try:  # ensure input text as decimal number
                p1x = float(self._ui.p1x.text())
                p1y = float(self._ui.p1y.text())
                p1z = float(self._ui.p1z.text())
                p2x = float(self._ui.p2x.text())
                p2y = float(self._ui.p2y.text())
                p2z = float(self._ui.p2z.text())
                r   = float(self._ui.cylinderRadius.text())
            except ValueError:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            if r == 0 or (p1x == p2x and p1y == p2y and p1z == p2z):
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            writer.append(sectionPath + '/type', 'cylinder', self.tr("Section Type"))
            writer.append(sectionPath + '/point1/x', self._ui.p1x.text(), self.tr("Axis Point1 X"))
            writer.append(sectionPath + '/point1/y', self._ui.p1y.text(), self.tr("Axis Point1 Y"))
            writer.append(sectionPath + '/point1/z', self._ui.p1z.text(), self.tr("Axis Point1 Z"))
            writer.append(sectionPath + '/point2/x', self._ui.p2x.text(), self.tr("Axis Point2 X"))
            writer.append(sectionPath + '/point2/y', self._ui.p2y.text(), self.tr("Axis Point2 Y"))
            writer.append(sectionPath + '/point2/z', self._ui.p2z.text(), self.tr("Axis Point2 Z"))
            writer.append(sectionPath + '/radius',   self._ui.cylinderRadius.text(), self.tr("Cylinder Radius"))

        elif self._sectionType == SectionType.SPHERE:
            try:  # ensure input text as decimal number
                cx = float(self._ui.cx.text())
                cy = float(self._ui.cy.text())
                cz = float(self._ui.cz.text())
                r = float(self._ui.sphereRadius.text())
            except ValueError:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            if r == 0:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            writer.append(sectionPath + '/type', 'sphere', self.tr("Section Type"))
            writer.append(sectionPath + '/point1/x', self._ui.cx.text(), self.tr("Center X"))
            writer.append(sectionPath + '/point1/y', self._ui.cy.text(), self.tr("Center Y"))
            writer.append(sectionPath + '/point1/z', self._ui.cz.text(), self.tr("Center Z"))
            writer.append(sectionPath + '/radius',   self._ui.sphereRadius.text(), self.tr("Sphere Radius"))

        elif self._sectionType == SectionType.CELL_ZONE:
            writer.append(sectionPath + '/type', 'cellZone', self.tr("Section Type"))
            for czid, radio in self._cellZoneRadio.items():
                if radio.isChecked():
                    writer.append(sectionPath + '/cellZone', czid, self.tr("Cell Zone"))
                    break

        if self._ui.overrideBoundaryValue.isChecked():
            writer.append(sectionPath + '/overrideBoundaryValue', 'true', self.tr("Override Boundary Value"))
        else:
            writer.append(sectionPath + '/overrideBoundaryValue', 'false', self.tr("Override Boundary Value"))

        # Parameter processing

        parameterConfigured = False

        if self._ui.velocityGroup.isChecked():
            try:  # ensure input text as decimal number
                ux = float(self._ui.ux.text())
                uy = float(self._ui.uy.text())
                uz = float(self._ui.uz.text())
            except ValueError:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid velocity parameter'))
                return

            writer.setAttribute(sectionPath + '/velocity', 'disabled', 'false')
            writer.append(sectionPath + '/velocity/x', self._ui.ux.text(), self.tr("X-Velocity"))
            writer.append(sectionPath + '/velocity/y', self._ui.uy.text(), self.tr("Y-Velocity"))
            writer.append(sectionPath + '/velocity/z', self._ui.uz.text(), self.tr("Z-Velocity"))
            parameterConfigured = True
        else:
            writer.setAttribute(sectionPath + '/velocity', 'disabled', 'true')

        if self._ui.pressureCheckBox.isChecked():
            try:  # ensure input text as decimal number
                p = float(self._ui.pressure.text())
            except ValueError:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid pressure parameter'))
                return

            writer.setAttribute(sectionPath + '/pressure', 'disabled', 'false')
            writer.append(sectionPath + '/pressure', self._ui.pressure.text(), self.tr("Pressure"))
            parameterConfigured = True
        else:
            writer.setAttribute(sectionPath + '/pressure', 'disabled', 'true')

        if self._ui.temperatureCheckBox.isChecked():
            try:  # ensure input text as decimal number
                t = float(self._ui.temperature.text())
            except ValueError:
                QMessageBox.warning(self, self.tr('Warning'), self.tr('Invalid temperature parameter'))
                return

            writer.setAttribute(sectionPath + '/temperature', 'disabled', 'false')
            writer.append(sectionPath + '/temperature', self._ui.temperature.text(), self.tr("Temperature"))
            parameterConfigured = True
        else:
            writer.setAttribute(sectionPath + '/temperature', 'disabled', 'true')

        if self._volumeFractionWidget.on():
            if self._volumeFractionWidget.isChecked():
                writer.setAttribute(sectionPath + '/volumeFractions', 'disabled', 'false')
                if not self._volumeFractionWidget.appendToWriter(writer):
                    return
                parameterConfigured = True
            else:
                writer.setAttribute(sectionPath + '/volumeFractions', 'disabled', 'true')

        if not parameterConfigured:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('At least one parameter should be configured'))
            return

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _showCreatePage(self):
        self._ui.editPage.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self._ui.creatPage.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._ui.stackedWidget.adjustSize()
        self._ui.stackedWidget.setCurrentIndex(PageType.CREATE.value)  # set the index to Create page

    def _showEditPage(self):
        self._ui.page_0.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self._ui.page_1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self._ui.page_2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self._ui.page_3.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        if self._sectionType == SectionType.HEX:
            self._ui.page_0.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        elif self._sectionType == SectionType.CYLINDER:
            self._ui.page_1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        elif self._sectionType == SectionType.SPHERE:
            self._ui.page_2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        elif self._sectionType == SectionType.CELL_ZONE:
            self._ui.page_3.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        else:
            raise AssertionError

        self._ui.sectionStack.adjustSize()

        self._ui.sectionStack.setCurrentIndex(self._sectionType.value)

        self._ui.creatPage.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self._ui.editPage.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._ui.stackedWidget.adjustSize()

        self._ui.stackedWidget.setCurrentIndex(PageType.EDIT.value)  # set the index to Edit page
