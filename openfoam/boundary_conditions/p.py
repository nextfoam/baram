#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType, InterfaceMode
from coredb.cell_zone_db import CellZoneDB
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class P(BoundaryCondition):
    DIMENSIONS = '[1 -1 -2 0 0 0 0]'

    def __init__(self, rname: str, field='p', calculated=False):
        super().__init__(self.boundaryLocation(rname), field)

        self._rname = rname
        self._calculated = calculated
        self._db = coredb.CoreDB()
        self._initialValue = self._db.getValue('.//initialization/initialValues/pressure')
        self._calculatedValue = 0

        if calculated:
            operatingPressure = self._db.getValue(CellZoneDB.OPERATING_CONDITIONS_XPATH + '/pressure')
            self._calculatedValue = float(self._initialValue) + float(operatingPressure)

    def build(self):
        if self._data is not None:
            return self

        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self._initialValue),
            'boundaryField': self._constructBoundaryField()
        }

        return self

    def _constructBoundaryField(self):
        field = {}

        boundaries = self._db.getBoundaryConditions(self._rname)
        for b in boundaries:
            name = b[BoundaryListIndex.NAME.value]

            if self._calculated:
                field[name] = self._constructCalculated(self._calculatedValue)
            else:
                bcid = b[BoundaryListIndex.ID.value]
                type_ = b[BoundaryListIndex.TYPE.value]
                xpath = BoundaryDB.getXPath(bcid)

                field[name] = {
                    BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructZeroGradient()),
                    BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructZeroGradient()),
                    BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructTotalPressure(self._db.getValue(xpath + '/pressureInlet/pressure'))),
                    BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructTotalPressure(self._db.getValue(xpath + '/pressureOutlet/totalPressure'))),
                    BoundaryType.ABL_INLET.value:           (lambda: self._constructZeroGradient()),
                    BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructZeroGradient()),
                    BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                    BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestreamPressure(xpath + '/freeStream')),
                    BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemann(xpath + '/farFieldRiemann')),
                    BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructSubsonicInflow(xpath + '/subsonicInflow')),
                    BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                    BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue( self._db.getValue(xpath + '/supersonicInflow/staticPressure'))),
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

    def _constructFreestreamPressure(self, xpath):
        return {
            'type': 'freestreamPressure',
            'freestreamValue': self._db.getValue(xpath + '/pressure')
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