#!/usr/bin/env python
# -*- coding: utf-8 -*-
from uuid import UUID

from libbaram.natural_name_uuid import uuidToNnstr

from baramFlow.base.base import SpatialScalarList
from baramFlow.base.boundary.flow_rate_port import FlowRateSpecification
from baramFlow.base.boundary.temperature import TemperatureProfile, TemperatureTemporalDistributionSpecification
from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType, WallHeatTransferMode
from baramFlow.coredb.boundary_db import InterfaceMode
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.coredb.project import Project
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class T(BoundaryCondition):
    DIMENSIONS = '[0 0 0 1 0 0 0]'

    def __init__(self, region, time, processorNo):
        super().__init__(region, time, processorNo, 'T')

        self._initialValue = region.initialTemperature

    def build0(self):
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

            if type_ == BoundaryType.WALL.value:
                if WallHeatTransferMode(self._db.getValue(xpath + '/wall/heatTransfer/type')) == WallHeatTransferMode.TEMPERATURE_DISTRIBUTION:
                    df = Project.instance().fileDB().getDataFrame(uuidToNnstr(UUID(self._db.getValue(xpath + '/wall/heatTransfer/temperatureDistributionName'))))
                    field[name] = self._constructTimeVaryingMappedFixedValue(self._region.rname, name, 'T', df)
                else:
                    field[name] = self._constructWallT(xpath, float(self._db.getValue(xpath + '/temperature/constant')))
            elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                field[name] = self._constructCompressibleturbulentTemperatureRadCoupledMixed(xpath, type_)
            elif profile == TemperatureProfile.CONSTANT.value:
                constant = float(self._db.getValue(xpath + '/temperature/constant'))

                field[name] = {
                    BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructFixedValue(constant)),
                    BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructFlowRateInletT(xpath, constant)),
                    BoundaryType.FLOW_RATE_OUTLET.value:    (lambda: self._constructZeroGradient()),
                    BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructInletOutletTotalTemperature(xpath, constant)),
                    BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPressureOutletT(xpath)),
                    BoundaryType.INTAKE_FAN.value:          (lambda: self._constructFixedValue(constant)),
                    BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructZeroGradient()),
                    BoundaryType.ABL_INLET.value:           (lambda: self._constructFixedValue(constant)),
                    BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructFixedValue(constant)),
                    BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructFixedValue(constant)),
                    BoundaryType.OUTFLOW.value:             (lambda: self._constructZeroGradient()),
                    BoundaryType.FREE_STREAM.value:         (lambda: self._constructFreeStream(constant)),
                    BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructFarfieldRiemann(xpath + '/farFieldRiemann', self._db.getValue(xpath + '/farFieldRiemann/staticTemperature'))),
                    BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructSubsonicInlet(xpath + '/subsonicInlet')),
                    BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructSubsonicOutflow(xpath + '/subsonicOutflow')),
                    BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructFixedValue(float(self._db.getValue(xpath + '/supersonicInflow/staticTemperature')))),
                    BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructZeroGradient()),
                    BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                    BoundaryType.INTERFACE.value:           (lambda: self._constructInterfaceT(xpath)),
                    BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                    BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                    BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                    BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                    BoundaryType.CYCLIC_ACMI.value:         (lambda: self._constructCyclicACMI()),
                    BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
                }.get(type_, lambda: None)()
            elif profile == TemperatureProfile.SPATIAL_DISTRIBUTION.value:
                field[name] = self._constructTimeVaryingMappedFixedValue(
                    self._region.rname, name, 'T',
                    SpatialScalarList.fromElement(
                        self._db.getElement(xpath + '/temperature/spatialDistribution')).dataFrame())
            elif profile == TemperatureProfile.TEMPORAL_DISTRIBUTION.value:
                spec = self._db.getValue(xpath + '/temperature/temporalDistribution/specification')
                if spec == TemperatureTemporalDistributionSpecification.PIECEWISE_LINEAR.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/piecewiseLinear', self.TableType.TEMPORAL_SCALAR_LIST
                    )
                elif spec == TemperatureTemporalDistributionSpecification.POLYNOMIAL.value:
                    field[name] = self._constructUniformFixedValue(
                        xpath + '/temperature/temporalDistribution/polynomial', self.TableType.POLYNOMIAL)

        return field

    def _constructInletOutletTotalTemperature(self, xpath, constant):
        if ModelsDB.isEnergyModelOn():
            gamma = self._calculateGamma(MaterialDB.getMaterialComposition(xpath + '/species', self._region.mid), constant)
        else:
            gamma = 1.0

        return {
            'type': 'inletOutletTotalTemperature',
            'gamma': gamma,
            'inletValue': ('uniform', constant),
            'T0': ('uniform', constant)
        }

    def _constructCompressibleturbulentTemperatureRadCoupledMixed(self, xpath, type_=None):
        data = {
            'type': 'compressible::turbulentTemperatureRadCoupledMixed',
            'Tnbr': 'T',
            'kappaMethod': 'fluidThermo' if self._region.isFluid() else 'solidThermo',
            'value': self._initialValueByTime()
        }

        if type_ == BoundaryType.THERMO_COUPLED_WALL.value:
            wallLayersXpath = xpath + '/thermoCoupledWall/temperature/wallLayers'
            if self._db.getAttribute(wallLayersXpath, 'disabled') == 'false':
                data['thicknessLayers'] = self._db.getValue(wallLayersXpath + '/thicknessLayers').split()
                data['kappaLayers'] = self._db.getValue(wallLayersXpath + '/thermalConductivityLayers').split()

        return data

    def _constructFlowRateInletT(self, xpath, constant):
        spec = self._db.getValue(xpath + '/flowRateInlet/flowRate/specification')
        if spec == FlowRateSpecification.VOLUME_FLOW_RATE.value:
            return self._constructFixedValue(constant)
        elif spec == FlowRateSpecification.MASS_FLOW_RATE.value:
            return self._constructInletOutletTotalTemperature(xpath, constant)

    def _constructPressureOutletT(self, xpath):
        if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
            constant = float(self._db.getValue(xpath + '/pressureOutlet/backflowTotalTemperature'))
            return self._constructInletOutletTotalTemperature(xpath, constant)
        else:
            return self._constructZeroGradient()

    def _constructInterfaceT(self, xpath):
        spec = self._db.getValue(xpath + '/interface/mode')
        if spec == InterfaceMode.REGION_INTERFACE.value:
            return self._constructCompressibleturbulentTemperatureRadCoupledMixed(xpath)
        else:
            return self._constructCyclicAMI()

    def _constructWallT(self, xpath, constant):
        if self._isAtmosphericWall(xpath):
            return self._constructFixedValue(constant)
        else:
            spec = self._db.getValue(xpath + '/wall/heatTransfer/type')
            if spec == WallHeatTransferMode.ADIABATIC.value:
                return self._constructZeroGradient()
            elif spec == WallHeatTransferMode.CONSTANT_TEMPERATURE.value:
                t = self._db.getValue(xpath + '/wall/heatTransfer/temperature')
                return self._constructFixedValue(t)
            elif spec == WallHeatTransferMode.CONSTANT_HEAT_FLUX.value:
                q = self._db.getValue(xpath + '/wall/heatTransfer/heatFlux')
                return {
                    'type': 'externalWallHeatFluxTemperature',
                    'mode': 'flux',
                    'q': ('uniform', q),
                    'kappaMethod': 'fluidThermo' if self._region.isFluid() else 'solidThermo',
                    'value': self._initialValueByTime()
                }
            elif spec == WallHeatTransferMode.CONVECTION.value:
                data = {
                    'type': 'externalWallHeatFluxTemperature',
                    'mode': 'coefficient',
                    'h': ('constant', self._db.getValue(xpath + '/wall/heatTransfer/heatTransferCoefficient')),
                    'Ta': ('constant', self._db.getValue(xpath + '/wall/heatTransfer/freeStreamTemperature')),
                    'emissivity': self._db.getValue(xpath + '/wall/heatTransfer/externalEmissivity'),
                    'kappaMethod': 'fluidThermo' if self._region.isFluid() else 'solidThermo',
                    'value': self._initialValueByTime()
                }

                wallLayersXpath = xpath + '/wall/heatTransfer/wallLayers'
                if self._db.getAttribute(wallLayersXpath, 'disabled') == 'false':
                    data['thicknessLayers'] = self._db.getValue(wallLayersXpath + '/thicknessLayers').split()
                    data['kappaLayers'] = self._db.getValue(wallLayersXpath + '/thermalConductivityLayers').split()

                return data

