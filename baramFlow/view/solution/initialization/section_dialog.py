#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from enum import Enum, IntEnum, auto
from typing import Optional

import qasync
from PySide6.QtWidgets import QSizePolicy, QRadioButton, QGridLayout, QLabel, QCheckBox, QLineEdit, QGroupBox

from baramFlow.case_manager import CaseManager
from baramFlow.coredb.material_db import MaterialDB
from widgets.async_message_box import AsyncMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.initialization_db import InitializationDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from baramFlow.view.widgets.species_widget import SpeciesWidget
from baramFlow.view.widgets.volume_fraction_widget import VolumeFractionWidget
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


class UserDefinedScalarList(QGroupBox):
    class Column(IntEnum):
        CHECK_BOX = 0
        LABEL = auto()
        VALUE = auto()

    def __init__(self, scalars):
        super().__init__(self.tr('User-defined Scalars'))

        self._layout = QGridLayout(self)
        self._scalars = {}

        for scalarID, fieldName in scalars:
            checkBox = QCheckBox()
            edit = QLineEdit()
            edit.setEnabled(False)
            checkBox.toggled.connect(edit.setEnabled)

            row = self._layout.rowCount()
            self._layout.addWidget(checkBox, row, self.Column.CHECK_BOX)
            self._layout.addWidget(QLabel(fieldName), row, self.Column.LABEL)
            self._layout.addWidget(edit, row, self.Column.VALUE)
            self._scalars[scalarID] = row

    def ids(self):
        return self._scalars.keys()

    def value(self, scalarID):
        return (self._layout.itemAtPosition(self._scalars[scalarID], self.Column.VALUE).widget().text()
                if self._layout.itemAtPosition(self._scalars[scalarID], self.Column.CHECK_BOX).widget().isChecked()
                else None)

    def fieldName(self, scalarID):
        self._layout.itemAtPosition(self._scalars[scalarID], self.Column.LABEL).widget().text()

    def setData(self, scalarID, enabled, value):
        self._layout.itemAtPosition(self._scalars[scalarID], self.Column.CHECK_BOX).widget().setChecked(enabled)
        self._layout.itemAtPosition(self._scalars[scalarID], self.Column.VALUE).widget().setText(value)


