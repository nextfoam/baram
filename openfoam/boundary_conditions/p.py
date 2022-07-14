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

                if type_ == BoundaryType.VELOCITY_INLET.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.FLOW_RATE_INLET.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.PRESSURE_INLET.value:
                    field[name] = self._constructTotalPressure(self._db.getValue(xpath + '/pressureInlet/pressure'))
                elif type_ == BoundaryType.PRESSURE_OUTLET.value:
                    field[name] = self._constructTotalPressure(
                        self._db.getValue(xpath + '/pressureOutlet/totalPressure'))
                elif type_ == BoundaryType.ABL_INLET.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.OUTFLOW.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.FREE_STREAM.value:
                    field[name] = self._constructFreestreamPressure(xpath + '/freeStream')
                elif type_ == BoundaryType.FAR_FIELD_RIEMANN.value:
                    field[name] = self._constructFarfieldRiemann(xpath + '/farFieldRiemann')
                elif type_ == BoundaryType.SUBSONIC_INFLOW.value:
                    field[name] = self._constructSubsonicInflow(xpath + '/subsonicInflow')
                elif type_ == BoundaryType.SUBSONIC_OUTFLOW.value:
                    field[name] = self._constructSubsonicOutflow(xpath + '/subsonicOutflow')
                elif type_ == BoundaryType.SUPERSONIC_INFLOW.value:
                    field[name] = self._constructFixedValue(
                        self._db.getValue(xpath + '/supersonicInflow/staticPressure'))
                elif type_ == BoundaryType.SUPERSONIC_OUTFLOW.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.WALL.value:
                    field[name] = self._constructFluxPressure()
                elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                    field[name] = self._constructFluxPressure()
                elif type_ == BoundaryType.SYMMETRY.value:
                    field[name] = self._constructSymmetry()
                elif type_ == BoundaryType.INTERFACE.value:
                    spec = self._db.getValue(xpath + '/interface/mode')
                    if spec == InterfaceMode.REGION_INTERFACE.value:
                        field[name] = self._constructFluxPressure()
                    else:
                        field[name] = self._constructCyclicAMI()
                elif type_ == BoundaryType.POROUS_JUMP.value:
                    field[name] = self._constructPorousBafflePressure(xpath + '/porousJump')
                elif type_ == BoundaryType.FAN.value:
                    field[name] = self._constructFanPressure(xpath + '/fan')
                elif type_ == BoundaryType.EMPTY.value:
                    field[name] = self._constructEmpty()
                elif type_ == BoundaryType.CYCLIC.value:
                    field[name] = self._constructCyclic()
                elif type_ == BoundaryType.WEDGE.value:
                    field[name] = self._constructWedge()

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
