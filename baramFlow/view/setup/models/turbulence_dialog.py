#!/usr/bin/env python
# -*- coding: utf-8 -*-

import qasync
from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel, RANSModel, ShieldingFunctions
from baramFlow.coredb.models_db import TurbulenceRasModels, KEpsilonModel, NearWallTreatment, KOmegaModel
from baramFlow.coredb.models_db import SubgridScaleModel, LengthScaleModel
from baramFlow.view.widgets.enum_button_group import EnumButtonGroup
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .turbulence_dialog_ui import Ui_TurbulenceDialog


class TurbulenceModelDialog(ResizableDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_TurbulenceDialog()
        self._ui.setupUi(self)

        self._modelRadios = EnumButtonGroup()

        self._kEpsilonModelRadios = EnumButtonGroup()
        self._nearWallTreatmentRadios = EnumButtonGroup()

        self._RANSModelRadios = EnumButtonGroup()
        self._shieldingFunctionsRadios = EnumButtonGroup()
        self._DESLengthScaleModelRadios = EnumButtonGroup()

        self._subgridScaleModelRadios = EnumButtonGroup()
        self._LESLengthScaleModelRadios = EnumButtonGroup()

        self._xpath = ModelsDB.TURBULENCE_MODELS_XPATH

        self._modelRadios.addEnumButton(self._ui.inviscid,        TurbulenceModel.INVISCID)
        self._modelRadios.addEnumButton(self._ui.laminar,         TurbulenceModel.LAMINAR)
        self._modelRadios.addEnumButton(self._ui.spalartAllmaras, TurbulenceModel.SPALART_ALLMARAS)
        self._modelRadios.addEnumButton(self._ui.kEpsilon,        TurbulenceModel.K_EPSILON)
        self._modelRadios.addEnumButton(self._ui.kOmega,          TurbulenceModel.K_OMEGA)
        self._modelRadios.addEnumButton(self._ui.DES,             TurbulenceModel.DES)
        self._modelRadios.addEnumButton(self._ui.LES,             TurbulenceModel.LES)

        self._kEpsilonModelRadios.addEnumButton(self._ui.standard,   KEpsilonModel.STANDARD)
        self._kEpsilonModelRadios.addEnumButton(self._ui.RNG,        KEpsilonModel.RNG)
        self._kEpsilonModelRadios.addEnumButton(self._ui.realizable, KEpsilonModel.REALIZABLE)

        self._nearWallTreatmentRadios.addEnumButton(self._ui.standardWallFunction,  NearWallTreatment.STANDARD_WALL_FUNCTIONS)
        self._nearWallTreatmentRadios.addEnumButton(self._ui.enhancedWallTreatment, NearWallTreatment.ENHANCED_WALL_TREATMENT)

        self._RANSModelRadios.addEnumButton(self._ui.RANSSpalartAllmaras,   RANSModel.SPALART_ALLMARAS)
        self._RANSModelRadios.addEnumButton(self._ui.RANSKOmegaSST,         RANSModel.K_OMEGA_SST)

        self._shieldingFunctionsRadios.addEnumButton(self._ui.DDES, ShieldingFunctions.DDES)
        self._shieldingFunctionsRadios.addEnumButton(self._ui.IDDES, ShieldingFunctions.IDDES)

        self._DESLengthScaleModelRadios.addEnumButton(self._ui.DESCubeRootVolume, LengthScaleModel.CUBE_ROOT_VOLUME)
        self._DESLengthScaleModelRadios.addEnumButton(self._ui.DESVanDriest, LengthScaleModel.VAN_DRIEST)
        self._DESLengthScaleModelRadios.addEnumButton(self._ui.DESSmooth, LengthScaleModel.SMOOTH)

        self._subgridScaleModelRadios.addEnumButton(self._ui.smagorinskyLilly,          SubgridScaleModel.SMAGORINSKY)
        self._subgridScaleModelRadios.addEnumButton(self._ui.WALE,                      SubgridScaleModel.WALE)
        self._subgridScaleModelRadios.addEnumButton(self._ui.kineticEnergyTransport,    SubgridScaleModel.DYNAMIC_KEQN)
        self._subgridScaleModelRadios.addEnumButton(self._ui.oneEquationEddyViscosity,  SubgridScaleModel.KEQN)

        self._LESLengthScaleModelRadios.addEnumButton(self._ui.LESCubeRootVolume, LengthScaleModel.CUBE_ROOT_VOLUME)
        self._LESLengthScaleModelRadios.addEnumButton(self._ui.LESVanDriest, LengthScaleModel.VAN_DRIEST)
        self._LESLengthScaleModelRadios.addEnumButton(self._ui.LESSmooth, LengthScaleModel.SMOOTH)

        self._ui.LES.setEnabled(GeneralDB.isTimeTransient())
        self._ui.DES.setEnabled(GeneralDB.isTimeTransient())

        if not ModelsDB.isSpeciesModelOn():
            self._ui.schmidtNumber.hide()

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._modelRadios.dataChecked.connect(self._modelChanged)
        self._kEpsilonModelRadios.dataChecked.connect(self._kEpsilonModelChanged)
        self._nearWallTreatmentRadios.dataChecked.connect(self._nearWallTreatmentChanged)
        self._RANSModelRadios.dataChecked.connect(self._RANSModelChanged)
        self._ui.delayedDES.stateChanged.connect(self._delayedDESChanged)
        self._shieldingFunctionsRadios.dataChecked.connect(self._updateDESLengthScaleModelVisibility)
        self._subgridScaleModelRadios.dataChecked.connect(self._updateLESConstantsVisibility)
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        writer = CoreDBWriter()

        model = self._modelRadios.checkedData()
        writer.append(self._xpath + '/model', model.value, None)

        if model in TurbulenceRasModels:
            if model == TurbulenceModel.K_EPSILON:
                kEpsilonModel = self._kEpsilonModelRadios.checkedData()
                writer.append(self._xpath + '/k-epsilon/model', kEpsilonModel.value, None)

                if kEpsilonModel == KEpsilonModel.REALIZABLE:
                    nearWallTreatment = self._nearWallTreatmentRadios.checkedData()
                    writer.append(self._xpath + '/k-epsilon/realizable/nearWallTreatment',
                                  nearWallTreatment.value, self.tr('Near-wall Treatment'))
                    if nearWallTreatment == NearWallTreatment.ENHANCED_WALL_TREATMENT:
                        writer.append(self._xpath + '/k-epsilon/realizable/threshold',
                                      self._ui.threshold.text(), self.tr('Reynolds Threshold'))
                        writer.append(self._xpath + '/k-epsilon/realizable/blendingWidth',
                                      self._ui.blendingWidth.text(), self.tr('Reynolds Blending Width'))
            elif model == TurbulenceModel.K_OMEGA:
                writer.append(self._xpath + '/k-omega/model', KOmegaModel.SST.value, None)

            writer.append(self._xpath + '/energyPrandtlNumber',
                          self._ui.energyPrandtlNumber.text(), self.tr('Energy PrandtlNumber'))
            writer.append(self._xpath + '/wallPrandtlNumber',
                          self._ui.wallPrandtlNumber.text(), self.tr('Wall PrandtlNumber'))
        elif model == TurbulenceModel.DES:
            ransModel = self._RANSModelRadios.checkedData()
            writer.append(self._xpath + '/des/RANSModel', ransModel.value, None)
            if ransModel == RANSModel.SPALART_ALLMARAS:
                writer.append(self._xpath + '/des/spalartAllmarasOptions/lowReDamping',
                              'true' if self._ui.lowReDamping.isChecked() else 'false', None)
                writer.append(self._xpath + '/des/modelConstants/DES', self._ui.cDES.text(),
                              self.tr('DES Model Constants'))
            elif ransModel == RANSModel.K_OMEGA_SST:
                writer.append(self._xpath + '/des/modelConstants/DESKOmega', self._ui.cDESKOmega.text(),
                              self.tr('k-omega DES Model Constants'))
                writer.append(self._xpath + '/des/modelConstants/DESKEpsilon', self._ui.cDESKEpsilon.text(),
                              self.tr('k-epsilon DES Model Constants'))

            delayedDES = self._ui.delayedDES.isChecked()
            writer.append(self._xpath + '/des/DESOptions/delayedDES', 'true' if delayedDES else 'false', None)
            shieldingFunctions = None
            if delayedDES:
                shieldingFunctions = self._shieldingFunctionsRadios.checkedData()
                writer.append(self._xpath + '/des/shieldingFunctions',
                              shieldingFunctions.value, None)
            if shieldingFunctions != ShieldingFunctions.IDDES:
                writer.append(self._xpath + '/des/lengthScaleModel',
                              self._DESLengthScaleModelRadios.checkedData().value, None)
        elif model == TurbulenceModel.LES:
            subgridScaleModel = self._subgridScaleModelRadios.checkedData()
            writer.append(self._xpath + '/les/subgridScaleModel', subgridScaleModel.value, None)
            writer.append(self._xpath + '/les/lengthScaleModel',
                          self._LESLengthScaleModelRadios.checkedData().value, None)

            if subgridScaleModel == SubgridScaleModel.DYNAMIC_KEQN:
                writer.append(self._xpath + '/les/modelConstants/k', self._ui.ck.text(),
                              self.tr('LES Model Constants k'))
                writer.append(self._xpath + '/les/modelConstants/e', self._ui.ce.text(),
                              self.tr('LES Model Constants e'))
            elif subgridScaleModel == SubgridScaleModel.WALE:
                writer.append(self._xpath + '/les/modelConstants/w', self._ui.cw.text(),
                              self.tr('LES Model Constants w'))

        if ModelsDB.isSpeciesModelOn():
            writer.append(self._xpath + '/turbulentSchmidtNumber', self._ui.turbulentSchmidtNumber.text(),
                          self.tr('Turbulent Schmidt Number'))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        db = coredb.CoreDB()

        self._modelRadios.setCheckedData(TurbulenceModel(db.getValue(self._xpath + '/model')))
        self._kEpsilonModelRadios.setCheckedData(KEpsilonModel(db.getValue(self._xpath + '/k-epsilon/model')))
        self._nearWallTreatmentRadios.setCheckedData(
            NearWallTreatment(db.getValue(self._xpath + '/k-epsilon/realizable/nearWallTreatment')))

        self._RANSModelRadios.setCheckedData(RANSModel(db.getValue(self._xpath + '/des/RANSModel')))
        self._ui.lowReDamping.setChecked(
            db.getValue(self._xpath + '/des/spalartAllmarasOptions/lowReDamping') == 'true')
        self._ui.delayedDES.setChecked(db.getValue(self._xpath + '/des/DESOptions/delayedDES') == 'true')
        self._shieldingFunctionsRadios.setCheckedData(
            ShieldingFunctions(db.getValue(self._xpath + '/des/shieldingFunctions')))
        self._DESLengthScaleModelRadios.setCheckedData(
            LengthScaleModel(db.getValue(self._xpath + '/des/lengthScaleModel')))

        self._subgridScaleModelRadios.setCheckedData(
            SubgridScaleModel(db.getValue(self._xpath + '/les/subgridScaleModel')))
        self._LESLengthScaleModelRadios.setCheckedData(
            LengthScaleModel(db.getValue(self._xpath + '/les/lengthScaleModel')))

        self._ui.energyPrandtlNumber.setText(db.getValue(self._xpath + '/energyPrandtlNumber'))
        self._ui.wallPrandtlNumber.setText(db.getValue(self._xpath + '/wallPrandtlNumber'))

        self._ui.threshold.setText(db.getValue(self._xpath + '/k-epsilon/realizable/threshold'))
        self._ui.blendingWidth.setText(db.getValue(self._xpath + '/k-epsilon/realizable/blendingWidth'))

        self._ui.cDES.setText(db.getValue(self._xpath + '/des/modelConstants/DES'))
        self._ui.cDESKEpsilon.setText(db.getValue(self._xpath + '/des/modelConstants/DESKEpsilon'))
        self._ui.cDESKOmega.setText(db.getValue(self._xpath + '/des/modelConstants/DESKOmega'))

        self._ui.ck.setText(db.getValue(self._xpath + '/les/modelConstants/k'))
        self._ui.ce.setText(db.getValue(self._xpath + '/les/modelConstants/e'))
        self._ui.cw.setText(db.getValue(self._xpath + '/les/modelConstants/w'))

        if ModelsDB.isSpeciesModelOn():
            self._ui.turbulentSchmidtNumber.setText(db.getValue(self._xpath + '/turbulentSchmidtNumber'))

        self._delayedDESChanged()

    def _modelChanged(self, model):
        self._ui.kEpsilonModel.setVisible(model == TurbulenceModel.K_EPSILON)
        self._ui.kOmegaModel.setVisible(model == TurbulenceModel.K_OMEGA)
        self._ui.LESModel.setVisible(model == TurbulenceModel.LES)
        self._ui.DESModel.setVisible(model == TurbulenceModel.DES)

        self._ui.RASModelConstants.setVisible(model in TurbulenceRasModels)
        self._ui.DESModelConstants.setVisible(model == TurbulenceModel.DES)

        self._updateReynoldsParametersVisibility()
        self._updateLESConstantsVisibility()

    def _kEpsilonModelChanged(self, model):
        self._ui.nearWallTreatment.setVisible(model == KEpsilonModel.REALIZABLE)
        self._updateReynoldsParametersVisibility()

    def _nearWallTreatmentChanged(self):
        self._updateReynoldsParametersVisibility()

    def _RANSModelChanged(self, model):
        self._ui.sparlartAllmarasOptions.setVisible(model == RANSModel.SPALART_ALLMARAS)
        self._ui.DESConstantsLayout.setRowVisible(self._ui.cDES, model == RANSModel.SPALART_ALLMARAS)
        self._ui.DESConstantsLayout.setRowVisible(self._ui.cDESKOmega, model == RANSModel.K_OMEGA_SST)
        self._ui.DESConstantsLayout.setRowVisible(self._ui.cDESKEpsilon, model == RANSModel.K_OMEGA_SST)

    def _delayedDESChanged(self):
        self._ui.shieldingFunctions.setVisible(self._ui.delayedDES.isChecked())
        self._updateDESLengthScaleModelVisibility()

    def _updateReynoldsParametersVisibility(self):
        isActive = self._isEnhancedWallTreatmentActive()
        self._ui.reynoldsGroup.setVisible(isActive)

    def _isEnhancedWallTreatmentActive(self) -> bool:
        return (self._ui.kEpsilon.isChecked()
                and self._ui.realizable.isChecked()
                and self._ui.enhancedWallTreatment.isChecked())

    def _updateDESLengthScaleModelVisibility(self):
        self._ui.DESLengthScaleModel.setVisible(
            not self._ui.delayedDES.isChecked() or not self._ui.IDDES.isChecked())

    def _updateLESConstantsVisibility(self):
        if self._modelRadios.checkedData() != TurbulenceModel.LES:
            self._ui.LESModelConstants.hide()
            return

        model = self._subgridScaleModelRadios.checkedData()
        self._ui.LESModelConstants.setVisible(model != SubgridScaleModel.DYNAMIC_KEQN)
        self._ui.LESConstantsLayout.setRowVisible(self._ui.cw, model == SubgridScaleModel.WALE)
