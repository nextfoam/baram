#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from coredb.general_db import GeneralDB
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition
import openfoam.solver

TYPE_MAP = {
    BoundaryType.VELOCITY_INLET.value: 'calculated',
    BoundaryType.FLOW_RATE_INLET.value: 'calculated',
    BoundaryType.PRESSURE_INLET.value: 'calculated',
    BoundaryType.ABL_INLET.value: 'calculated',
    BoundaryType.OPEN_CHANNEL_INLET.value: 'calculated',
    BoundaryType.FREE_STREAM.value: 'calculated',
    BoundaryType.FAR_FIELD_RIEMANN.value: 'calculated',
    BoundaryType.SUBSONIC_INFLOW.value: 'calculated',
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


class P(BoundaryCondition):
    DIMENSIONS = '[1 -1 -2 0 0 0 0]'

    def __init__(self, rname: str, field='p'):
        super().__init__(self.boundaryLocation(rname), field)

        self._rname = rname
        self._db = coredb.CoreDB()
        self.initialPressure = float(self._db.getValue('.//initialization/initialValues/pressure'))
        self.operatingPressure = float(self._db.getValue(GeneralDB.OPERATING_CONDITIONS_XPATH + '/pressure'))

        self._field = field
        self._data = None
        self._usePrgh = False

        solvers = openfoam.solver.findSolvers()
        if len(solvers) == 0:  # configuration not enough yet
            raise RuntimeError

        cap = openfoam.solver.getSolverCapability(solvers[0])
        self._usePrgh = cap['usePrgh']

        if field == 'p_rgh' and cap['useGaugePressureInPrgh']:
            self.operatingPressure = 0  # This makes Gauge Pressure value unchanged

    def build(self):
        self._data = None

        forceCalculatedType = False

        if self._field == 'p_rgh' and not self._usePrgh:
            return self  # no "p_rgh" file

        if self._field == 'p' and self._usePrgh:  # "p" field is calculated internally by the solver
            forceCalculatedType = True

        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self.initialPressure + self.operatingPressure),
            'boundaryField': self._constructBoundaryField(forceCalculatedType)
        }

        return self

    def _constructBoundaryField(self, forceCalculatedType):
        field = {}

        boundaries = self._db.getBoundaryConditions(self._rname)
        for bcid, name, type_ in boundaries:
            t = TYPE_MAP[type_]
            if type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(BoundaryDB.getXPath(bcid) + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    t = 'calculated'

            if forceCalculatedType:
                field[name] = {
                    'calculated': (lambda: self._constructCalculated(self.initialPressure + self.operatingPressure)),
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
                    BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructTotalPressure(self.operatingPressure + float(self._db.getValue(xpath + '/pressureInlet/pressure')))),
                    BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructTotalPressure(self.operatingPressure + float(self._db.getValue(xpath + '/pressureOutlet/totalPressure')))),
                    BoundaryType.ABL_INLET.value:           (lambda: self._constructZeroGradient()),
                    BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructZeroGradient()),
                    BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                    BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestreamPressure(self.operatingPressure + float(self._db.getValue(xpath + '/freeStream/pressure')))),
                    BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemann(xpath + '/farFieldRiemann')),
                    BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructSubsonicInflow(xpath + '/subsonicInflow')),
                    BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                    BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(self.operatingPressure + float(self._db.getValue(xpath + '/supersonicInflow/staticPressure')))),
                    BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.WALL.value:                (lambda: self._constructFluxPressure()),
                    BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructFluxPressure()),
                    BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                    BoundaryType.INTERFACE.value:           (lambda: self._constructInterfacePressure(self._db.getValue(xpath + '/interface/mode'))),
                    BoundaryType.POROUS_JUMP.value:         (lambda: self._constructPorousBafflePressure(xpath + '/porousJump', self.initialPressure + self.operatingPressure)),
                    BoundaryType.FAN.value:                 (lambda: self._constructFan(xpath + '/fan', self.initialPressure + self.operatingPressure)),
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

    def _constructFreestreamPressure(self, pressure):
        return {
            'type': 'freestreamPressure',
            'freestreamValue': pressure
        }

    def _constructFluxPressure(self):
        return {
            'type': 'fixedFluxPressure'
        }

    def _constructInterfacePressure(self, spec):
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructFluxPressure()
        else:
            return self._constructCyclicAMI()

    def _constructFan(self, xpath, value):
        return {
            'type': 'fan',
            'patchType': 'cyclic',
            'fanCurve': 'csvFile',
            'nHeaderLine': 0,
            'refColumn': 0,
            'componentColumns': '( 1 )',
            'separator': '","',
            'mergeSeparators': 'no',
            'outOfBounds': 'clamp',
            'interpolationScheme': 'linear',
            # ToDo: set fanCurveFile according to the coredb's file handling structure
            'file': self._db.getValue(xpath + '/fanCurveFile'),
            'reverse': self._db.getValue(xpath + '/reverseDirection'),
            'value': ('uniform', value)
        }