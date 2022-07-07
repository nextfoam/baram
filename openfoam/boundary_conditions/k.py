#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.boundary_conditions.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType
from view.setup.boundary_conditions.boundary_db import KEpsilonSpecification, KOmegaSpecification, InterfaceMode
from view.setup.models.models_db import ModelsDB, TurbulenceModel
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class K(BoundaryCondition):
    DIMENSIONS = '[0 2 -2 0 0 0 0]'

    def __init__(self, rname: str):
        self._rname = rname
        super().__init__(self.boundaryLocation(rname), 'K')

        self._db = coredb.CoreDB()
        # ToDo: Set initialValue
        self._initialValue = 0
        self._specification = None
        self._model = ModelsDB.getTurbulenceModel()

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
            type_ = b[BoundaryListIndex.TYPE.value]
            xpath = BoundaryDB.getXPath(bcid)

            if type_ == BoundaryType.VELOCITY_INLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.FLOW_RATE_INLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.PRESSURE_INLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.PRESSURE_OUTLET.value:
                spec = self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow')
                if spec == 'true':
                    field[name] = self._constructInletOutletByModel(xpath)
                else:
                    field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.ABL_INLET.value:
                field[name] = self._constructAtmBoundaryLayerInletK()
            elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.FREE_STREAM.value:
                if self._model == TurbulenceModel.K_EPSILON:
                    spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
                    if spec == KEpsilonSpecification.K_AND_EPSILON.value:
                        field[name] = self._constructFreestream(xpath + '/freeStream')
                    elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                        field[name] = self._constructNEXTTurbulentIntensityInletOutletTKE(
                            self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity'))
                elif self._model == TurbulenceModel.K_OMEGA:
                    spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
                    if spec == KOmegaSpecification.K_AND_OMEGA.value:
                        field[name] = self._constructFreestream(xpath + '/freeStream')
                    elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                        field[name] = self._constructNEXTTurbulentIntensityInletOutletTKE(
                            self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity'))
            elif type_ == BoundaryType.FAR_FIELD_RIEMANN.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.SUBSONIC_INFLOW.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.SUBSONIC_OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.SUPERSONIC_INFLOW.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.SUPERSONIC_OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.WALL.value:
                field[name] = self._constructKqRWallFunction()
            elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                field[name] = self._constructKqRWallFunction()
            elif type_ == BoundaryType.SYMMETRY.value:
                field[name] = self._constructSymmetry()
            elif type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(xpath + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    field[name] = self._constructKqRWallFunction()
                else:
                    field[name] = self._constructCyclicAMI()
            elif type_ == BoundaryType.POROUS_JUMP.value:
                field[name] = self._constructCyclic()
            elif type_ == BoundaryType.FAN.value:
                field[name] = self._constructCyclic()
            elif type_ == BoundaryType.EMPTY.value:
                field[name] = self._constructEmpty()
            elif type_ == BoundaryType.CYCLIC.value:
                field[name] = self._constructCyclic()
            elif type_ == BoundaryType.WEDGE.value:
                field[name] = self._constructWedge()

        return field

    def _constructInletOutletByModel(self, xpath):
        if self._model == TurbulenceModel.K_EPSILON:
            spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
            if spec == KEpsilonSpecification.K_AND_EPSILON.value:
                return self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentKineticEnergy'), self._initialValue)
            elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructNEXTTurbulentIntensityInletOutletTKE(
                    self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentIntensity'))
        elif self._model == TurbulenceModel.K_OMEGA:
            spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
            if spec == KOmegaSpecification.K_AND_OMEGA.value:
                return self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/k-omega/turbulentKineticEnergy'), self._initialValue)
            elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                return self._constructNEXTTurbulentIntensityInletOutletTKE(
                    self._db.getValue(xpath + '/turbulence/k-omega/turbulentIntensity'))

    def _constructNEXTTurbulentIntensityInletOutletTKE(self, turbulentIntensity):
        return {
            'type': 'NEXT::turbulentIntensityInletOutletTKE',
            'turbIntensity': turbulentIntensity
        }

    def _constructAtmBoundaryLayerInletK(self):
        return {
            'type': 'atmBoundaryLayerInletK',
            'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
            'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
            'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
            'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }

    def _constructKqRWallFunction(self):
        return {
            'type': 'kqRWallFunction',
            'value': ('uniform', self._initialValue)
        }
