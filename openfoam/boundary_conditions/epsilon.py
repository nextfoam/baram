#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType
from coredb.boundary_db import KEpsilonSpecification, InterfaceMode
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Epsilon(BoundaryCondition):
    DIMENSIONS = '[0 2 -3 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'epsilon')

        self._rname = rname
        self._db = coredb.CoreDB()
        # ToDo: Set initialValue
        self._initialValue = 0

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
                if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
                    field[name] = self._constructInletOutletByModel(xpath)
                else:
                    field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.ABL_INLET.value:
                field[name] = self._constructAtmBoundaryLayerInletEpsilon()
            elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.FREE_STREAM.value:
                spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
                if spec == KEpsilonSpecification.K_AND_EPSILON.value:
                    field[name] = self._constructFreestream(xpath + '/freeStream')
                elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                    field[name] = self._constructNEXTViscosityRatioInletOutletTDR(
                        self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))
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
                field[name] = self._constructNEXTEpsilonWallFunction()
            elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                field[name] = self._constructNEXTEpsilonWallFunction()
            elif type_ == BoundaryType.SYMMETRY.value:
                field[name] = self._constructSymmetry()
            elif type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(xpath + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    field[name] = self._constructNEXTEpsilonWallFunction()
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
        spec = self._db.getValue(xpath + '/turbulence/k-epsilon/specification')
        if spec == KEpsilonSpecification.K_AND_EPSILON.value:
            return self._constructInletOutlet(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentDissipationRate'), self._initialValue)
        elif spec == KEpsilonSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructNEXTViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-epsilon/turbulentViscosityRatio'))

    def _constructAtmBoundaryLayerInletEpsilon(self):
        return {
            'type': 'atmBoundaryLayerInletVelocity',
            'flowDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/flowDirection'),
            'zDir': self._db.getVector(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/groundNormalDirection'),
            'Uref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceFlowSpeed'),
            'Zref': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/referenceHeight'),
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }

    def _constructNEXTEpsilonWallFunction(self):
        return {
            'type': 'NEXT::epsilonWallFunction',
            'value': ('uniform', self._initialValue)
        }
