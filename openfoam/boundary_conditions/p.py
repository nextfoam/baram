#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryDB, BoundaryType, InterfaceMode
from coredb.general_db import GeneralDB
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition
import openfoam.solver


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

        if field == 'p_rgh':
            solvers = openfoam.solver.findSolvers()
            if len(solvers) == 0:  # configuration not enough yet
                raise RuntimeError

            cap = openfoam.solver.getSolverCapability(solvers[0])
            if cap['nextfoamCustom']:  # Gauge Pressure is used for p_rgh
                self.operatingPressure = 0  # This makes Gauge Pressure value unchanged

    def build(self):
        self._data = None

        forceCalculatedType = False

        if self._field == 'p_rgh' and not GeneralDB.isGravityModelOn():
            return self  # no "p_rgh" file

        if self._field == 'p' and GeneralDB.isGravityModelOn():  # "p" field is calculated internally by the solver
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
            if forceCalculatedType:
                field[name] = self._constructCalculated(self.initialPressure + self.operatingPressure)
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
                    BoundaryType.POROUS_JUMP.value:         (lambda: self._constructPorousBafflePressure(xpath + '/porousJump')),
                    BoundaryType.FAN.value:                 (lambda: self._constructFanPressure(xpath + '/fan')),
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

    def _constructPorousBafflePressure(self, xpath):
        return {
            'type': 'porousBafflePressure',
            'patchType': 'cyclic',
            'D': self._db.getValue(xpath + '/darcyCoefficient'),
            'I': self._db.getValue(xpath + '/inertialCoefficient'),
            'length': self._db.getValue(xpath + '/porousMediaThickness'),
        }

    def _constructFanPressure(self, xpath):
        return {
            'type': 'fanPressureJump',
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
        }