#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from uuid import UUID

from PyFoam.Basics.FoamFileGenerator import FoamFileGenerator

from baramFlow.coredb.project import Project
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from baramFlow.coredb.coredb_reader import Region
from baramFlow.coredb.general_db import GeneralDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition
from baramFlow.openfoam.file_system import FileSystem
from baramFlow.openfoam.solver import usePrgh, useGaugePressureInPrgh
from libbaram.natural_name_uuid import uuidToNnstr


TYPE_MAP = {
    BoundaryType.VELOCITY_INLET.value: 'calculated',
    BoundaryType.FLOW_RATE_INLET.value: 'calculated',
    BoundaryType.FLOW_RATE_OUTLET.value: 'calculated',
    BoundaryType.PRESSURE_INLET.value: 'calculated',
    BoundaryType.INTAKE_FAN.value: 'calculated',
    BoundaryType.EXHAUST_FAN.value: 'calculated',
    BoundaryType.ABL_INLET.value: 'calculated',
    BoundaryType.OPEN_CHANNEL_INLET.value: 'calculated',
    BoundaryType.FREE_STREAM.value: 'calculated',
    BoundaryType.FAR_FIELD_RIEMANN.value: 'calculated',
    BoundaryType.SUBSONIC_INLET.value: 'calculated',
    BoundaryType.SUPERSONIC_INFLOW.value: 'calculated',
    BoundaryType.PRESSURE_OUTLET.value: 'calculated',
    BoundaryType.OPEN_CHANNEL_OUTLET.value: 'calculated',
    BoundaryType.OUTFLOW.value: 'calculated',
    BoundaryType.SUBSONIC_OUTFLOW.value: 'calculated',
    BoundaryType.SUPERSONIC_OUTFLOW.value: 'calculated',
    BoundaryType.WALL.value: 'calculated',
    BoundaryType.THERMO_COUPLED_WALL.value: 'calculated',
    BoundaryType.POROUS_JUMP.value: 'cyclic',
    BoundaryType.FAN.value: 'cyclic',
    BoundaryType.SYMMETRY.value: 'symmetry',
    BoundaryType.INTERFACE.value: 'cyclicAMI',
    BoundaryType.EMPTY.value: 'empty',
    BoundaryType.CYCLIC.value: 'cyclic',
    BoundaryType.WEDGE.value: 'wedge',
}


class FanPressureDirection(Enum):
    IN = 'in'
    OUT = 'out'


