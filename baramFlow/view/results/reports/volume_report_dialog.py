#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path

import qasync
from PySide6.QtWidgets import QDialog

from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.material_schema import MaterialType
from baramFlow.coredb.monitor_db import MonitorDB, FieldHelper, Field
from baramFlow.coredb.region_db import RegionDB
from baramFlow.coredb.scalar_model_db import UserDefinedScalarsDB
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.components import foComponentsReport
from baramFlow.openfoam.function_objects.mag import foMagReport
from baramFlow.openfoam.function_objects.vol_field_value import VolumeReportType, VolumeType, \
    foVolFieldValueReport
from baramFlow.openfoam.post_processing.post_file_reader import readPostFile
from baramFlow.openfoam.solver import findSolver

from libbaram import utils
from libbaram.run import runParallelUtility
from widgets.async_message_box import AsyncMessageBox
from widgets.selector_dialog import SelectorDialog

from .volume_report_dialog_ui import Ui_VolumeReportDialog


class VolumeReportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_VolumeReportDialog()
        self._ui.setupUi(self)

        self._volume = None

        for t in VolumeReportType:
            self._ui.reportType.addEnumItem(t, MonitorDB.volumeReportTypeToText(t))

        for f in FieldHelper.getAvailableFields():
            self._ui.fieldVariable.addItem(f.text, f.key)

        self._connectSignalsSlots()

        self._load()

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._selectVolumes)
        self._ui.compute.clicked.connect(self._compute)
        self._ui.close.clicked.connect(self._accept)

    def _load(self):
        pass

    @qasync.asyncSlot()
    async def _accept(self):
        self.accept()

    @qasync.asyncSlot()
    async def _compute(self):
        if not self._volume:
            await AsyncMessageBox().information(self, self.tr('Input Error'), self.tr('Select Volume.'))
            return

        fieldKey: FieldHelper.FieldItem.DBFieldKey = self._ui.fieldVariable.currentData()
        fieldType = fieldKey.field
        fieldID = fieldKey.id

        rname = CellZoneDB.getCellZoneRegion(self._volume)
        if (fieldType == Field.SCALAR
                and rname != UserDefinedScalarsDB.getRegion(fieldID)):
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('The region where the scalar field is configured does not contain selected Volume.'))
            return

        reportType = self._ui.reportType.currentData()

        primary = RegionDB.getMaterial(rname)
        if fieldType == Field.MATERIAL:
            mid = fieldID
            if MaterialDB.getType(mid) == MaterialType.SPECIE:
                if mid not in MaterialDB.getSpecies(primary):
                    await AsyncMessageBox().information(
                        self, self.tr('Input Error'),
                        self.tr('The region where the specie is configured does not contain selected Point.'))
                    return
            elif mid != primary and mid not in RegionDB.getSecondaryMaterials(rname):
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'),
                    self.tr('The region where the material is configured does not contain selected Point.'))
                return

        field = FieldHelper.DBFieldKeyToField(fieldType, fieldID)

        self._ui.compute.setEnabled(False)

        self._ui.resultValue.setText('Calculating...')

        seed = str(uuid.uuid4())

        foName = f'delete_me_{seed}_volume'

        functions = {}

        if field == 'mag(U)':
            functions['mag1'] = foMagReport('U')
        elif field in ('Ux', 'Uy', 'Uz'):
            functions['components1'] = foComponentsReport('U')

        name = CellZoneDB.getCellZoneName(self._volume)
        if CellZoneDB.isRegion(name):
            volumeType = VolumeType.All
            volumeName = None
        else:
            volumeType = VolumeType.CELLZONE
            volumeName = name

        functions[foName] = foVolFieldValueReport(volumeType, volumeName, field, reportType, rname)

        data = {
            'functions': functions
        }

        foDict = FoDict(f'delete_me_{seed}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(), caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing
        proc = await runParallelUtility(solver, '-postProcess', '-latestTime', '-dict', str(dictRelativePath), parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        foDict.fullPath().unlink()

        if rc != 0:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)
            return

        foPath = FileSystem.postProcessingPath(rname) / foName

        foFiles:  list[Path] = list(foPath.glob('**/volFieldValue.dat'))

        if len(foFiles) < 1:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.resultValue.setText('0')
            self._ui.compute.setEnabled(True)

            return

        df = readPostFile(foFiles[0])

        self._ui.resultValue.setText(str(df.iloc[0, 0]))

        utils.rmtree(foPath)

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

