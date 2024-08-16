#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from math import sqrt
import logging

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

from libbaram.math import calucateDirectionsByRotation
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile, DataClass

from baramFlow.coredb.boundary_db import DirectionSpecificationMethod
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.material_db import UNIVERSAL_GAS_CONSTANT, MaterialDB
from baramFlow.coredb.turbulence_model_db import TurbulenceModel
from baramFlow.openfoam.constant.boundary_data import BoundaryData
from baramFlow.openfoam.file_system import FileSystem

logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)


class BoundaryCondition(DictionaryFile):
    class TableType(Enum):
        POLYNOMIAL = auto()
        TEMPORAL_SCALAR_LIST = auto()
        TEMPORAL_VECTOR_LIST = auto()

    def __init__(self, region, time, processorNo, field, class_=DataClass.CLASS_VOL_SCALAR_FIELD):
        super().__init__(FileSystem.caseRoot(), self.boundaryLocation(region.rname, time), field, class_)

        self._initialValue = None
        self._region = region
        self._time = time
        self._processorNo = processorNo
        self._fieldsData = None
        self._db = CoreDBReader()

    def build0(self):
        raise AssertionError  # This method should be overwritten by descendants

    def build(self):
        self.build0()
        if not self._data:
            self._fieldsData = None
            return self

        path = self.fullPath(self._processorNo)
        if path.is_file():
            self._fieldsData = ParsedParameterFile(str(path), debug=None)

            for name, builded in self._data['boundaryField'].items():
                loaded = self._fieldsData.content['boundaryField'][name]
                if loaded['type'] == builded['type'] == 'fixedValue' and not loaded['value'].isUniform():
                    builded['value'] = None

                loaded.update({k: v for k, v in builded.items() if v is not None})

        return self

    def fullPath(self, processorNo=None):
        # Boundary Conditions reside in Field Data Files
        # Field Data Files are reconstructed, updated, and decomposed in sequence
        # so that no need to handle the data under processors folders
        timeDirPath = FileSystem.caseRoot() / self._header['location']
        boundaryFilePath = timeDirPath / self._header['object']
        boundaryFieldsPath = timeDirPath / 'boundaryFields' / self._header['object']

        return boundaryFieldsPath if boundaryFieldsPath.exists() else boundaryFilePath

    def write(self):
        if self._fieldsData:
            self._fieldsData.writeFile()
        elif self._data:
            self._write(self._processorNo)

    def _initialValueByTime(self):
        path = self.fullPath(self._processorNo)
        if self._time == '0' or not path.is_file():
            return 'uniform', self._initialValue
        else:
            return None

    def _constructCalculated(self):
        return {
            'type': 'calculated',
            'value': self._initialValueByTime()
        }

    def _constructZeroGradient(self):
        return {
            'type': 'zeroGradient'
        }

    def _constructFixedValue(self, value):
        return {
            'type': 'fixedValue',
            'value': ('uniform', value)
        }

    def _constructFarfieldRiemann(self, xpath, value):
        return {
            'type': 'farfieldRiemann',
            'flowDir': self._calculateFarfiledRiemanFlowDirection(xpath + '/flowDirection'),
            'MInf': self._db.getValue(xpath + '/machNumber'),
            'pInf': self._db.getValue(xpath + '/staticPressure'),
            'TInf': self._db.getValue(xpath + '/staticTemperature'),
            'value': ('uniform', value)
        }

    def _constructSubsonicInlet(self, xpath):
        return {
            'type': 'subsonicInlet',
            'flowDir': self._db.getVector(xpath + '/flowDirection'),
            'p0': self._db.getValue(xpath + '/totalPressure'),
            'T0': self._db.getValue(xpath + '/totalTemperature'),
            'value': self._initialValueByTime()
        }

    def _constructSubsonicOutflow(self, xpath):
        return {
            'type': 'subsonicOutflow',
            'pExit': self._db.getValue(xpath + '/staticPressure'),
            'value': self._initialValueByTime()
        }

    def _constructSymmetry(self):
        return {
            'type': 'symmetry'
        }

    def _constructCyclicAMI(self):
        return {
            'type': 'cyclicAMI'
        }

    def _constructEmpty(self):
        return {
            'type': 'empty'
        }

    def _constructCyclic(self):
        return {
            'type': 'cyclic'
        }

    def _constructWedge(self):
        return {
            'type': 'wedge'
        }

    def _constructTimeVaryingMappedFixedValue(self, rname, bname, field, data):
        points = BoundaryData.write(rname, bname, field, data)

        return {
            'type': 'timeVaryingMappedFixedValue',
            'points': points
        }

    def _constructUniformFixedValue(self, xpath, type_):
        if type_ == self.TableType.POLYNOMIAL:
            v = self._db.getValue(xpath).split()

            return {
                'type': 'uniformFixedValue',
                'uniformValue': ('polynomial', [[v[i], i] for i in range(len(v))])
            }
        elif type_ == self.TableType.TEMPORAL_SCALAR_LIST:
            t = self._db.getValue(xpath + '/t').split()
            v = self._db.getValue(xpath + '/v').split()

            return {
                'type': 'uniformFixedValue',
                'uniformValue': 'table',
                'uniformValueCoeffs': {
                    'values': [[t[i], v[i]] for i in range(len(t))]
                }
            }
        elif type_ == self.TableType.TEMPORAL_VECTOR_LIST:
            t = self._db.getValue(xpath + '/t').split()
            x = self._db.getValue(xpath + '/x').split()
            y = self._db.getValue(xpath + '/y').split()
            z = self._db.getValue(xpath + '/z').split()

            return {
                'type': 'uniformFixedValue',
                'uniformValue': 'table',
                'uniformValueCoeffs': {
                    'values': [[t[i], [x[i], y[i], z[i]]] for i in range(len(t))]
                }
            }

    def _constructUniformNormalFixedValue(self, xpath, type_):
        values = None

        if type_ == self.TableType.TEMPORAL_SCALAR_LIST:
            t = self._db.getValue(xpath + '/t').split()
            v = self._db.getValue(xpath + '/v').split()

            values = [[t[i], -float(v[i])] for i in range(len(t))]
        elif type_ == self.TableType.TEMPORAL_VECTOR_LIST:
            pass

        return {
            'type': 'uniformNormalFixedValue',
            'uniformValue': 'table',
            'uniformValueCoeffs': {
                'values': values
            }
        }

    def _constructSurfaceNormalFixedValue(self, value):
        return {
            'type': 'surfaceNormalFixedValue',
            'refValue': ('uniform', -float(value))
        }

    def _construcSlip(self):
        return {
            'type': 'slip'
        }

    def _constructFreeStream(self, value):
        return {
            'type': 'freestream',
            'freestreamValue': ('uniform', value)
        }

    def _constructInletOutlet(self, inletValue):
        return {
            'type': 'inletOutlet',
            'inletValue': ('uniform', inletValue),
            'value': self._initialValueByTime()
        }

    def _constructViscosityRatioInletOutletTDR(self, viscosityRatio):
        return {
            'type': 'viscosityRatioInletOutletTDR',
            'viscosityRatio': ('uniform', viscosityRatio),
            'value': self._initialValueByTime()
        }

    def _constructWaveTransmissive(self, xpath, temperature: float):
        return {
            'type': 'waveTransmissive',
            'gamma': self._calculateGamma(
                MaterialDB.getMaterialComposition(xpath + '/species', self._region.mid), temperature)
        }

    def _calculateFreeStreamTurbulentValues(self, xpath, region, model):
        ux = float(self._db.getValue(xpath + 'freeStream/streamVelocity/x'))
        uy = float(self._db.getValue(xpath + 'freeStream/streamVelocity/y'))
        uz = float(self._db.getValue(xpath + 'freeStream/streamVelocity/z'))

        v = sqrt(ux**2 + uy**2 + uz**2)

        p = float(self._db.getValue(xpath + '/freeStream/pressure'))
        t = float(self._db.getValue(xpath + '/temperature/constant'))

        if model == TurbulenceModel.K_EPSILON:
            i = float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity')) / 100
            b = float(self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))
        elif model == TurbulenceModel.K_OMEGA:
            i = float(self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity')) / 100
            b = float(self._db.getValue(xpath + '/turbulence/k-omega/turbulentViscosityRatio'))
        elif model == TurbulenceModel.LES:
            i = float(self._db.getValue(xpath + '/turbulence/les/turbulentIntensity')) / 100
            b = float(self._db.getValue(xpath + '/turbulence/les/turbulentViscosityRatio'))
        else:
            raise AssertionError

        materials = MaterialDB.getMaterialComposition(xpath + '/species', region.mid)
        rho = self._db.getDensity(materials, t, p)  # Density
        mu = self._db.getViscosity(materials, t)  # Viscosity

        nu = mu / rho  # Kinetic Viscosity

        nut = b * nu

        k = 1.5 * (v*i) ** 2
        e = 0.09 * k ** 2 / nut
        w = k / nut

        return k, e, w

    def _calculateFreeStreamKE(self, xpath, region):
        k, e, w = self._calculateFreeStreamTurbulentValues(xpath, region, TurbulenceModel.K_EPSILON)
        return k, e

    def _calculateFreeStreamKW(self, xpath, region):
        k, e, w = self._calculateFreeStreamTurbulentValues(xpath, region, TurbulenceModel.K_OMEGA)
        return k, w

    def _calculateFreeStreamLES(self, xpath, region):
        k, e, w = self._calculateFreeStreamTurbulentValues(xpath, region, TurbulenceModel.LES)
        return k, w

    def _calculateFarfiledRiemanFlowDirection(self, xpath):
        drag = self._db.getVector(xpath + '/dragDirection')
        lift = self._db.getVector(xpath + '/liftDirection')
        if self._db.getValue(xpath + '/specificationMethod') == DirectionSpecificationMethod.AOA_AOS.value:
            drag, lift = calucateDirectionsByRotation(drag, lift,
                                                      float(self._db.getValue(xpath + '/angleOfAttack')),
                                                      float(self._db.getValue(xpath + '/angleOfSideslip')))

        return drag

    def _calculateGamma(self, materials, t: float):
        cp = self._db.getSpecificHeat(materials, t)
        mw = self._db.getMolecularWeight(materials)

        return cp / (cp - UNIVERSAL_GAS_CONSTANT / mw)