class SectionDialog(ResizableDialog):
    def __init__(self, parent=None, rname='', name=None):
        super().__init__(parent)
        self._ui = Ui_sectionDialog()
        self._ui.setupUi(self)

        self._rname = rname
        self._sectionName = name
        self._sectionType: Optional[SectionType] = None
        self._cellZoneRadio = {}
        self._scalars = {}

        self._pageType = None
        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        if CaseManager().isActive():
            self._ui.editForm.setEnabled(False)
            self._ui.ok.setEnabled(False)

        self._connectSignalsToSlots()

        sectionPath = InitializationDB.getSectionXPath(rname, name)

        mid = RegionDB.getMaterial(self._rname)
        if MaterialDB.isFluid(mid):
            volumeFractionWidget = VolumeFractionWidget(self._rname)
            if volumeFractionWidget.on():
                self._volumeFractionWidget = volumeFractionWidget
                self._volumeFractionWidget.setCheckable(True)
                self._volumeFractionWidget.setChecked(False)
                self._ui.initialValuesLayout.addWidget(self._volumeFractionWidget)

            db = coredb.CoreDB()
            if scalars := db.getUserDefinedScalarsInRegion(self._rname):
                self._scalarsWidget = UserDefinedScalarList(scalars)
                self._ui.initialValuesLayout.addWidget(self._scalarsWidget)

            speciesWidget = SpeciesWidget(mid, True)
            if speciesWidget.on():
                self._speciesWidget = speciesWidget
                self._ui.initialValuesLayout.addWidget(self._speciesWidget)
        else:
            self._ui.velocityGroup.hide()
            self._ui.properties.layout().setRowVisible(self._ui.pressure, False)

        if name is not None:  # Open Edit page with the parameters from coreDB
            self._pageType = PageType.EDIT
            self._load(sectionPath)
            self._showEditPage()
        else:
            self._pageType = PageType.CREATE
            self._showCreatePage()

    def _connectSignalsToSlots(self):
        self._ui.nextButton.clicked.connect(self.nextButtonClicked)
        self._ui.cancelButton.clicked.connect(self.cancelButtonClicked)
        self._ui.ok.clicked.connect(self._accept)

    @property
    def sectionName(self):
        return self._sectionName

    @qasync.asyncSlot()
    async def nextButtonClicked(self):
        if not re.match(r'^\w+$', self._ui.sectionNameInput.text()):
            await AsyncMessageBox().warning(self, self.tr('Warning'),
                                            self.tr('Section name can only contain letters, numbers, and underscores'))
            return

        db = coredb.CoreDB()
        self._sectionName = self._ui.sectionNameInput.text()

        # Check if the name already exists
        sectionPath = InitializationDB.getSectionXPath(self._rname, self._sectionName)
        try:
            _ = db.getValue(sectionPath + '/type')
        except LookupError:  # Ok, No Duplication
            pass
        else:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Section with same name already exists'))
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
            cellZones = db.getCellZones(self._rname)
            if len(cellZones) == 1:  # 'All' only
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('No Cell Zone found in the region'))
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

        self._showEditPage()

    @qasync.asyncSlot()
    async def cancelButtonClicked(self):
        self.close()

    @qasync.asyncSlot()
    async def _accept(self) -> None:
        #
        # Validation check for parameters
        #
        if self._volumeFractionWidget and self._volumeFractionWidget.isChecked():
            valid, msg = self._volumeFractionWidget.validate()
            if not valid:
                await AsyncMessageBox().warning(self, self.tr('Warning'), msg)
                return
        # ToDo: Add validation for other parameters

        writer = CoreDBWriter()

        if self._pageType == PageType.CREATE:
            speciesXML = ''
            if self._speciesWidget:
                xml = ''
                for specie in self._speciesWidget.species():
                    xml += f'<specie><mid>{specie}</mid><value>0</value></specie>'

                speciesXML = f'''
                    <mixture disabled="true" xmlns="http://www.baramcfd.org/baram">
                        <mid>{self._speciesWidget.mid()}</mid>{xml}
                    </mixture>'''

                # Create an element with given name and default values
            writer.addElement(f'/regions/region[name="{self._rname}"]/initialization/advanced/sections',
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
                                    <volumeFractions disabled="true"/>
                                    <userDefinedScalars/>
                                    <species>{speciesXML}</species>
                                    <overrideBoundaryValue>false</overrideBoundaryValue>
                                </section>
                            ''')

        sectionPath = InitializationDB.getSectionXPath(self._rname, self._sectionName)

        if self._sectionType == SectionType.HEX:
            try:  # ensure input text as decimal number
                minX = float(self._ui.minPointX.text())
                minY = float(self._ui.minPointY.text())
                minZ = float(self._ui.minPointZ.text())
                maxX = float(self._ui.maxPointX.text())
                maxY = float(self._ui.maxPointY.text())
                maxZ = float(self._ui.maxPointZ.text())
            except ValueError:
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            if maxX <= minX or maxY <= minY or maxZ <= minZ:
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
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
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            if r == 0 or (p1x == p2x and p1y == p2y and p1z == p2z):
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
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
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
                return

            if r == 0:
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid Geometry parameter'))
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
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid velocity parameter'))
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
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid pressure parameter'))
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
                await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Invalid temperature parameter'))
                return

            writer.setAttribute(sectionPath + '/temperature', 'disabled', 'false')
            writer.append(sectionPath + '/temperature', self._ui.temperature.text(), self.tr("Temperature"))
            parameterConfigured = True
        else:
            writer.setAttribute(sectionPath + '/temperature', 'disabled', 'true')

        if self._volumeFractionWidget:
            if self._volumeFractionWidget.isChecked():
                writer.setAttribute(sectionPath + '/volumeFractions', 'disabled', 'false')
                if not await self._volumeFractionWidget.appendToWriter(writer, sectionPath + '/volumeFractions'):
                    return
                parameterConfigured = True
            else:
                writer.setAttribute(sectionPath + '/volumeFractions', 'disabled', 'true')

        if self._scalarsWidget:
            if self._pageType == PageType.CREATE:
                for scalarID in self._scalarsWidget.ids():
                    value = self._scalarsWidget.value(scalarID)
                    writer.addElement(f'{sectionPath}/userDefinedScalars',
                                      InitializationDB.buildSectionUserDefinedScalar(scalarID, value),
                                      self._scalarsWidget.fieldName(scalarID))
                    parameterConfigured = parameterConfigured or value is not None
            else:
                for scalarID in self._scalarsWidget.ids():
                    xpath = f'{sectionPath}/userDefinedScalars/scalar[scalarID="{scalarID}"]/value'
                    if value := self._scalarsWidget.value(scalarID):
                        writer.setAttribute(xpath, 'disabled', 'false')
                        writer.append(xpath, value, self._scalarsWidget.fieldName(scalarID))
                        parameterConfigured = True
                    else:
                        writer.setAttribute(xpath, 'disabled', 'true')

        if self._speciesWidget:
            if not await self._speciesWidget.appendToWriter(writer, f'{sectionPath}/species'):
                return
            parameterConfigured = parameterConfigured or self._speciesWidget.isChecked()

        if not parameterConfigured:
            await AsyncMessageBox().warning(self, self.tr('Warning'),
                                            self.tr('At least one parameter should be configured'))
            return

        errorCount = writer.write()
        if errorCount > 0:
            await AsyncMessageBox().critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.accept()

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

    def _load(self, sectionPath):
        self._pageType = PageType.EDIT

        self._ui.sectionName.setText(self._sectionName)

        db = coredb.CoreDB()

        typeString = db.getValue(sectionPath+'/type')
        if typeString == 'hex':
            self._sectionType = SectionType.HEX
            self._ui.minPointX.setText(db.getValue(sectionPath+'/point1/x'))
            self._ui.minPointY.setText(db.getValue(sectionPath+'/point1/y'))
            self._ui.minPointZ.setText(db.getValue(sectionPath+'/point1/z'))
            self._ui.maxPointX.setText(db.getValue(sectionPath+'/point2/x'))
            self._ui.maxPointY.setText(db.getValue(sectionPath+'/point2/y'))
            self._ui.maxPointZ.setText(db.getValue(sectionPath+'/point2/z'))
        elif typeString == 'cylinder':
            self._sectionType = SectionType.CYLINDER
            self._ui.p1x.setText(db.getValue(sectionPath+'/point1/x'))
            self._ui.p1y.setText(db.getValue(sectionPath+'/point1/y'))
            self._ui.p1z.setText(db.getValue(sectionPath+'/point1/z'))
            self._ui.p2x.setText(db.getValue(sectionPath+'/point2/x'))
            self._ui.p2y.setText(db.getValue(sectionPath+'/point2/y'))
            self._ui.p2z.setText(db.getValue(sectionPath+'/point2/z'))
            self._ui.cylinderRadius.setText(db.getValue(sectionPath+'/radius'))
        elif typeString == 'sphere':
            self._sectionType = SectionType.SPHERE
            self._ui.cx.setText(db.getValue(sectionPath+'/point1/x'))
            self._ui.cy.setText(db.getValue(sectionPath+'/point1/y'))
            self._ui.cz.setText(db.getValue(sectionPath+'/point1/z'))
            self._ui.sphereRadius.setText(db.getValue(sectionPath+'/radius'))
        elif typeString == 'cellZone':
            self._sectionType = SectionType.CELL_ZONE
            savedId = db.getValue(sectionPath+'/cellZone')
            cellZones = db.getCellZones(self._rname)
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

        self._ui.ux.setText(db.getValue(sectionPath+'/velocity/x'))
        self._ui.uy.setText(db.getValue(sectionPath+'/velocity/y'))
        self._ui.uz.setText(db.getValue(sectionPath+'/velocity/z'))
        if db.getAttribute(sectionPath+'/velocity', 'disabled') == 'false':
            self._ui.velocityGroup.setChecked(True)

        self._ui.pressure.setText(db.getValue(sectionPath+'/pressure'))
        if db.getAttribute(sectionPath+'/pressure', 'disabled') == 'false':
            self._ui.pressureCheckBox.setChecked(True)

        self._ui.temperature.setText(db.getValue(sectionPath+'/temperature'))
        if db.getAttribute(sectionPath+'/temperature', 'disabled') == 'false':
            self._ui.temperatureCheckBox.setChecked(True)

        if self._volumeFractionWidget:
            self._volumeFractionWidget.load(sectionPath + '/volumeFractions')
            if db.getAttribute(sectionPath + '/volumeFractions', 'disabled') == 'false':
                self._volumeFractionWidget.setChecked(True)

        if self._scalarsWidget:
            for scalarID in self._scalarsWidget.ids():
                xpath = f'{sectionPath}/userDefinedScalars/scalar[scalarID="{scalarID}"]/value'
                self._scalarsWidget.setData(
                    scalarID,
                    db.getAttribute(xpath, 'disabled') == 'false',
                    db.getValue(xpath))

        if self._speciesWidget:
            self._speciesWidget.load(f'{sectionPath}/species')

        if db.getValue(sectionPath+'/overrideBoundaryValue') == 'true':
            self._ui.overrideBoundaryValue.setChecked(True)
        else:
            self._ui.overrideBoundaryValue.setChecked(False)
