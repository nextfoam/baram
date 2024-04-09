#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel
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
        self._subgridScaleModelRadios = EnumButtonGroup()
        self._lengthScaleModelRadios = EnumButtonGroup()

        self._db = coredb.CoreDB()
        self._xpath = ModelsDB.TURBULENCE_MODELS_XPATH

        self._modelRadios.addEnumButton(self._ui.inviscid,        TurbulenceModel.INVISCID)
        self._modelRadios.addEnumButton(self._ui.laminar,         TurbulenceModel.LAMINAR)
        self._modelRadios.addEnumButton(self._ui.spalartAllmaras, TurbulenceModel.SPALART_ALLMARAS)
        self._modelRadios.addEnumButton(self._ui.kEpsilon,        TurbulenceModel.K_EPSILON)
        self._modelRadios.addEnumButton(self._ui.kOmega,          TurbulenceModel.K_OMEGA)
        self._modelRadios.addEnumButton(self._ui.LES,             TurbulenceModel.LES)

        self._kEpsilonModelRadios.addEnumButton(self._ui.standard,   KEpsilonModel.STANDARD)
        self._kEpsilonModelRadios.addEnumButton(self._ui.RNG,        KEpsilonModel.RNG)
        self._kEpsilonModelRadios.addEnumButton(self._ui.realizable, KEpsilonModel.REALIZABLE)

        self._nearWallTreatmentRadios.addEnumButton(self._ui.standardWallFunction,  NearWallTreatment.STANDARD_WALL_FUNCTIONS)
        self._nearWallTreatmentRadios.addEnumButton(self._ui.enhancedWallTreatment, NearWallTreatment.ENHANCED_WALL_TREATMENT)

        self._subgridScaleModelRadios.addEnumButton(self._ui.smagorinskyLilly,          SubgridScaleModel.SMAGORINSKY)
        self._subgridScaleModelRadios.addEnumButton(self._ui.WALE,                      SubgridScaleModel.WALE)
        self._subgridScaleModelRadios.addEnumButton(self._ui.kineticEnergyTransport,    SubgridScaleModel.DYNAMIC_KEQN)
        self._subgridScaleModelRadios.addEnumButton(self._ui.oneEquationEddyViscosity,  SubgridScaleModel.KEQN)

        self._lengthScaleModelRadios.addEnumButton(self._ui.cubeRootVolume, LengthScaleModel.CUBE_ROOT_VOLUME)
        self._lengthScaleModelRadios.addEnumButton(self._ui.vanDriest,      LengthScaleModel.VAN_DRIEST)
        self._lengthScaleModelRadios.addEnumButton(self._ui.smooth,         LengthScaleModel.SMOOTH)

        self._ui.LES.setEnabled(GeneralDB.isTimeTransient())

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._modelRadios.dataChecked.connect(self._modelChanged)
        self._kEpsilonModelRadios.dataChecked.connect(self._kEpsilonModelChanged)
        self._nearWallTreatmentRadios.dataChecked.connect(self._nearWallTreatmentChanged)
        self._subgridScaleModelRadios.dataChecked.connect(self._updateLESConstantsVisibility)

    def accept(self):
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
        elif model == TurbulenceModel.LES:
            subgridScaleModel = self._subgridScaleModelRadios.checkedData()
            writer.append(self._xpath + '/les/subgridScaleModel', subgridScaleModel.value, None)
            writer.append(self._xpath + '/les/lengthScaleModel', self._lengthScaleModelRadios.checkedData().value, None)

            if subgridScaleModel == SubgridScaleModel.DYNAMIC_KEQN:
                writer.append(self._xpath + '/les/modelConstants/k', self._ui.ck.text(), self.tr('ck'))
                writer.append(self._xpath + '/les/modelConstants/e', self._ui.ce.text(), self.tr('ce'))
            elif subgridScaleModel == SubgridScaleModel.WALE:
                writer.append(self._xpath + '/les/modelConstants/w', self._ui.cw.text(), self.tr('cw'))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        self._modelRadios.setCheckedValue(TurbulenceModel(self._db.getValue(self._xpath + '/model')))
        self._kEpsilonModelRadios.setCheckedValue(KEpsilonModel(self._db.getValue(self._xpath + '/k-epsilon/model')))
        self._nearWallTreatmentRadios.setCheckedValue(
            NearWallTreatment(self._db.getValue(self._xpath + '/k-epsilon/realizable/nearWallTreatment')))
        self._subgridScaleModelRadios.setCheckedValue(
            SubgridScaleModel(self._db.getValue(self._xpath + '/les/subgridScaleModel')))
        self._lengthScaleModelRadios.setCheckedValue(
            LengthScaleModel(self._db.getValue(self._xpath + '/les/lengthScaleModel')))

        self._ui.energyPrandtlNumber.setText(self._db.getValue(self._xpath + '/energyPrandtlNumber'))
        self._ui.wallPrandtlNumber.setText(self._db.getValue(self._xpath + '/wallPrandtlNumber'))

        self._ui.threshold.setText(self._db.getValue(self._xpath + '/k-epsilon/realizable/threshold'))
        self._ui.blendingWidth.setText(self._db.getValue(self._xpath + '/k-epsilon/realizable/blendingWidth'))

        self._ui.ck.setText(self._db.getValue(self._xpath + '/les/modelConstants/k'))
        self._ui.ce.setText(self._db.getValue(self._xpath + '/les/modelConstants/e'))
        self._ui.cw.setText(self._db.getValue(self._xpath + '/les/modelConstants/w'))

    def _modelChanged(self, model):
        self._ui.kEpsilonModel.setVisible(model == TurbulenceModel.K_EPSILON)
        self._ui.kOmegaModel.setVisible(model == TurbulenceModel.K_OMEGA)
        self._ui.LESModel.setVisible(model == TurbulenceModel.LES)

        self._ui.RASModelConstants.setVisible(model in TurbulenceRasModels)

        self._updateReynoldsParametersVisibility()
        self._updateLESConstantsVisibility()

    def _kEpsilonModelChanged(self):
        self._ui.nearWallTreatment.setVisible(self._ui.realizable.isChecked())
        self._updateReynoldsParametersVisibility()

    def _nearWallTreatmentChanged(self):
        self._updateReynoldsParametersVisibility()

    def _updateLESConstantsVisibility(self):
        if self._modelRadios.checkedData() != TurbulenceModel.LES:
            self._ui.LESModelConstants.hide()
            return

        model = self._subgridScaleModelRadios.checkedData()
        self._ui.LESModelConstants.setVisible(model != SubgridScaleModel.DYNAMIC_KEQN)
        self._ui.LESConstantsLayout.setRowVisible(self._ui.cw, model == SubgridScaleModel.WALE)

    def _updateReynoldsParametersVisibility(self):
        isActive = self._isEnhancedWallTreatmentActive()
        self._ui.reynoldsGroup.setVisible(isActive)

    def _isEnhancedWallTreatmentActive(self) -> bool:
        return (self._ui.kEpsilon.isChecked()
                and self._ui.realizable.isChecked()
                and self._ui.enhancedWallTreatment.isChecked())
