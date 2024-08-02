#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pathlib
import uuid

import pandas as pd
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
from baramFlow.openfoam.solver import findSolver
from baramFlow.view.widgets.region_objects_selector import BoundariesSelector
from libbaram import utils

from libbaram.math import calucateDirectionsByRotation
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile
from libbaram.openfoam.of_utils import openfoamLibraryPath
from libbaram.run import runParallelUtility

from widgets.async_message_box import AsyncMessageBox

from .force_report_dialog_ui import Ui_ForceReportDialog


class ForceDict(DictionaryFile):
    def __init__(self, objectName: str):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(), objectName)

        self._writeControl = 'runTime'
        self._writeInterval = None

    def build(self, data):
        self._data = data
        return self


class ForceReportDialog(QDialog):
    def __init__(self, parent, name=None):
        """Constructs force monitor setup dialog.

        Args:
            name: Force Monitor name. If None, create a new monitor.
        """
        super().__init__(parent)
        self._ui = Ui_ForceReportDialog()
        self._ui.setupUi(self)

        self._name = name
        self._rname = None
        self._boundaries = None

        self._db = coredb.CoreDB()

        self._ui.specificationMethod.addEnumItems({
            DirectionSpecificationMethod.DIRECT:    self.tr('Direct'),
            DirectionSpecificationMethod.AOA_AOS:   self.tr('Angles of Attack, Sideslip')
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
            self._ui.direction.setTitle(self.tr('Direction at AoA=0, AoS=0'))
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

        seed = str(uuid.uuid4())

        forceFoName = f'delete_me_{seed}_force'
        coeffsFoName = f'delete_me_{seed}_coeffs'

        data = {
            'functions': {
                forceFoName: self._generateForces(),
                coeffsFoName: self._generateForceCoeffs()
            }
        }

        foDict = ForceDict(f'delete_me_{seed}').build(data)
        foDict.write()

        caseRoot = FileSystem.caseRoot()
        solver = findSolver()
        proc = await runParallelUtility(solver, '-postProcess', '-latestTime', '-dict', os.path.relpath(foDict.fullPath(), caseRoot), parallel=parallel.getEnvironment(), cwd=caseRoot)

        rc = await proc.wait()

        if rc != 0:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.drag.setText('0')
            self._ui.lift.setText('0')
            self._ui.moment.setText('0')
            self._ui.compute.setEnabled(False)
            return

        forcePath = FileSystem.postProcessingPath(self._rname) / forceFoName
        coeffsPath = FileSystem.postProcessingPath(self._rname) / coeffsFoName

        files: list[pathlib.Path] = list(coeffsPath.glob('**/coefficient.dat'))

        if len(files) < 1:
            await AsyncMessageBox().warning(self, self.tr('Warning'), self.tr('Computing failed'))
            self._ui.drag.setText('0')
            self._ui.lift.setText('0')
            self._ui.moment.setText('0')
            self._ui.compute.setEnabled(False)
            return

        df = self._readDataFrame(files[0])

        self._ui.drag.setText(str(df['Cd'][0]))
        self._ui.lift.setText(str(df['Cl'][0]))
        self._ui.moment.setText(str(df['CmPitch'][0]))

        foDict.fullPath().unlink()
        utils.rmtree(forcePath)
        utils.rmtree(coeffsPath)

        self._ui.compute.setEnabled(True)

    def _generateForces(self):
        boundaries = []

        for bcid in self._boundaries:
            boundaries.append(BoundaryDB.getBoundaryText(bcid))

        data = {
            'type': 'forces',
            'libs': [openfoamLibraryPath('libforces')],

            'patches': boundaries,
            'CofR': [float(self._ui.centerOfRotationX.text()), float(self._ui.centerOfRotationY.text()), float(self._ui.centerOfRotationZ.text())],

            'executeControl': 'onEnd',
            'writeControl': 'onEnd',
            'updateHeader': 'false',
            'log': 'false',
        }

        if self._rname:
            data['region'] = self._rname

        return data

    def _generateForceCoeffs(self):
        drag = [float(self._ui.dragDirectionX.text()), float(self._ui.dragDirectionY.text()), float(self._ui.dragDirectionZ.text())]
        lift = [float(self._ui.liftDirectionX.text()), float(self._ui.liftDirectionY.text()), float(self._ui.liftDirectionZ.text())]
        if self._ui.specificationMethod.currentData() == DirectionSpecificationMethod.AOA_AOS.value:
            drag, lift = calucateDirectionsByRotation(
                drag, lift,
                float(self._ui.AoA),
                float(self._ui.AoS))

        boundaries = []

        for bcid in self._boundaries:
            boundaries.append(BoundaryDB.getBoundaryText(bcid))

        data = {
            'type': 'forceCoeffs',
            'libs': [openfoamLibraryPath('libforces')],

            'patches': boundaries,
            'coefficients': ['Cd', 'Cl', 'CmPitch'],
            'rho': 'rho',
            'Aref': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/area'),
            'lRef': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/length'),
            'magUInf':  self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/velocity'),
            'rhoInf': self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/density'),
            'dragDir': drag,
            'liftDir': lift,
            'CofR': [float(self._ui.centerOfRotationX.text()), float(self._ui.centerOfRotationY.text()), float(self._ui.centerOfRotationZ.text())],

            'executeControl': 'onEnd',
            'writeControl': 'onEnd',
            'updateHeader': 'false',
            'log': 'false',
        }

        if not GeneralDB.isDensityBased():
            referencePressure = float(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'))
            operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
            data['pRef'] = referencePressure + operatingPressure

        if self._rname:
            data['region'] = self._rname

        return data

    def _readDataFrame(self, path):
        with path.open(mode='r') as f:
            header = None
            line = f.readline()
            while line[0] == '#':
                p = f.tell()
                header = line
                line = f.readline()

            names = header[1:].split()  # read header
            if names[0] != 'Time':
                raise RuntimeError
            if len(names) == 1:
                names.append(path.stem)

            f.seek(p)
            df = pd.read_csv(f, sep=r'\s+', names=names, skiprows=0)
            # df.set_index('Time', inplace=True)

            return df

