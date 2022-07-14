#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from coredb.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType
from coredb.boundary_db import KOmegaSpecification, WallVelocityCondition, InterfaceMode
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Omega(BoundaryCondition):
    DIMENSIONS = '[0 0 -1 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'omega')

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
                spec = self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow')
                if spec == 'true':
                    field[name] = self._constructInletOutletByModel(xpath)
                else:
                    field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.ABL_INLET.value:
                field[name] = self._constructInletOutlet(
                    self._db.getValue(xpath + '/turbulence/k-omega/specificDissipationRate'), self._initialValue)
            elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                field[name] = self._constructInletOutletByModel(xpath)
            elif type_ == BoundaryType.OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.FREE_STREAM.value:
                spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
                if spec == KOmegaSpecification.K_AND_OMEGA.value:
                    field[name] = self._constructFreestream(xpath + '/freeStream')
                elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
                    field[name] = self._constructNEXTViscosityRatioInletOutletTDR(
                        self._db.getValue(xpath + '/turbulence/k-omega/turbulentViscosityRatio'))
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
                spec = self._db.getValue(xpath + '/wall/velocity/type')
                if spec == WallVelocityCondition.ATMOSPHERIC_WALL.value:
                    field[name] = self._constructAtmOmegaWallFunction()
                else:
                    field[name] = self._constructNEXTOmegaBlendedWallFunction()
            elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                field[name] = self._constructNEXTOmegaBlendedWallFunction()
            elif type_ == BoundaryType.SYMMETRY.value:
                field[name] = self._constructSymmetry()
            elif type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(xpath + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    field[name] = self._constructNEXTOmegaBlendedWallFunction()
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
        spec = self._db.getValue(xpath + '/turbulence/k-omega/specification')
        if spec == KOmegaSpecification.K_AND_OMEGA.value:
            return self._constructInletOutlet(
                self._db.getValue(xpath + '/turbulence/k-omega/specificDissipationRate'), self._initialValue)
        elif spec == KOmegaSpecification.INTENSITY_AND_VISCOSITY_RATIO.value:
            return self._constructNEXTViscosityRatioInletOutletTDR(
                self._db.getValue(xpath + '/turbulence/k-omega/turbulentViscosityRatio'))

    def _constructNEXTOmegaBlendedWallFunction(self):
        return {
            'type': 'NEXT::omegaBlendedWallFunction',
            'value': ('uniform', self._initialValue)
        }

    def _constructAtmOmegaWallFunction(self):
        return {
            'type': 'atmOmegaWallFunction',
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength'),
            'd': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/minimumZCoordinate')
        }
