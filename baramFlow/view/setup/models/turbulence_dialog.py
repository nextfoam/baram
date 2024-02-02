#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from baramFlow.coredb import coredb
from baramFlow.coredb.coredb_writer import CoreDBWriter
from baramFlow.coredb.models_db import ModelsDB, TurbulenceModel, TurbulenceRasModels, KEpsilonModel, NearWallTreatment, KOmegaModel
from baramFlow.view.widgets.resizable_dialog import ResizableDialog
from .turbulence_dialog_ui import Ui_TurbulenceDialog


class TurbulenceModelDialog(ResizableDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_TurbulenceDialog()
        self._ui.setupUi(self)

        self._ui.modelRadioGroup.setId(self._ui.inviscid,        TurbulenceModel.INVISCID.index)
        self._ui.modelRadioGroup.setId(self._ui.laminar,         TurbulenceModel.LAMINAR.index)
        self._ui.modelRadioGroup.setId(self._ui.spalartAllmaras, TurbulenceModel.SPALART_ALLMARAS.index)
        self._ui.modelRadioGroup.setId(self._ui.kEpsilon,        TurbulenceModel.K_EPSILON.index)
        self._ui.modelRadioGroup.setId(self._ui.kOmega,          TurbulenceModel.K_OMEGA.index)
        self._ui.modelRadioGroup.setId(self._ui.LES,             TurbulenceModel.LES.index)

        self._ui.kEpsilonRadioGroup.setId(self._ui.standard,   KEpsilonModel.STANDARD.index)
        self._ui.kEpsilonRadioGroup.setId(self._ui.RNG,        KEpsilonModel.RNG.index)
        self._ui.kEpsilonRadioGroup.setId(self._ui.realizable, KEpsilonModel.REALIZABLE.index)

        self._ui.nearWallTreatmentRadioGroup.setId(self._ui.standardWallFunction,  NearWallTreatment.STANDARD_WALL_FUNCTIONS.index)
        self._ui.nearWallTreatmentRadioGroup.setId(self._ui.enhancedWallTreatment, NearWallTreatment.ENHANCED_WALL_TREATMENT.index)

        self._db = coredb.CoreDB()
        self._xpath = ModelsDB.TURBULENCE_MODELS_XPATH

        self._ui.LES.setVisible(False)

        self._connectSignalsSlots()
        self._load()

    def _connectSignalsSlots(self):
        self._ui.modelRadioGroup.idToggled.connect(self._modelChanged)
        self._ui.kEpsilonRadioGroup.idToggled.connect(self._kEpsilonModelChanged)
        self._ui.nearWallTreatmentRadioGroup.idToggled.connect(self._nearWallTreatmentChanged)

    def accept(self):
        writer = CoreDBWriter()

        model = TurbulenceModel.byIndex(self._ui.modelRadioGroup.checkedId())
        writer.append(self._xpath + '/model', model.value, None)

        if model in TurbulenceRasModels:
            if model == TurbulenceModel.K_EPSILON:
                kEpsilonModel = KEpsilonModel.byIndex(self._ui.kEpsilonRadioGroup.checkedId())
                writer.append(self._xpath + '/k-epsilon/model', kEpsilonModel.value, None)

                if kEpsilonModel == KEpsilonModel.REALIZABLE:
                    nearWallTreatment = NearWallTreatment.byIndex(self._ui.nearWallTreatmentRadioGroup.checkedId())
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

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            super().accept()

    def _load(self):
        model = TurbulenceModel(self._db.getValue(self._xpath + '/model'))
        button = self._ui.modelRadioGroup.button(model.index)
        button.setChecked(True)

        model = KEpsilonModel(self._db.getValue(self._xpath + '/k-epsilon/model'))
        button = self._ui.kEpsilonRadioGroup.button(model.index)
        button.setChecked(True)

        model = NearWallTreatment(self._db.getValue(self._xpath + '/k-epsilon/realizable/nearWallTreatment'))
        button = self._ui.nearWallTreatmentRadioGroup.button(model.index)
        button.setChecked(True)

        self._ui.energyPrandtlNumber.setText(self._db.getValue(self._xpath + '/energyPrandtlNumber'))
        self._ui.wallPrandtlNumber.setText(self._db.getValue(self._xpath + '/wallPrandtlNumber'))

        self._ui.threshold.setText(self._db.getValue(self._xpath + '/k-epsilon/realizable/threshold'))
        self._ui.blendingWidth.setText(self._db.getValue(self._xpath + '/k-epsilon/realizable/blendingWidth'))

    def _modelChanged(self, id_, checked):
        if checked:
            model = TurbulenceModel.byIndex(id_)
            self._ui.kEpsilonModel.setVisible(self._ui.kEpsilon.isChecked())
            self._ui.kOmegaModel.setVisible(self._ui.kOmega.isChecked())
            self._ui.constantsWidget.setVisible(model in TurbulenceRasModels)
            self._updateReynoldsParametersVisibility()

    def _kEpsilonModelChanged(self, id_, checked):
        if checked:
            self._ui.nearWallTreatment.setVisible(self._ui.realizable.isChecked())
            self._updateReynoldsParametersVisibility()

    def _nearWallTreatmentChanged(self, id_, checked):
        self._updateReynoldsParametersVisibility()

    def _updateReynoldsParametersVisibility(self):
        isActive = self._isEnhancedWallTreatmentActive()
        self._ui.reynoldsGroup.setVisible(isActive)

    def _isEnhancedWallTreatmentActive(self) -> bool:
        try:
            model = TurbulenceModel.byIndex(self._ui.modelRadioGroup.checkedId())
            if model == TurbulenceModel.K_EPSILON:
                kEpsilonModel = KEpsilonModel.byIndex(self._ui.kEpsilonRadioGroup.checkedId())
                if kEpsilonModel == KEpsilonModel.REALIZABLE:
                    nearWallTreatment = NearWallTreatment.byIndex(self._ui.nearWallTreatmentRadioGroup.checkedId())
                    if nearWallTreatment == NearWallTreatment.ENHANCED_WALL_TREATMENT:
                        return True
        except KeyError:
            pass  # "checkedId()" can be "-1" during loading

        return False