class P(BoundaryCondition):
    DIMENSIONS = '[1 -1 -2 0 0 0 0]'

    def __init__(self, region: Region, time, processorNo, field):
        super().__init__(region, time, processorNo, field)

        self._operatingPressure = 0

        self._field = field
        self._usePrgh = False

        self._initialValue = 0

    def build0(self):
        self._data = None

        initialGaugePressure = float(
            self._db.getValue(f'{RegionDB.getXPath(self._region.rname)}/initialization/initialValues/pressure'))

        self._usePrgh = usePrgh()

        self._operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))
        if self._field == 'p_rgh':
            if not self._usePrgh:
                return self  # no "p_rgh" file

            if useGaugePressureInPrgh():
                self._operatingPressure = 0  # This makes Gauge Pressure value unchanged

        self._initialValue = initialGaugePressure + self._operatingPressure

        forceCalculatedType = False
        if self._field == 'p' and self._usePrgh:  # "p" field is calculated internally by the solver
            forceCalculatedType = True

        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self._initialValue),
            'boundaryField': self._constructBoundaryField(forceCalculatedType)
        }

        return self

    def _constructBoundaryField(self, forceCalculatedType):
        field = {}

        for bcid, name, type_ in self._region.boundaries:
            t = TYPE_MAP[type_]
            if type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(BoundaryDB.getXPath(bcid) + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    t = 'calculated'

            if forceCalculatedType:
                field[name] = {
                    'calculated': (lambda: self._constructCalculated()),
                    'cyclic':     (lambda: self._constructCyclic()),
                    'symmetry':   (lambda: self._constructSymmetry()),
                    'cyclicAMI':  (lambda: self._constructCyclicAMI()),
                    'empty':      (lambda: self._constructEmpty()),
                    'wedge':      (lambda: self._constructWedge())
                }.get(t)()
            else:
                xpath = BoundaryDB.getXPath(bcid)

                field[name] = {
                    BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructZeroGradient()),
                    BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructZeroGradient()),
                    BoundaryType.FLOW_RATE_OUTLET.value:    (lambda: self._constructZeroGradient()),
                    BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructTotalPressure(self._operatingPressure + float(self._db.getValue(xpath + '/pressureInlet/pressure')))),
                    BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletP(xpath)),
                    BoundaryType.INTAKE_FAN.value:          (lambda: self._constructFanPressure(xpath, bcid, FanPressureDirection.IN)),
                    BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructFanPressure(xpath, bcid, FanPressureDirection.OUT)),
                    BoundaryType.ABL_INLET.value:           (lambda: self._constructZeroGradient()),
                    BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructZeroGradient()),
                    BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                    BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestreamPressure(self._operatingPressure + float(self._db.getValue(xpath + '/freeStream/pressure')))),
                    BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemann(xpath + '/farFieldRiemann', self._operatingPressure + float(self._db.getValue(xpath + '/farFieldRiemann/staticPressure')))),
                    BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructSubsonicInlet(xpath + '/subsonicInlet')),
                    BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                    BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(self._operatingPressure + float(self._db.getValue(xpath + '/supersonicInflow/staticPressure')))),
                    BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.WALL.value:                (lambda: self._constructWall()),
                    BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructFluxPressure()),
                    BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                    BoundaryType.INTERFACE.value:           (lambda: self._constructInterfacePressure(self._db.getValue(xpath + '/interface/mode'))),
                    BoundaryType.POROUS_JUMP.value:         (lambda: self._constructPorousBafflePressure(xpath + '/porousJump')),
                    BoundaryType.FAN.value:                 (lambda: self._constructFan(xpath, bcid)),
                    BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                    BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                    BoundaryType.WEDGE.value:               (lambda: self._constructWedge())
                }.get(type_)()

        return field

    def _constructTotalPressure(self, pressure):
        return {
            'type': 'totalPressure',
            'p0': ('uniform', pressure)
        }

    def _constructPressureOutletP(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/nonReflective') == 'true':
            t = 300
            if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
                t = float(self._db.getValue(xpath + '/pressureOutlet/backflowTotalTemperature'))
            return self._constructWaveTransmissive(xpath, t)
        else:
            return self._constructTotalPressure(
                self._operatingPressure + float(self._db.getValue(xpath + '/pressureOutlet/totalPressure')))

    def _constructFreestreamPressure(self, pressure):
        return {
            'type': 'freestreamPressure',
            'freestreamValue': ('uniform', pressure)
        }

    def _constructWall(self):
        if GeneralDB.isCompressibleDensity():
            return self._constructZeroGradient()
        else:
            return self._constructFluxPressure()

    def _constructFluxPressure(self):
        return {
            'type': 'fixedFluxPressure'
        }

    def _constructInterfacePressure(self, spec):
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructFluxPressure()
        else:
            return self._constructCyclicAMI()

    def _constructPorousBafflePressure(self, xpath):
        return {
            'type': 'porousBafflePressure',
            'patchType': 'cyclic',
            'D': self._db.getValue(xpath + '/darcyCoefficient'),
            'I': self._db.getValue(xpath + '/inertialCoefficient'),
            'length': self._db.getValue(xpath + '/porousMediaThickness'),
            'value': self._initialValueByTime()
        }

    def _constructFan(self, xpath, bcid):
        fanCurveFileName = f'fanCurve_{bcid}'
        self._writeFanCurveFile(fanCurveFileName, xpath)

        return {
            'type': 'fan',
            'patchType': 'cyclic',
            'mode': 'volumeFlowRate',
            'jumpTable': {
                'type': 'table',
                'file': f'constant/{fanCurveFileName}',
                'outOfBounds': 'clamp'
            },
            'value': self._initialValueByTime()
        }

    def _constructFanPressure(self, xpath, bcid, direction):
        fanCurveFileName = f'fanCurve_{bcid}'
        self._writeFanCurveFile(fanCurveFileName, xpath)

        p0 = self._operatingPressure + float(self._db.getValue(xpath + '/pressure'))
        return {
            'type': 'fanPressure',
            'direction': direction.value,
            'fanCurve': {
                'type': 'table',
                'file': f'constant/{fanCurveFileName}',
                'outOfBounds': 'clamp'
            },
            'p0': ('uniform', p0),
            'value': self._initialValueByTime()
        }

    def _writeFanCurveFile(self, fileName, xpath):
        fanCurveName = UUID(self._db.getValue(xpath + '/fanCurveName'))
        fanCurve = None
        if fanCurveName.int != 0:
            df = Project.instance().fileDB().getDataFrame(uuidToNnstr(fanCurveName))
            if df is not None:
                fanCurve = df.values.tolist()
                if len(fanCurve[0]) > 2:  # if it includes vector value
                    fanCurve = [[row[0], row[1:]] for row in fanCurve]

        # ToDo: What if fanCurve is not available?

        path = FileSystem.constantPath() / fileName
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(str(FoamFileGenerator(fanCurve)))
