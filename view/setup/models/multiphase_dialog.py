#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QMessageBox

from coredb import coredb
from coredb.coredb_writer import CoreDBWriter
from view.widgets.resizable_dialog import ResizableDialog
from .multiphase_dialog_ui import Ui_MultiphaseDialog
from .models_db import ModelsDB, MultiphaseModel


class ModelId(Enum):
    OFF = auto()
    VOLUME_OF_FLUID = auto()
    MIXTURE = auto()


class MultiphaseModelDialog(ResizableDialog):
    models = {
        ModelId.OFF.value:             MultiphaseModel.OFF,
        ModelId.VOLUME_OF_FLUID.value: MultiphaseModel.VOLUME_OF_FLUID,
    }

    def __init__(self):
        super().__init__()
        self._ui = Ui_MultiphaseDialog()
        self._ui.setupUi(self)

        self._db = coredb.CoreDB()

        self._ui.volumeOfFluid.hide()
        self._ui.mixture.hide()

    def showEvent(self, ev):
        if ev.spontaneous():
            return super().showEvent(ev)

        xpath = ModelsDB.MULTIPHASE_MODELS_PATH
        self._setModel(ModelsDB.getMultiphaseModel(self._db.getValue(xpath + '/model')))

        return super().showEvent(ev)

    def accept(self):
        xpath = ModelsDB.MULTIPHASE_MODELS_PATH
        writer = CoreDBWriter()
        writer.append(xpath + '/model',
                      self.models[self._ui.modelRadioGroup.id(self._ui.modelRadioGroup.checkedButton())].value,
                      self.tr("Model"))

        errorCount = writer.write()
        if errorCount > 0:
            QMessageBox.critical(self, self.tr("Input Error"), writer.firstError().toMessage())
        else:
            self.close()

    def _setModel(self, model):
        self._setupRadioGroup(self._ui.off, ModelId.OFF.value, model)
        self._setupRadioGroup(self._ui.volumeOfFluid, ModelId.VOLUME_OF_FLUID.value, model)
        # self._setRadioId(self._ui.mixture, Model.MIXTURE.value, model)

    def _setupRadioGroup(self, button, id_, model):
        self._ui.modelRadioGroup.setId(button, id_)
        if self.models[id_] == model:
            button.setChecked(True)
