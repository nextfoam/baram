#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from coredb import coredb
from openfoam.dictionary_file import DictionaryFile, DataClass
from openfoam.constant.boundary_data import BoundaryData


class BoundaryCondition(DictionaryFile):
    class TableType(Enum):
        POLYNOMIAL = auto()
        TEMPORAL_SCALAR_LIST = auto()
        TEMPORAL_VECTOR_LIST = auto()

    def __init__(self, location, field, class_=DataClass.CLASS_VOL_SCALAR_FIELD):
        super().__init__(location, field, class_)

        self._db = coredb.CoreDB()

    def _constructCalculated(self, value):
        return {
            'type': 'calculated',
            'value': ('uniform', value)
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

    def _constructFarfieldRiemann(self, xpath):
        return {
            'type': 'farfieldRiemann',
            'flowDir': self._db.getVector(xpath + '/flowDirection'),
            'MInf': self._db.getValue(xpath + '/machNumber'),
            'pInf': self._db.getValue(xpath + '/staticPressure'),
            'TInf': self._db.getValue(xpath + '/staticTemperature'),
        }

    def _constructSubsonicInflow(self, xpath):
        return {
            'type': 'subsonicInflow',
            'flowDir': self._db.getVector(xpath + '/flowDirection'),
            'p0': self._db.getValue(xpath + '/totalPressure'),
            'T0': self._db.getValue(xpath + '/totalTemperature'),
        }

    def _constructSubsonicOutflow(self, xpath):
        return {
            'type': 'subsonicOutflow',
            'pExit': self._db.getValue(xpath + '/staticPressure'),
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
        BoundaryData.write(rname, bname, field, data)

        return {
            'type': 'timeVaryingMappedFixedValue'
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
                'uniformValue': ('table', [[t[i], v[i]] for i in range(len(t))])
            }
        elif type_ == self.TableType.TEMPORAL_VECTOR_LIST:
            t = self._db.getValue(xpath + '/t').split()
            x = self._db.getValue(xpath + '/x').split()
            y = self._db.getValue(xpath + '/y').split()
            z = self._db.getValue(xpath + '/z').split()

            return {
                'type': 'uniformFixedValue',
                'uniformValue': ('table', [[t[i], [x[i], y[i], z[i]]] for i in range(len(t))])
            }

    def _constructUniformNormalFixedValue(self, xpath, type_):
        value = None

        if type_ == self.TableType.TEMPORAL_SCALAR_LIST:
            t = self._db.getValue(xpath + '/t').split()
            v = self._db.getValue(xpath + '/v').split()

            value = [[t[i], -float(v[i])] for i in range(len(t))]
        elif type_ == self.TableType.TEMPORAL_VECTOR_LIST:
            pass

        return {
            'type': 'uniformNormalFixedValue',
            'uniformValue': ('table', value)
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

    def _constructPorousBafflePressure(self, xpath):
        return {
            'type': 'porousBafflePressure',
            'patchType': 'cyclic',
            'D': self._db.getValue(xpath + '/darcyCoefficient'),
            'I': self._db.getValue(xpath + '/inertialCoefficient'),
            'length': self._db.getValue(xpath + '/porousMediaThickness'),
        }

    def _constructFreestream(self, xpath):
        return {
            'type': 'freestream',
            'freestreamValue': ('uniform', self._db.getVector(xpath + '/streamVelocity'))
        }

    def _constructInletOutlet(self, inletValue, value):
        return {
            'type': 'inletOutlet',
            'inletValue': ('uniform', inletValue),
            'value': ('uniform', value)
        }

    def _constructNEXTViscosityRatioInletOutletTDR(self, viscosityRatio):
        return {
            'type': 'NEXT::viscosityRatioInletOutletTDR',
            'viscosityRatio': viscosityRatio
        }
