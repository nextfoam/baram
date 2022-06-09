#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.resizable_dialog import ResizableDialog
from .turbulence_dialog_ui import Ui_TurbulenceDialog
from .models_db import ModelsDB, TurbulenceModel, KEpsilonModel, NearWallTreatment, KOmegaModel


class TurbulenceModelDialog(ResizableDialog):
    def __init__(self):
        super().__init__()
        self._ui = Ui_TurbulenceDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()
        self._xpath = ModelsDB.TURBULENCE_MODELS_PATH

        self._modelRadios = {
            self._ui.modelRadioGroup.id(self._ui.laminar): TurbulenceModel.LAMINAR.value,
            self._ui.modelRadioGroup.id(self._ui.spalartAllmaras): TurbulenceModel.SPALART_ALLMARAS.value,
            self._ui.modelRadioGroup.id(self._ui.kEpsilon): TurbulenceModel.K_EPSILON.value,
            self._ui.modelRadioGroup.id(self._ui.kOmega): TurbulenceModel.K_OMEGA.value,
            self._ui.modelRadioGroup.id(self._ui.LES): TurbulenceModel.LES.value,
        }

        self._kEpsilonModelRadios = {
            self._ui.kEpsilonRadioGroup.id(self._ui.standard): KEpsilonModel.STANDARD.value,
            self._ui.kEpsilonRadioGroup.id(self._ui.RNG): KEpsilonModel.RNG.value,
            self._ui.kEpsilonRadioGroup.id(self._ui.realizable): KEpsilonModel.REALIZABLE.value,
        }

        self._nearWallTreatmentRadios = {
            self._ui.nearWallTreatmentRadioGroup.id(self._ui.standardWallFunction):
                NearWallTreatment.STANDARD_WALL_FUNCTIONS.value,
            self._ui.nearWallTreatmentRadioGroup.id(self._ui.enhancedWallTreatment):
                NearWallTreatment.ENHANCED_WALL_TREATMENT.value,
        }

        self._connectSignalsSlots()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        self._getRadio(
            self._ui.modelRadioGroup, self._modelRadios, self._db.getValue(self._xpath + '/model')
        ).setChecked(True)

        self._getRadio(
            self._ui.kEpsilonRadioGroup, self._kEpsilonModelRadios, self._db.getValue(self._xpath + '/k-epsilon/model')
        ).setChecked(True)

        self._getRadio(
            self._ui.nearWallTreatmentRadioGroup, self._nearWallTreatmentRadios,
            self._db.getValue(self._xpath + '/k-epsilon/realizable/nearWallTreatment')
        ).setChecked(True)

        self._ui.SST.setChecked(True)

        return super().showEvent(ev)

    def accept(self):
        writer = CoreDBWriter()

        model = self._getRadioValue(self._ui.modelRadioGroup, self._modelRadios)
        writer.append(self._xpath + '/model', model, None)

        if model == TurbulenceModel.K_EPSILON.value:
            kEpsilonModel = self._getRadioValue(self._ui.kEpsilonRadioGroup, self._kEpsilonModelRadios)
            writer.append(self._xpath + '/k-epsilon/model', kEpsilonModel, None)

            if kEpsilonModel == KEpsilonModel.REALIZABLE.value:
                writer.append(self._xpath + '/k-epsilon/realizable/nearWallTreatment',
                              self._getRadioValue(self._ui.nearWallTreatmentRadioGroup, self._nearWallTreatmentRadios),
                              None)
        elif model == TurbulenceModel.K_OMEGA.value:
            writer.append(self._xpath + '/k-omega/model', KOmegaModel.SST.value, None)

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.close()

    def _connectSignalsSlots(self):
        self._ui.modelRadioGroup.idToggled.connect(self._modelChanged)
        self._ui.kEpsilonRadioGroup.idToggled.connect(self._kEpsilonModelChanged)

    def _modelChanged(self, id_, checked):
        if checked:
            self._ui.kEpsilonModel.setVisible(self._ui.kEpsilon.isChecked())
            self._ui.kOmegaModel.setVisible(self._ui.kOmega.isChecked())

    def _kEpsilonModelChanged(self, id_, checked):
        if checked:
            self._ui.nearWallTreatment.setVisible(self._ui.realizable.isChecked())

    def _getRadio(self, group, radios, value):
        return group.button(list(radios.keys())[list(radios.values()).index(value)])

    def _getRadioValue(self, group, radios):
        return radios[group.id(group.checkedButton())]
