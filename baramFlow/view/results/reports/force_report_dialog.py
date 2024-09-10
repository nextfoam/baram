#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import uuid

import qasync

from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QDialog

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.monitor_db import DirectionSpecificationMethod
from baramFlow.coredb.reference_values_db import ReferenceValuesDB
from baramFlow.openfoam import parallel
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.function_objects import FoDict
from baramFlow.openfoam.function_objects.force_coeffs import foForceCoeffsReport
from baramFlow.openfoam.function_objects.forces import foForcesReport
from baramFlow.openfoam.post_processing.post_file_reader import readPostFile
from baramFlow.openfoam.solver import findSolver
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector

from libbaram import utils
from libbaram.math import calucateDirectionsByRotation
from libbaram.run import runParallelUtility
from widgets.async_message_box import AsyncMessageBox

from .force_report_dialog_ui import Ui_ForceReportDialog


class ForceReportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_ForceReportDialog()
        self._ui.setupUi(self)

        self._rname = None
        self._boundaries = None

        self._db = coredb.CoreDB()

        self._ui.specificationMethod.addEnumItems({
            DirectionSpecificationMethod.DIRECT: self.tr('Direct'),
            DirectionSpecificationMethod.AOA_AOS: self.tr('AOA and AOS')
        })

        self._setupValidators()

        self._setBoundaries([])

        self._connectSignalsSlots()

        self._ui.specificationMethod.setCurrentData(DirectionSpecificationMethod.DIRECT)

    def _connectSignalsSlots(self):
        self._ui.specificationMethod.currentDataChanged.connect(self._specificationMethodChanged)
        self._ui.select.clicked.connect(self._selectBoundaries)
        self._ui.compute.clicked.connect(self._compute)
        self._ui.close.clicked.connect(self.close)

    def _setupValidators(self):
        self._ui.dragDirectionX.setValidator(QDoubleValidator())
        self._ui.dragDirectionY.setValidator(QDoubleValidator())
        self._ui.dragDirectionZ.setValidator(QDoubleValidator())

        self._ui.liftDirectionX.setValidator(QDoubleValidator())
        self._ui.liftDirectionY.setValidator(QDoubleValidator())
        self._ui.liftDirectionZ.setValidator(QDoubleValidator())

        self._ui.AoA.setValidator(QDoubleValidator(-90, 90, 1000))
        self._ui.AoS.setValidator(QDoubleValidator(-90., 90, 1000))

        self._ui.centerOfRotationX.setValidator(QDoubleValidator())
        self._ui.centerOfRotationY.setValidator(QDoubleValidator())
        self._ui.centerOfRotationZ.setValidator(QDoubleValidator())

    def _setBoundaries(self, boundaries):
        self._boundaries = boundaries

        self._ui.boundaries.clear()
        for bcid in boundaries:
            self._ui.boundaries.addItem(BoundaryDB.getBoundaryText(bcid))

    def _selectBoundaries(self):
        self._dialog = BoundariesSelector(self, self._boundaries)
        self._dialog.accepted.connect(self._boundariesChanged)
        self._dialog.open()

    def _boundariesChanged(self):
        self._rname = self._dialog.region()
        self._setBoundaries(self._dialog.selectedItems())

    def _specificationMethodChanged(self, method):
        if method == DirectionSpecificationMethod.DIRECT:
            self._ui.direction.setTitle(self.tr('Direction'))
            self._ui.angles.hide()
        else:
            self._ui.direction.setTitle(self.tr('Direction at AOA=0, AOS=0'))
            self._ui.angles.show()

    @qasync.asyncSlot()
    async def _compute(self):
        if not self._boundaries:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Select Boundaries'))
            return

        self._ui.compute.setEnabled(False)

        self._ui.drag.setText('Calculating...')
        self._ui.lift.setText('Calculating...')
        self._ui.moment.setText('Calculating...')
        self._ui.total_force_x.setText('Calculating...')
        self._ui.total_force_y.setText('Calculating...')
        self._ui.total_force_z.setText('Calculating...')
        self._ui.pressure_force_x.setText('Calculating...')
        self._ui.pressure_force_y.setText('Calculating...')
        self._ui.pressure_force_z.setText('Calculating...')
        self._ui.viscous_force_x.setText('Calculating...')
        self._ui.viscous_force_y.setText('Calculating...')
        self._ui.viscous_force_z.setText('Calculating...')
        self._ui.total_moment_x.setText('Calculating...')
        self._ui.total_moment_y.setText('Calculating...')
        self._ui.total_moment_z.setText('Calculating...')
        self._ui.pressure_moment_x.setText('Calculating...')
        self._ui.pressure_moment_y.setText('Calculating...')
        self._ui.pressure_moment_z.setText('Calculating...')
        self._ui.viscous_moment_x.setText('Calculating...')
        self._ui.viscous_moment_y.setText('Calculating...')
        self._ui.viscous_moment_z.setText('Calculating...')

        seed = str(uuid.uuid4())

        forceFoName = f'delete_me_{seed}_force'
        coeffsFoName = f'delete_me_{seed}_coeffs'

        data = {
            'functions': {
                forceFoName: self._generateForces(),
                coeffsFoName: self._generateForceCoeffs()
            }
        }

        foDict = FoDict(f'delete_me_{seed}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        dictRelativePath = Path(os.path.relpath(foDict.fullPath(),
                                                caseRoot)).as_posix()  # "as_posix()": OpenFOAM cannot handle double backward slash separators in parallel processing
        proc = await runParallelUtility(solver, '-postProcess', '-latestTime', '-dict', str(dictRelativePath),
                                        parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        foDict.fullPath().unlink()

        if rc != 0:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.drag.setText('0')
            self._ui.lift.setText('0')
            self._ui.moment.setText('0')
            self._ui.compute.setEnabled(True)
            return

        forcePath = FileSystem.postProcessingPath(self._rname) / forceFoName
        coeffsPath = FileSystem.postProcessingPath(self._rname) / coeffsFoName

        forceFiles: list[Path] = list(forcePath.glob('**/force.dat'))
        coeffsFiles: list[Path] = list(coeffsPath.glob('**/coefficient.dat'))
        momentFiles: list[Path] = list(forcePath.glob('**/moment.dat'))

        if len(coeffsFiles) < 1 or len(forceFiles) < 1:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))

            self._ui.drag.setText('0')
            self._ui.lift.setText('0')
            self._ui.moment.setText('0')
            self._ui.total_force_x.setText('0')
            self._ui.total_force_y.setText('0')
            self._ui.total_force_z.setText('0')
            self._ui.pressure_force_x.setText('0')
            self._ui.pressure_force_y.setText('0')
            self._ui.pressure_force_z.setText('0')
            self._ui.viscous_force_x.setText('0')
            self._ui.viscous_force_y.setText('0')
            self._ui.viscous_force_z.setText('0')
            self._ui.total_moment_x.setText('0')
            self._ui.total_moment_y.setText('0')
            self._ui.total_moment_z.setText('0')
            self._ui.pressure_moment_x.setText('0')
            self._ui.pressure_moment_y.setText('0')
            self._ui.pressure_moment_z.setText('0')
            self._ui.viscous_moment_x.setText('0')
            self._ui.viscous_moment_y.setText('0')
            self._ui.viscous_moment_z.setText('0')

            self._ui.compute.setEnabled(True)

            return

        df = readPostFile(coeffsFiles[0])

        self._ui.drag.setText(str(df['Cd'].iloc[0]))
        self._ui.lift.setText(str(df['Cl'].iloc[0]))
        self._ui.moment.setText(str(df['CmPitch'].iloc[0]))

        df = readPostFile(forceFiles[0])

        self._ui.total_force_x.setText(str(df['total_x'].iloc[0]))
        self._ui.total_force_y.setText(str(df['total_y'].iloc[0]))
        self._ui.total_force_z.setText(str(df['total_z'].iloc[0]))
        self._ui.pressure_force_x.setText(str(df['pressure_x'].iloc[0]))
        self._ui.pressure_force_y.setText(str(df['pressure_y'].iloc[0]))
        self._ui.pressure_force_z.setText(str(df['pressure_z'].iloc[0]))
        self._ui.viscous_force_x.setText(str(df['viscous_x'].iloc[0]))
        self._ui.viscous_force_y.setText(str(df['viscous_y'].iloc[0]))
        self._ui.viscous_force_z.setText(str(df['viscous_z'].iloc[0]))

        df = readPostFile(momentFiles[0])

        self._ui.total_moment_x.setText(str(df['total_x'].iloc[0]))
        self._ui.total_moment_y.setText(str(df['total_y'].iloc[0]))
        self._ui.total_moment_z.setText(str(df['total_z'].iloc[0]))
        self._ui.pressure_moment_x.setText(str(df['pressure_x'].iloc[0]))
        self._ui.pressure_moment_y.setText(str(df['pressure_y'].iloc[0]))
        self._ui.pressure_moment_z.setText(str(df['pressure_z'].iloc[0]))
        self._ui.viscous_moment_x.setText(str(df['viscous_x'].iloc[0]))
        self._ui.viscous_moment_y.setText(str(df['viscous_y'].iloc[0]))
        self._ui.viscous_moment_z.setText(str(df['viscous_z'].iloc[0]))

        utils.rmtree(forcePath)
        utils.rmtree(coeffsPath)

        self._ui.compute.setEnabled(True)

    def _generateForces(self):
        boundaries = []

        for bcid in self._boundaries:
            boundaries.append(BoundaryDB.getBoundaryText(bcid))

        cofr = [float(self._ui.centerOfRotationX.text()),
                float(self._ui.centerOfRotationY.text()),
                float(self._ui.centerOfRotationZ.text())]

        data = foForcesReport(boundaries, cofr, self._rname)

        return data

    def _generateForceCoeffs(self):
        boundaries = []
        for bcid in self._boundaries:
            boundaries.append(BoundaryDB.getBoundaryName(bcid))

        aRef = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'))
        lRef = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'))
        magUInf = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'))
        rhoInf = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'))
        dragDir = [float(self._ui.dragDirectionX.text()),
                   float(self._ui.dragDirectionY.text()),
                   float(self._ui.dragDirectionZ.text())]
        liftDir = [float(self._ui.liftDirectionX.text()),
                   float(self._ui.liftDirectionY.text()),
                   float(self._ui.liftDirectionZ.text())]
        cofr = [float(self._ui.centerOfRotationX.text()),
                float(self._ui.centerOfRotationY.text()),
                float(self._ui.centerOfRotationZ.text())]

        if self._ui.specificationMethod.currentData() == DirectionSpecificationMethod.AOA_AOS:
            dragDir, liftDir = calucateDirectionsByRotation(
                dragDir, liftDir,
                float(self._ui.AoA.text()),
                float(self._ui.AoS.text()))

        if GeneralDB.isDensityBased():
            pRef = None
        else:
            referencePressure = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
            operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
            pRef = referencePressure + operatingPressure

        data = foForceCoeffsReport(boundaries, aRef, lRef, magUInf, rhoInf, dragDir, liftDir, cofr, pRef, self._rname)

        return data
