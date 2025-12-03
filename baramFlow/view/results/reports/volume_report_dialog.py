#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog

from libbaram import utils
from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.run import runParallelUtility
from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog
from widgets.selector_dialog import SelectorDialog

from baramFlow.base.constants import FieldType, VectorComponent
from baramFlow.base.field import CollateralField, Field, SpecieField, UserScalarField
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.monitor_db import MonitorDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.openfoam import parallel
from baramFlow.libbaram.collateral_fields import collateralFieldDict
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.components import foComponentsReport
from baramFlow.openfoam.function_objects.mag import foMagReport
from baramFlow.openfoam.function_objects.read_fields import foReadFieldsReport
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType, VolumeType, foVolFieldValueReport
from baramFlow.openfoam.post_processing.post_file_reader import readPostFile
from baramFlow.openfoam.solver import findSolver
from baramFlow.openfoam.solver_field import getSolverComponentName, getSolverFieldName
from baramFlow.view.widgets.post_field_selector import loadFieldsComboBox, connectFieldsToComponents
from .volume_report_dialog_ui import Ui_VolumeReportDialog


class VolumeReportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_VolumeReportDialog()
        self._ui.setupUi(self)

        self._volume = None

        for t in VolumeReportType:
            self._ui.reportType.addItem(MonitorDB.volumeReportTypeToText(t), t)

        loadFieldsComboBox(self._ui.fieldVariable)

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        # self._ui.reportType.currentIndexChanged.connect(self._updateInputFields)
        self._ui.select.clicked.connect(self._selectVolumes)
        self._ui.compute.clicked.connect(self._compute)
        self._ui.close.clicked.connect(self._accept)

        connectFieldsToComponents(self._ui.fieldVariable, self._ui.fieldComponent)

    def _load(self):
        pass

    @qasync.asyncSlot()
    async def _accept(self):
        self.accept()

    @qasync.asyncSlot()
    async def _compute(self):
        self._ui.compute.setEnabled(False)

        reportType: VolumeReportType = self._ui.reportType.currentData()

        field: Field = self._ui.fieldVariable.currentData()
        fieldComponent: VectorComponent = self._ui.fieldComponent.currentData()

        if not self._volume:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Volume.'))
            self._ui.compute.setEnabled(True)
            return

        rname = CellZoneDB.getCellZoneRegion(self._volume)

        seed = uuidToNnstr(uuid.uuid4())
        foName = f'delete_me_{seed}_volume'

        functions = {}

        solverFieldName = getSolverFieldName(field)

        if isinstance(field, CollateralField):
            time = FileSystem.latestTime()
            if FileSystem.fieldExists(time, solverFieldName):
                functions[f'readField_{solverFieldName}'] = foReadFieldsReport([solverFieldName], rname)  # FO for reading the collateral field
            else:
                functions.update(collateralFieldDict([field]))  # FO for generating the collateral field

        elif isinstance(field, SpecieField):
            if field.codeName not in RegionDB.getSecondaryMaterials(rname):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the material is configured does not contain selected surface."))
                self._ui.compute.setEnabled(True)
                return

        elif isinstance(field, UserScalarField):
            if rname != UserDefinedScalarsDB.getRegion(field.codeName):
                await AsyncMessageBox().information(self, self.tr("Input Error"),
                                                    self.tr("The region where the scalar field is configured does not contain selected surface."))
                self._ui.compute.setEnabled(True)
                return

        name = CellZoneDB.getCellZoneName(self._volume)
        if CellZoneDB.isRegion(name):
            volumeType = VolumeType.All
            volumeName = None
        else:
            volumeType = VolumeType.CELLZONE
            volumeName = name

        if field.type == FieldType.SCALAR:
            functions[foName] = foVolFieldValueReport(volumeType, volumeName, solverFieldName, reportType, rname)

        else:  # FieldType.VECTOR
            if fieldComponent == VectorComponent.MAGNITUDE:
                functions['mag1'] = foMagReport(solverFieldName, rname)
            else:
                functions['components1'] = foComponentsReport(solverFieldName, rname)

            solverComponentName = getSolverComponentName(field, fieldComponent)
            functions[foName] = foVolFieldValueReport(volumeType, volumeName, solverComponentName, reportType, rname)

        self._ui.resultValue.setText('Calculating...')

        data = {
            'functions': functions
        }

        progressDialog = ProgressDialog(self, self.tr('Surface Report'), openDelay=500)
        progressDialog.setLabelText(self.tr('Generating Report...'))
        progressDialog.open()

        foDict = FoDict(f'delete_me_{seed}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing
        proc = await runParallelUtility(solver, '-postProcess', '-latestTime', '-dict', str(dictRelativePath), parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        foDict.fullPath().unlink()

        if rc != 0:
            progressDialog.abort(self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)
            return

        foPath = FileSystem.postProcessingPath(rname) / foName

        foFiles:  list[Path] = list(foPath.glob('**/volFieldValue.dat'))
        print(foPath, foFiles)

        if len(foFiles) < 1:
            progressDialog.abort(self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)

            return

        df = readPostFile(foFiles[0])

        self._ui.resultValue.setText(str(df.iloc[0, 0]))

        utils.rmtree(foPath)

        progressDialog.finish(self.tr('Calculation Completed'))

        self._ui.compute.setEnabled(True)

    def _setVolume(self, volume):
        self._volume = volume
        self._ui.volume.setText(CellZoneDB.getCellZoneText(volume))

    def _selectVolumes(self):
        self._dialog = SelectorDialog(self, self.tr("Select Cell Zone"), self.tr("Select Cell Zone"),
                                      CellZoneDB.getCellZoneSelectorItems())
        self._dialog.open()
        self._dialog.accepted.connect(self._volumeChanged)

    def _volumeChanged(self):
        self._setVolume(self._dialog.selectedItem())

