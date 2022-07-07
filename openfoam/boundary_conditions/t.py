#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.boundary_conditions.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType
from view.setup.boundary_conditions.boundary_db import FlowRateInletSpecification
from view.setup.boundary_conditions.boundary_db import TemperatureProfile, TemperatureTemporalDistribution
from view.setup.boundary_conditions.boundary_db import InterfaceMode
from view.setup.cell_zone_conditions.cell_zone_db import RegionDB
from view.setup.materials.material_db import Phase
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class T(BoundaryCondition):
    DIMENSIONS = '[0 0 0 1 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'T')

        self._rname = rname
        self._db = coredb.CoreDB()
        self._initialValue = self._db.getValue('.//initialization/initialValues/temperature')

    def build(self):
        if self._data is not None:
            return

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
            bcid = b[BoundaryListIndex.ID.value]
            name = b[BoundaryListIndex.NAME.value]
            xpath = BoundaryDB.getXPath(bcid)

            profile = self._db.getValue(xpath + '/temperature/profile')
            if profile == TemperatureProfile.CONSTANT.value:
                type_ = b[BoundaryListIndex.TYPE.value]
                constant = self._db.getValue(xpath + '/temperature/constant')

                if type_ == BoundaryType.VELOCITY_INLET.value:
                    field[name] = self._constructFixedValue(constant)
                elif type_ == BoundaryType.FLOW_RATE_INLET.value:
                    spec = self._db.getValue(xpath + '/flowRateInlet/flowRate/specification')
                    if spec == FlowRateInletSpecification.VOLUME_FLOW_RATE.value:
                        field[name] = self._constructFixedValue(constant)
                    elif spec == FlowRateInletSpecification.MASS_FLOW_RATE.value:
                        field[name] = self._constructInletOutletTemperature(constant)
                elif type_ == BoundaryType.PRESSURE_INLET.value:
                    field[name] = self._constructInletOutletTemperature(constant)
                elif type_ == BoundaryType.PRESSURE_OUTLET.value:
                    if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
                        field[name] = self._constructInletOutletTemperature(constant)
                    else:
                        field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.ABL_INLET.value:
                    pass
                elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                    pass
                elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                    pass
                elif type_ == BoundaryType.OUTFLOW.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.FREE_STREAM.value:
                    field[name] = self._constructFreestream(xpath + '/freeStream')
                elif type_ == BoundaryType.FAR_FIELD_RIEMANN.value:
                    field[name] = self._constructFarfieldRiemann(xpath + '/farFieldRiemann')
                elif type_ == BoundaryType.SUBSONIC_INFLOW.value:
                    field[name] = self._constructSubsonicInflow(xpath + '/subsonicInflow')
                elif type_ == BoundaryType.SUBSONIC_OUTFLOW.value:
                    field[name] = self._constructSubsonicOutflow(xpath + '/subsonicOutflow')
                elif type_ == BoundaryType.SUPERSONIC_INFLOW.value:
                    field[name] = self._constructFixedValue(constant)
                elif type_ == BoundaryType.SUPERSONIC_OUTFLOW.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.WALL.value:
                    field[name] = self._constructZeroGradient()
                elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                    field[name] = self._constructNEXTTurbulentTemperatureCoupledBaffleMixed()
                elif type_ == BoundaryType.SYMMETRY.value:
                    field[name] = self._constructSymmetry()
                elif type_ == BoundaryType.INTERFACE.value:
                    spec = self._db.getValue(xpath + '/interface/mode')
                    if spec == InterfaceMode.REGION_INTERFACE.value:
                        field[name] = self._constructNEXTTurbulentTemperatureCoupledBaffleMixed()
                    else:
                        field[name] = self._constructCyclicAMI()
                elif type_ == BoundaryType.POROUS_JUMP.value:
                    field[name] = self._constructPorousBafflePressure(xpath + '/porousJump')
                elif type_ == BoundaryType.FAN.value:
                    field[name] = self._constructCyclic()
                elif type_ == BoundaryType.EMPTY.value:
                    field[name] = self._constructEmpty()
                elif type_ == BoundaryType.CYCLIC.value:
                    field[name] = self._constructCyclic()
                elif type_ == BoundaryType.WEDGE.value:
                    field[name] = self._constructWedge()
            elif profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value:
                field[name] = self._constructTimeVaryingMappedFixedValue(
                    self._rname, 'T', self._db.getValue(xpath + '/temperature/spatialDistribution'))
            elif profile == TemperatureProfile.TEMPORAL_DISTRIBUTION.value:
                spec = self._db.getValue(xpath + '/temperature/temporalDistribution/specification')
                if spec == TemperatureTemporalDistribution.PIECEWISE_LINEAR.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/piecewiseLinear', self.TableType.TEMPORAL_SCALAR_LIST
                    )
                elif spec == TemperatureTemporalDistribution.POLYNOMIAL.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/polynomial', self.TableType.NUMBER_LIST, 'a')

        return field

    def _constructInletOutletTemperature(self, constant):
        return {
            'type': 'inletOutletTotalTemperature',
            'gamma': 'gamma',
            'inletValue': ('uniform', constant),
            'T0': ('uniform', constant)
        }

    def _constructNEXTTurbulentTemperatureCoupledBaffleMixed(self):
        return {
            'type': 'NEXT::turbulentTemperatureCoupledBaffleMixed',
            'Tnbr': 'T',
            'kappaMethod': 'solidThermo' if RegionDB.getPhase(self._rname) == Phase.SOLID else 'fluidThermo'
        }
