#!/usr/bin/env python
# -*- coding: utf-8 -*-

from coredb import coredb
from view.setup.boundary_conditions.boundary_db import BoundaryListIndex, BoundaryDB, BoundaryType
from view.setup.boundary_conditions.boundary_db import WallVelocityCondition, InterfaceMode
from view.setup.models.models_db import ModelsDB, TurbulenceModel
from openfoam.boundary_conditions.boundary_condition import BoundaryCondition


class Nut(BoundaryCondition):
    DIMENSIONS = '[0 2 -1 0 0 0 0]'

    def __init__(self, rname: str):
        super().__init__(self.boundaryLocation(rname), 'nut')

        self._rname = rname
        self._db = coredb.CoreDB()
        # ToDo: Set initialValue
        self._initialValue = 0
        self._model = ModelsDB.getTurbulenceModel()

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
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.FLOW_RATE_INLET.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.PRESSURE_INLET.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.PRESSURE_OUTLET.value:
                if self._db.getValue(xpath + '/pressureOutlet/calculatedBackflow') == 'true':
                    field[name] = self._constructCalculated(self._initialValue)
                else:
                    field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.ABL_INLET.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.OPEN_CHANNEL_INLET.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.OPEN_CHANNEL_OUTLET.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.OUTFLOW.value:
                field[name] = self._constructZeroGradient()
            elif type_ == BoundaryType.FREE_STREAM.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.FAR_FIELD_RIEMANN.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.SUBSONIC_INFLOW.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.SUBSONIC_OUTFLOW.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.SUPERSONIC_INFLOW.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.SUPERSONIC_OUTFLOW.value:
                field[name] = self._constructCalculated(self._initialValue)
            elif type_ == BoundaryType.WALL.value:
                spec = self._db.getValue(xpath + '/wall/velocity/type')
                if spec == WallVelocityCondition.ATMOSPHERIC_WALL.value:
                    field[name] = self._constructAtmNutkWallFunction(xpath + '/wall')
                else:
                    field[name] = self._constructWallFunctionByModel()
            elif type_ == BoundaryType.THERMO_COUPLED_WALL.value:
                field[name] = self._constructWallFunctionByModel()
            elif type_ == BoundaryType.SYMMETRY.value:
                field[name] = self._constructSymmetry()
            elif type_ == BoundaryType.INTERFACE.value:
                spec = self._db.getValue(xpath + '/interface/mode')
                if spec == InterfaceMode.REGION_INTERFACE.value:
                    field[name] = self._constructWallFunctionByModel()
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

    def _constructWallFunctionByModel(self):
        if self._model == TurbulenceModel.K_EPSILON:
            return self._constructNEXTNutkWallFunction()
        elif self._model == TurbulenceModel.K_OMEGA:
            return self._constructNEXTNutSpaldingWallFunction()

    def _constructNEXTNutkWallFunction(self):
        return {
            'type': 'NEXT::nutkWallFunction',
            'value': ('uniform', self._initialValue)
        }

    def _constructNEXTNutSpaldingWallFunction(self):
        return {
            'type': 'NEXT::nutSpaldingWallFunction',
            'value': ('uniform', self._initialValue)
        }

    def _constructAtmNutkWallFunction(self, xpath):
        return {
            'type': 'atmNutkWallFunction',
            'z0': self._db.getValue(BoundaryDB.ABL_INLET_CONDITIONS_XPATH + '/surfaceRoughnessLength')
        }
