#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional
from enum import Enum, auto
from math import sqrt

from PySide6.QtWidgets import QWidget, QMessageBox, QPushButton, QHBoxLayout
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from baramFlow.case_manager import CaseManager
from libbaram.math import calucateDirectionsByRotation
from resources import resource
from widgets.flat_push_button import FlatPushButton

from baramFlow.app import app
from baramFlow.base.material.material import UNIVERSAL_GAS_CONSTANT
from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from baramFlow.coredb.boundary_db import DirectionSpecificationMethod, TemperatureProfile, VelocitySpecification, VelocityProfile
from baramFlow.coredb.boundary_db import KEpsilonSpecification, KOmegaSpecification, SpalartAllmarasSpecification
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.project import Project
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceModelsDB, RANSModel
from baramFlow.mesh.vtk_loader import hexActor, cylinderActor, sphereActor
from baramFlow.view.widgets.species_widget import SpeciesWidget
from baramFlow.view.widgets.user_defined_scalars_widget import UserDefinedScalarsWidget
from baramFlow.view.widgets.volume_fraction_widget import VolumeFractionWidget
from .initialization_widget_ui import Ui_initializationWidget
from .section_dialog import SectionDialog


class OptionType(Enum):
    OFF = auto()
    SET_FIELDS = auto()
    MAP_FIELDS = auto()
    POTENTIAL_FLOW = auto()


class SectionRow(QWidget):
    doubleClicked = Signal()
    toggled = Signal(bool)
    eyeToggled = Signal(bool)

    def __init__(self, name, rname):
        super().__init__()

        self._name = name
        self._rname = rname
        self._key = f'{rname}:{name}'
        self._actor = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._eye = QPushButton(self)
        self._eyeOn: bool = False
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-off-outline.svg'))))
        self._eye.setFlat(True)
        self._eye.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._eye.clicked.connect(self.onClicked)

        layout.addWidget(self._eye)

        self._button = FlatPushButton(self)
        self._button.setStyleSheet('text-align: left;')
        self._button.setText(name)
        self._button.setCheckable(True)
        self._button.toggled.connect(self.toggled)
        self._button.doubleClicked.connect(self.doubleClicked)
        self._button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(self._button)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self._button.setText(value)

    @property
    def key(self):
        return f'{self._rname}:{self._name}'

    def actor(self):
        if self._actor is None:
            db = coredb.CoreDB()
            xpath = f'/regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{self._name}"]'

            typeString = db.getValue(xpath + '/type')
            if typeString == 'hex':
                self._actor = hexActor(db.getVector(xpath + '/point1'), db.getVector(xpath + '/point2'))
            elif typeString == 'cylinder':
                self._actor = cylinderActor(db.getVector(xpath + '/point1'),
                                            db.getVector(xpath + '/point2'),
                                            float(db.getValue(xpath + '/radius')))
            elif typeString == 'sphere':
                self._actor = sphereActor(db.getVector(xpath + '/point1'), float(db.getValue(xpath + '/radius')))
            elif typeString == 'cellZone':
                self._actor = app.cellZoneActor(int(db.getValue(xpath + '/cellZone')))

        return self._actor

    def isDisplayOn(self):
        return self._eyeOn

    def onClicked(self, checked):
        if self._eyeOn:
            self.displayOff()
        else:
            self.displayOn()

        self.eyeToggled.emit(self._eyeOn)

    def check(self):
        self._button.setChecked(True)

    def uncheck(self):
        self._button.setChecked(False)

    def displayOn(self):
        self._eyeOn = True
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-outline.svg'))))

    def displayOff(self):
        self._eyeOn = False
        self._eye.setIcon(QIcon(str(resource.file('ionicons/eye-off-outline.svg'))))

    def removeActor(self):
        self._actor = None


