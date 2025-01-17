#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType
from libbaram.run import runParallelUtility
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects.collateral_fields import foAgeReport, foHeatTransferCoefficientReport
from baramFlow.openfoam.function_objects.collateral_fields import foMachNumberReport, foQReport
from baramFlow.openfoam.function_objects.collateral_fields import foTotalPressureReport, foVorticityReport
from baramFlow.openfoam.function_objects.collateral_fields import foWallHeatFluxReport, foWallShearStressReport
from baramFlow.openfoam.function_objects.collateral_fields import foWallYPlusReport
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.solver import findSolver

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
        self._ui.machNumber.setEnabled(isEnergeOn and not isDensityBased)

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.compute.clicked.connect(self._compute)

    @qasync.asyncSlot()
    async def _compute(self):
        functions = {}
        
        if self._ui.age.isChecked():
            functions['collateralAge'] = foAgeReport()

        for rname in coredb.CoreDB().getRegions():
            if self._ui.heatTransferCoefficient.isChecked():
                functions['collateralHeatTransferCoefficient_' + rname] = foHeatTransferCoefficientReport(
                    [bcname for bcid, bcname in BoundaryDB.getBoundaryConditionsByType(BoundaryType.WALL, rname)])

        if self._ui.machNumber.isChecked():
            functions['collateralMachNumber'] = foMachNumberReport()

        if self._ui.q.isChecked():
            functions['collateralQ'] = foQReport()

        if self._ui.totalPressure.isChecked():
            functions['collateralTotalPressure'] = foTotalPressureReport()

        if self._ui.vorticity.isChecked():
            functions['collateralVorticity'] = foVorticityReport()

        if self._ui.wallHeatFlux.isChecked():
            functions['collateralWallHeatFlux'] = foWallHeatFluxReport()

        if self._ui.wallShearStress.isChecked():
            functions['collateralWallShearStress'] = foWallShearStressReport()

        if self._ui.wallYPlus.isChecked():
            functions['collateralWallYPlus'] = foWallYPlusReport()

        if not functions:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Fields.'))
            return

        self._progressDialog = ProgressDialog(self, self.tr('Collateral Fields Calculation'))
        self._progressDialog.open()

        data = {
            'functions': functions
        }

        foDict = FoDict(f'delete_me_{str(uuid.uuid4())}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing
        proc = await runParallelUtility(
            solver, '-postProcess', '-latestTime', '-dict', str(dictRelativePath),
            parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        foDict.fullPath().unlink()

        if rc != 0:
            self._progressDialog.finish(self.tr('Computing failed'))
        elif GeneralDB.isTimeTransient():
            self._progressDialog.finish(self.tr('Collateral Fields hava been written into time folders!'))
        else:
            self._progressDialog.finish(self.tr('Collateral Fields hava been written into the last time folder!'))
