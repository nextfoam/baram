#!/usr/bin/env python
# -*- coding: utf-8 -*-


import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.libbaram.collateral_fields import calculateCollateralField
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.base.field import AGE, HEAT_TRANSFER_COEFF, MACH_NUMBER, Q, TOTAL_PRESSURE, VORTICITY, WALL_HEAT_FLUX, WALL_SHEAR_STRESS, WALL_Y_PLUS
from baramFlow.openfoam.file_system import FileSystem


from .collateral_fields_report_dialog_ui import Ui_CollateralFieldsReportDialog


class CollateralFieldsReportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_CollateralFieldsReportDialog()
        self._ui.setupUi(self)

        self._progressDialog = None

        isDensityBased = GeneralDB.isDensityBased()
        isEnergeOn = ModelsDB.isEnergyModelOn()

        self._ui.age.setEnabled(not GeneralDB.isTimeTransient() and not isDensityBased)
        self._ui.heatTransferCoefficient.setEnabled(isEnergeOn)
        self._ui.wallHeatFlux.setEnabled(isEnergeOn)
        self._ui.machNumber.setEnabled(isEnergeOn and not isDensityBased)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.compute.clicked.connect(self._compute)

    @qasync.asyncSlot()
    async def _compute(self):
        fields = []

        if self._ui.heatTransferCoefficient.isChecked():
            fields.append(HEAT_TRANSFER_COEFF)

        if self._ui.wallHeatFlux.isChecked():
            fields.append(WALL_HEAT_FLUX)

        if self._ui.age.isChecked():
            fields.append(AGE)

        if self._ui.machNumber.isChecked():
            fields.append(MACH_NUMBER)

        if self._ui.q.isChecked():
            fields.append(Q)

        if self._ui.totalPressure.isChecked():
            fields.append(TOTAL_PRESSURE)

        if self._ui.vorticity.isChecked():
            fields.append(VORTICITY)

        if self._ui.wallShearStress.isChecked():
            fields.append(WALL_SHEAR_STRESS)

        if self._ui.wallYPlus.isChecked():
            fields.append(WALL_Y_PLUS)

        if len(fields) == 0:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Fields.'))
            return

        self._progressDialog = ProgressDialog(self, self.tr('Collateral Fields Calculation'))
        self._progressDialog.setLabelText(self.tr('Calculating Collateral Fields'))
        self._progressDialog.open()

        if GeneralDB.isTimeTransient():
            rc = await calculateCollateralField(fields)
        else:
            rc = await calculateCollateralField(fields, [FileSystem.latestTime()])

        if rc != 0:
            self._progressDialog.finish(self.tr('Computing failed'))
        elif GeneralDB.isTimeTransient():
            self._progressDialog.finish(self.tr('Collateral Fields hava been written into time folders!'))
        else:
            self._progressDialog.finish(self.tr('Collateral Fields hava been written into the last time folder!'))
