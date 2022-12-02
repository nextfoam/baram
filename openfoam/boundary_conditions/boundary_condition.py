#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto
from math import sqrt

from coredb import coredb
from coredb.material_db import MaterialDB
from coredb.models_db import TurbulenceModel
from coredb.region_db import RegionDB
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

    def _constructPorousBafflePressure(self, xpath, value):
        return {
            'type': 'porousBafflePressure',
            'patchType': 'cyclic',
            'D': self._db.getValue(xpath + '/darcyCoefficient'),
            'I': self._db.getValue(xpath + '/inertialCoefficient'),
            'length': self._db.getValue(xpath + '/porousMediaThickness'),
            'value': ('uniform', value)
        }

    def _constructFreestream(self, value):
        return {
            'type': 'freestream',
            'freestreamValue': ('uniform', value)
        }

    def _constructInletOutlet(self, inletValue, value):
        return {
            'type': 'inletOutlet',
            'inletValue': ('uniform', inletValue),
            'value': ('uniform', value)
        }

    def _constructNEXTViscosityRatioInletOutletTDR(self, viscosityRatio, initialValue):
        return {
            'type': 'viscosityRatioInletOutletTDR',
            'viscosityRatio': ('uniform', viscosityRatio),
            'value': ('uniform', initialValue)
        }

    def _calculateFreeStreamTurbulentValues(self, xpath, region, model):
        ux = float(self._db.getValue(xpath + 'freeStream/streamVelocity/x'))
        uy = float(self._db.getValue(xpath + 'freeStream/streamVelocity/y'))
        uz = float(self._db.getValue(xpath + 'freeStream/streamVelocity/z'))

        v = sqrt(ux**2 + uy**2 + uz**2)

        p = float(self._db.getValue(xpath + '/freeStream/pressure'))
        t = float(self._db.getValue(xpath + '/temperature/constant'))

        if model == TurbulenceModel.K_EPSILON:
            mstr = 'k-epsilon'
        elif model == TurbulenceModel.K_OMEGA:
            mstr = 'k-omega'
        else:
            raise AssertionError

        i = float(self._db.getValue(xpath + '/turbulence/' + mstr + '/turbulentIntensity'))/100
        b = float(self._db.getValue(xpath + '/turbulence/' + mstr + '/turbulentViscosityRatio'))

        mid = RegionDB.getMaterial(region)
        rho = MaterialDB.getDensity(mid, t, p)  # Density
        mu = MaterialDB.getViscosity(mid, t)  # Viscosity

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
