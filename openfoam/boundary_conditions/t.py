#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.filedb import BcFileRole
from coredb.boundary_db import BoundaryDB, BoundaryType, FlowRateInletSpecification, WallVelocityCondition
from coredb.boundary_db import TemperatureProfile, TemperatureTemporalDistribution, InterfaceMode
from coredb.material_db import MaterialDB, UNIVERSAL_GAL_CONSTANT
from coredb.models_db import ModelsDB
from coredb.project import Project
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class T(BoundaryCondition):
    DIMENSIONS = '[0 0 0 1 0 0 0]'

    def __init__(self, region):
        super().__init__(self.boundaryLocation(region.rname), 'T')

        self._region = region
        self._db = coredb.CoreDB()
        self._initialValue = self._db.getValue('.//initialization/initialValues/temperature')

        self._data = None

    def build(self):
        self._data = {
            'dimensions': self.DIMENSIONS,
            'internalField': ('uniform', self._initialValue),
            'boundaryField': self._constructBoundaryField()
        }

        return self

    def _constructBoundaryField(self):
        field = {}

        for bcid, name, type_ in self._region.boundaries:
            xpath = BoundaryDB.getXPath(bcid)

            profile = self._db.getValue(xpath + '/temperature/profile')
            if profile == TemperatureProfile.CONSTANT.value:
                constant = float(self._db.getValue(xpath + '/temperature/constant'))

                field[name] = {
                    BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValue(constant)),
                    BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFlowRateInletT(xpath, constant)),
                    BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructInletOutletTotalTemperature(constant)),
                    BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletT(xpath, constant)),
                    BoundaryType.ABL_INLET.value:           (lambda: self._constructFixedValue(constant)),
                    BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructFixedValue(constant)),
                    BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructFixedValue(constant)),
                    BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                    BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreestream(xpath + '/freeStream')),
                    BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemann(xpath + '/farFieldRiemann')),
                    BoundaryType.SUBSONIC_INFLOW.value:     (lambda: self._constructSubsonicInflow(xpath + '/subsonicInflow')),
                    BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                    BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(constant)),
                    BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.WALL.value:                (lambda: self._constructWallT(xpath, constant)),
                    BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructCompressibleTurbulentTemperatureCoupledBaffleMixed()),
                    BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                    BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceT(xpath)),
                    BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                    BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                    BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                    BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                    BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
                }.get(type_)()
            elif profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value:
                field[name] = self._constructTimeVaryingMappedFixedValue(
                    self._region.rname, name, 'T',
                    Project.instance().fileDB().getBcFile(bcid, BcFileRole.BC_TEMPERATURE))
            elif profile == TemperatureProfile.TEMPORAL_DISTRIBUTION.value:
                spec = self._db.getValue(xpath + '/temperature/temporalDistribution/specification')
                if spec == TemperatureTemporalDistribution.PIECEWISE_LINEAR.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/piecewiseLinear', self.TableType.TEMPORAL_SCALAR_LIST
                    )
                elif spec == TemperatureTemporalDistribution.POLYNOMIAL.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/polynomial', self.TableType.POLYNOMIAL)

        return field

    def _constructInletOutletTotalTemperature(self, constant):
        if ModelsDB.isEnergyModelOn():
            cp = MaterialDB.getSpecificHeat(self._region.mid, constant)
            mw = MaterialDB.getMolecularWeight(self._region.mid)
            gamma = cp / (cp - UNIVERSAL_GAL_CONSTANT/mw)
        else:
            gamma = 1.0

        return {
            'type': 'inletOutletTotalTemperature',
            'gamma': gamma,
            'inletValue': ('uniform', constant),
            'T0': ('uniform', constant)
        }

    def _constructCompressibleTurbulentTemperatureCoupledBaffleMixed(self):
        return {
            'type': 'compressible::turbulentTemperatureCoupledBaffleMixed',
            'Tnbr': 'T',
            'kappaMethod': 'fluidThermo' if self._region.isFluid() else 'solidThermo',
            'value': ('uniform', self._initialValue)
        }

    def _constructFlowRateInletT(self, xpath, constant):
        spec = self._db.getValue(xpath + '/flowRateInlet/flowRate/specification')
        if spec == FlowRateInletSpecification.VOLUME_FLOW_RATE.value:
            return self._constructFixedValue(constant)
        elif spec == FlowRateInletSpecification.MASS_FLOW_RATE.value:
            return self._constructInletOutletTotalTemperature(constant)

    def _constructPressureOutletT(self, xpath, constant):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            return self._constructInletOutletTotalTemperature(constant)
        else:
            return self._constructZeroGradient()

    def _constructInterfaceT(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructCompressibleTurbulentTemperatureCoupledBaffleMixed()
        else:
            return self._constructCyclicAMI()

    def _constructWallT(self, xpath, constant):
        spec = self._db.getValue(xpath + '/wall/velocity/type')
        if spec == WallVelocityCondition.ATMOSPHERIC_WALL.value:
            return self._constructFixedValue(constant)
        else:
            return self._constructZeroGradient()