class InitializationWidget(QWidget):
    displayChecked = Signal(SectionRow)
    displayUnchecked = Signal(SectionRow)

    def __init__(self, rname: str):
        super().__init__()
        self._ui = Ui_initializationWidget()
        self._ui.setupUi(self)

        self._rname = rname
        self._initialValuesPath = f'regions/region[name="{rname}"]/initialization/initialValues'
        self._dialog = None
        self._sectionDialog: Optional[SectionDialog] = None
        self._rows = {}
        self._currentRow: Optional[SectionRow] = None

        self._volumeFractionWidget = None
        self._scalarsWidget = None
        self._speciesWidget = None

        mid = RegionDB.getMaterial(self._rname)
        if MaterialDB.isFluid(mid):
            volumeFractionWidget = VolumeFractionWidget(rname)
            scalarsWidget = UserDefinedScalarsWidget(rname)
            speciesWidget = SpeciesWidget(mid)

            if volumeFractionWidget.on():
                self._volumeFractionWidget = volumeFractionWidget
                self._ui.initialValuesLayout.addWidget(self._volumeFractionWidget)

            if scalarsWidget.on():
                self._scalarsWidget = scalarsWidget
                self._ui.initialValuesLayout.addWidget(self._scalarsWidget)

            if speciesWidget.on():
                self._speciesWidget = speciesWidget
                self._ui.initialValuesLayout.addWidget(self._speciesWidget)
        else:
            self._ui.velocity.hide()
            self._ui.properties.layout().setRowVisible(self._ui.pressure, False)
            self._ui.turbulence.hide()

        self._updateEnabled()
        self._connectSignalsSlots()

    def load(self):
        db = coredb.CoreDB()

        boundaries = coredb.CoreDB().getBoundaryConditions(self._rname)
        self._ui.computeFrom.blockSignals(True)
        for bcid, bcname, bctypestr in boundaries:
            if BoundaryType(bctypestr) in [BoundaryType.VELOCITY_INLET, BoundaryType.FREE_STREAM, BoundaryType.FAR_FIELD_RIEMANN]:
                self._ui.computeFrom.addItem(bcname, bcid)
        self._ui.computeFrom.setCurrentIndex(-1)
        self._ui.computeFrom.blockSignals(False)

        self._ui.xVelocity.setText(db.getValue(self._initialValuesPath + '/velocity/x'))
        self._ui.yVelocity.setText(db.getValue(self._initialValuesPath + '/velocity/y'))
        self._ui.zVelocity.setText(db.getValue(self._initialValuesPath + '/velocity/z'))
        self._ui.pressure.setText(db.getValue(self._initialValuesPath + '/pressure'))
        self._ui.temperature.setText(db.getValue(self._initialValuesPath + '/temperature'))
        self._ui.scaleOfVelocity.setText(db.getValue(self._initialValuesPath + '/scaleOfVelocity'))
        self._ui.turbulentIntensity.setText(db.getValue(self._initialValuesPath + '/turbulentIntensity'))
        self._ui.turbulentViscosityRatio.setText(db.getValue(self._initialValuesPath + '/turbulentViscosity'))

        turbulenceModel = TurbulenceModelsDB.getModel()
        self._ui.temperature.setEnabled(ModelsDB.isEnergyModelOn())
        self._ui.turbulence.setDisabled(turbulenceModel in (TurbulenceModel.INVISCID, TurbulenceModel.LAMINAR))
        self._ui.turbulentIntensity.setDisabled(
            turbulenceModel == TurbulenceModel.SPALART_ALLMARAS
            or TurbulenceModelsDB.getDESRansModel() == RANSModel.SPALART_ALLMARAS
            or TurbulenceModelsDB.isLESSpalartAllmarasModel()
        )

        if self._volumeFractionWidget:
            self._volumeFractionWidget.load(self._initialValuesPath + '/volumeFractions')

        if self._scalarsWidget:
            self._scalarsWidget.load(self._initialValuesPath + '/userDefinedScalars')

        if self._speciesWidget:
            self._speciesWidget.load(f'{self._initialValuesPath}/species')

        sections: list[str] = db.getList(f'/regions/region[name="{self._rname}"]/initialization/advanced/sections/section/name')
        for name in sections:
            if name in self._rows:
                self._rows[name].displayOff()
            else:
                self._addSectionRow(name)

    def validate(self) -> tuple[bool, str]:
        if self._volumeFractionWidget:
            valid, msg = self._volumeFractionWidget.validate()
            if not valid:
                return valid, msg

        # ToDo: Add validation for other parameters
        return True, ''

    async def appendToWriter(self, writer):
        writer.append(self._initialValuesPath + '/velocity/x', self._ui.xVelocity.text(),
                      self.tr('X-Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/velocity/y', self._ui.yVelocity.text(),
                      self.tr('Y-Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/velocity/z', self._ui.zVelocity.text(),
                      self.tr('Z-Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/pressure', self._ui.pressure.text(),
                      self.tr('Pressure of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/temperature', self._ui.temperature.text(),
                      self.tr('Temperature of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/scaleOfVelocity', self._ui.scaleOfVelocity.text(),
                      self.tr('Scale of Velocity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/turbulentIntensity', self._ui.turbulentIntensity.text(),
                      self.tr('Turbulent Intensity of region [{}]').format(self._rname))
        writer.append(self._initialValuesPath + '/turbulentViscosity', self._ui.turbulentViscosityRatio.text(),
                      self.tr('Turbulent Viscosity of region [{}]').format(self._rname))

        if (self._volumeFractionWidget
                and not await self._volumeFractionWidget.appendToWriter(
                    writer, self._initialValuesPath + '/volumeFractions')):
            return False

        if (self._scalarsWidget
                and not self._scalarsWidget.appendToWriter(writer, self._initialValuesPath + '/userDefinedScalars')):
            return False

        if (self._speciesWidget
                and not await self._speciesWidget.appendToWriter(writer, f'{self._initialValuesPath}/species')):
            return False

        return True

    def _connectSignalsSlots(self):
        Project.instance().solverStatusChanged.connect(self._updateEnabled)

        self._ui.computeFrom.currentIndexChanged.connect(self._computeFromChanged)
        self._ui.create.clicked.connect(self._createOption)
        self._ui.delete_.clicked.connect(self._deleteOption)
        self._ui.edit.clicked.connect(self._editOption)

    def _updateEnabled(self):
        self._ui.initialValues.setEnabled(not CaseManager().isActive())
        self._ui.advanced.setEnabled(not CaseManager().isActive())

    def _computeFromChanged(self):
        bcid = self._ui.computeFrom.currentData()
        self._computeFromBoundary(bcid)

    def _createOption(self):
        self._sectionDialog = SectionDialog(self, self._rname)
        self._sectionDialog.accepted.connect(self._updateSectionList)
        self._sectionDialog.open()

    def _deleteOption(self):
        if self._currentRow is None:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('Please select a section to edit'))
            return

        button = QMessageBox.question(self, self.tr('Alert'), self.tr('Delete selected section?'))
        if button == QMessageBox.StandardButton.No:
            return

        sectionPath = f'/regions/region[name="{self._rname}"]/initialization/advanced/sections/section[name="{self._currentRow.name}"]'

        writer = CoreDBWriter()
        writer.removeElement(sectionPath)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr('Input Error'), writer.firstError().toMessage())
            return

        row = self._rows.pop(self._currentRow.name)
        if row.isDisplayOn():
            self.displayUnchecked.emit(row)

        self._ui.sectionListLayout.removeWidget(self._currentRow)
        self._currentRow.close()
        self._currentRow = None

    def _editOption(self):
        if self._currentRow is None:
            QMessageBox.warning(self, self.tr('Warning'), self.tr('Please select a section to edit'))
            return

        self._sectionDialog = SectionDialog(self, self._rname, self._currentRow.name)
        self._sectionDialog.accepted.connect(self._updateSectionList)
        self._sectionDialog.open()

    def _updateSectionList(self):
        if self._sectionDialog is None:
            return

        name = self._sectionDialog.sectionName

        if name in self._rows:
            row = self._rows[name]
            self.displayUnchecked.emit(row)
            row.removeActor()
            if row.isDisplayOn():
                self.displayChecked.emit(row)
        else:
            self._addSectionRow(name)

        self._sectionDialog = None

    def _rowSelectionChanged(self, checked):
        row: SectionRow = self.sender()
        if checked:
            self._currentRow = row
            for r in self._rows.values():
                if r != row:
                    r.uncheck()
        else:
            if row == self._currentRow:
                row.check()

    def _rowDoubleClicked(self):
        row: SectionRow = self.sender()
        self._currentRow = row
        for r in self._rows.values():
            if r != row:
                r.uncheck()

        self._editOption()

    def _rowEyeToggled(self, checked):
        row: SectionRow = self.sender()

        if checked:
            self.displayChecked.emit(row)
        else:
            self.displayUnchecked.emit(row)

    def _addSectionRow(self, name):
        row = SectionRow(name, self._rname)
        self._rows[name] = row
        row.toggled.connect(self._rowSelectionChanged)
        row.doubleClicked.connect(self._rowDoubleClicked)
        row.eyeToggled.connect(self._rowEyeToggled)
        idx = self._ui.sectionListLayout.count() - 1
        self._ui.sectionListLayout.insertWidget(idx, row)

    def _computeFromBoundary(self, bcid: int):
        db = CoreDBReader()  # Not "coredb" because Parsed data is required rather than raw USER PARAMETERS
        bctype = BoundaryDB.getBoundaryType(bcid)
        xpath = BoundaryDB.getXPath(bcid)

        v = float(self._ui.scaleOfVelocity.text())

        # Velocity
        if bctype == BoundaryType.VELOCITY_INLET:
            spec = VelocitySpecification(db.getValue(xpath + '/velocityInlet/velocity/specification'))
            if spec == VelocitySpecification.COMPONENT:
                profile = VelocityProfile(db.getValue(xpath + '/velocityInlet/velocity/component/profile'))
                if profile == VelocityProfile.CONSTANT:
                    ux = db.getValue(xpath + '/velocityInlet/velocity/component/constant/x')
                    uy = db.getValue(xpath + '/velocityInlet/velocity/component/constant/y')
                    uz = db.getValue(xpath + '/velocityInlet/velocity/component/constant/z')
                    self._ui.xVelocity.setText(ux)
                    self._ui.yVelocity.setText(uy)
                    self._ui.zVelocity.setText(uz)
                    v = sqrt(float(ux)**2 + float(uy)**2 + float(uz)**2)
                    self._ui.scaleOfVelocity.setText(str(v))
        elif bctype == BoundaryType.FREE_STREAM:
            dx, dy, dz = db.getFlowDirection(xpath + '/freeStream/flowDirection')
            dMag = sqrt(dx ** 2 + dy ** 2 + dz ** 2)
            speed = db.getValue(xpath + '/freeStream/speed')
            am = float(speed) / dMag

            self._ui.xVelocity.setText(str(am * dx))
            self._ui.yVelocity.setText(str(am * dy))
            self._ui.zVelocity.setText(str(am * dz))
            self._ui.scaleOfVelocity.setText(speed)
        elif bctype == BoundaryType.FAR_FIELD_RIEMANN:
            spec = DirectionSpecificationMethod(db.getValue(xpath + '/farFieldRiemann/flowDirection/specificationMethod'))
            drag = db.getVector(xpath + '/farFieldRiemann/flowDirection/dragDirection')
            lift = db.getVector(xpath + '/farFieldRiemann/flowDirection/liftDirection')
            if spec == DirectionSpecificationMethod.AOA_AOS:
                drag, lift = calucateDirectionsByRotation(drag, lift,
                                                        float(db.getValue(xpath + '/farFieldRiemann/flowDirection/angleOfAttack')),
                                                        float(db.getValue(xpath + '/farFieldRiemann/flowDirection/angleOfSideslip')))

            dx, dy, dz = drag  # Flow Direction
            gamma = 1.4
            mw = db.getMolecularWeight(MaterialDB.getMaterialComposition(xpath + '/species', RegionDB.getMaterial(self._rname)))
            a = sqrt(gamma * (UNIVERSAL_GAS_CONSTANT / mw) * float(db.getValue(xpath + '/farFieldRiemann/staticTemperature')))
            mInf = float(db.getValue(xpath + '/farFieldRiemann/machNumber'))
            dMag = sqrt(dx ** 2 + dy ** 2 + dz ** 2)
            am = a * mInf / dMag

            self._ui.xVelocity.setText(str(am * dx))
            self._ui.yVelocity.setText(str(am * dy))
            self._ui.zVelocity.setText(str(am * dz))

            v = a * mInf
            self._ui.scaleOfVelocity.setText(str(v))

        # pressure
        if bctype == BoundaryType.FREE_STREAM:
            self._ui.pressure.setText(db.getValue(xpath + '/freeStream/pressure'))
        elif bctype == BoundaryType.FAR_FIELD_RIEMANN:
            self._ui.pressure.setText(db.getValue(xpath + '/farFieldRiemann/staticPressure'))

        # temperature
        if bctype in [BoundaryType.VELOCITY_INLET, BoundaryType.FREE_STREAM]:
            if ModelsDB.isEnergyModelOn():
                tProfile = TemperatureProfile(db.getValue(xpath + '/temperature/profile'))
                if tProfile == TemperatureProfile.CONSTANT:
                    self._ui.temperature.setText(db.getValue(xpath + '/temperature/constant'))
        elif bctype == BoundaryType.FAR_FIELD_RIEMANN:
            self._ui.temperature.setText(db.getValue(xpath + '/farFieldRiemann/staticTemperature'))

        # turbulence intensity
        # turbulence viscosity
        p = float(self._ui.pressure.text())
        t = float(self._ui.temperature.text())

        material = MaterialDB.getMaterialComposition(xpath + '/species', RegionDB.getMaterial(self._rname))
        rho = db.getDensity(material, t, p)  # Density
        mu = db.getViscosity(material, t)  # Viscosity
        if rho > 0:
            nu = mu / rho  # Kinetic Viscosity
        else:  # To prevent device-by-zero exception. Some configurations may be inconsistent.
            nu = mu

        if turbulenceModel := TurbulenceModelsDB.getRASModel():
            if turbulenceModel == TurbulenceModel.K_EPSILON:
                i, b = self._getTurbulenceFromKEpsilonBoundary(db, xpath, v, nu)
                self._ui.turbulentIntensity.setText(i)
                self._ui.turbulentViscosityRatio.setText(b)
            elif turbulenceModel == TurbulenceModel.K_OMEGA:
                i, b = self._getTurbulenceFromKOmegaBoundary(db, xpath, v, nu)
                self._ui.turbulentIntensity.setText(i)
                self._ui.turbulentViscosityRatio.setText(b)
            elif turbulenceModel == TurbulenceModel.SPALART_ALLMARAS:
                b = self._getTurbulenceFromSpalartAllmarasBoundary(db, xpath, v, nu)
                self._ui.turbulentViscosityRatio.setText(b)
            elif turbulenceModel == TurbulenceModel.DES:
                ransModel = TurbulenceModelsDB.getDESRansModel()
                if ransModel == RANSModel.SPALART_ALLMARAS:
                    b = self._getTurbulenceFromSpalartAllmarasBoundary(db, xpath, v, nu)
                    self._ui.turbulentViscosityRatio.setText(b)
                elif ransModel == RANSModel.K_OMEGA_SST:
                    i, b = self._getTurbulenceFromKOmegaBoundary(db, xpath, v, nu)
                    self._ui.turbulentIntensity.setText(i)
                    self._ui.turbulentViscosityRatio.setText(b)

        # volume fraction
        if bctype == BoundaryType.VELOCITY_INLET:
            if self._volumeFractionWidget:
                self._volumeFractionWidget.load(xpath + '/volumeFractions')

        # UDS
        if bctype in [BoundaryType.VELOCITY_INLET, BoundaryType.FREE_STREAM]:
            if self._scalarsWidget:
                self._scalarsWidget.load(xpath + '/userDefinedScalars')

        # species
        if bctype in [BoundaryType.VELOCITY_INLET, BoundaryType.FREE_STREAM]:
            if self._speciesWidget:
                self._speciesWidget.load(xpath + '/species')


    def _getTurbulenceFromKEpsilonBoundary(self, db: CoreDBReader, xpath: str, v: float, nu: float) -> tuple[str, str]:
        spec = KEpsilonSpecification(db.getValue(xpath + '/turbulence/k-epsilon/specification'))
        if spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO:
            i = db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity')
            b = db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio')
            return i, b
        elif spec == KEpsilonSpecification.K_AND_EPSILON:
            k = float(db.getValue(xpath + '/turbulence/k-epsilon/turbulentKineticEnergy'))
            e = float(db.getValue(xpath + '/turbulence/k-epsilon/turbulentDissipationRate'))
            i = sqrt(k / 1.5) / v
            nut = 0.09 * k * k / e
            b = nut / nu
            return str(i), str(b)

    def _getTurbulenceFromKOmegaBoundary(self, db: CoreDBReader, xpath: str, v: float, nu: float) -> tuple[str, str]:
        spec = KOmegaSpecification(db.getValue(xpath + '/turbulence/k-omega/specification'))
        if spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO:
            i = db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity')
            b = db.getValue(xpath + '/turbulence/k-omega/turbulentViscosityRatio')
            return i, b
        elif spec == KOmegaSpecification.K_AND_OMEGA:
            k = float(db.getValue(xpath + '/turbulence/k-omega/turbulentKineticEnergy'))
            w = float(db.getValue(xpath + '/turbulence/k-omega/specificDissipationRate'))
            i = sqrt(k / 1.5) / v
            nut = k / w
            b = nut / nu
            return str(i), str(b)

    def _getTurbulenceFromSpalartAllmarasBoundary(self, db: CoreDBReader, xpath: str, v: float, nu: float) -> str:
        spec = SpalartAllmarasSpecification(db.getValue(xpath + '/turbulence/spalartAllmaras/specification'))
        if spec == SpalartAllmarasSpecification.TURBULENT_VISCOSITY_RATIO:
            b = db.getValue(xpath + '/turbulence/spalartAllmaras/turbulentViscosityRatio')
            return b
        elif spec == SpalartAllmarasSpecification.MODIFIED_TURBULENT_VISCOSITY:
            nuTilda = float(db.getValue(xpath + '/turbulence/spalartAllmaras/modifiedTurbulentViscosity'))
            b = nuTilda / nu
            return str(b)
