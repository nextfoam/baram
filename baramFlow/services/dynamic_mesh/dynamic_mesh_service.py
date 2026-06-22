#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock

from bidict import bidict

from baramFlow.base.dynamic_mesh.dynamic_mesh import DYNAMIC_MESH_PATH, DynamicMesh, MotionType
from baramFlow.base.dynamic_mesh.moving_boundary import MovingBoundaryEntry, PointMotionType
from baramFlow.base.event_bus import EventBus, RegionComponents
from baramFlow.coredb import coredb

from baramFlow.coredb.boundary_db import BoundaryDB, BoundaryType


_mutex = Lock()


CONSTRAINT_BOUNDARY_TYPE_MAP = {
    BoundaryType.POROUS_JUMP: PointMotionType.CYCLIC,
    BoundaryType.FAN:         PointMotionType.CYCLIC,
    BoundaryType.SYMMETRY:    PointMotionType.SYMMETRY,
    BoundaryType.INTERFACE:   PointMotionType.CYCLIC,
    BoundaryType.EMPTY:       PointMotionType.EMPTY,
    BoundaryType.CYCLIC:      PointMotionType.CYCLIC,
    BoundaryType.CYCLIC_ACMI: PointMotionType.CYCLIC,
    BoundaryType.WEDGE:       PointMotionType.WEDGE,
}

class DynamicMeshService:
    GRAPHICS_PATH = '/graphics'

    def __new__(cls, *args, **kwargs):
        with _mutex:
            if not hasattr(cls, '_instance'):
                cls._instance = super(DynamicMeshService, cls).__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self):
        with _mutex:
            if hasattr(self, '_initialized'):
                return
            else:
                self._initialized = True

        EventBus().onMeshLoading.asyncConnect(self._handleMeshUpdate)
        EventBus().onProjectOpen.asyncConnect(self._handleProjectOpen)
        EventBus().onProjectClose.asyncConnect(self._handleProjectClose)
        EventBus().onBoundaryTypeChange.asyncConnect(self._handleBoundaryTypeChange)

        EventBus().onSaving.connect(self._handleSave)

        self._dynamicMesh = DynamicMesh()

    def getDynamicMesh(self):
        return self._dynamicMesh

    async def load(self):
        db = coredb.CoreDB()
        self._dynamicMesh.replaceWith(DynamicMesh.fromElement(db.getElement(DYNAMIC_MESH_PATH)))
        # ToDo: For compatibility. Remove this code block after 20271231
        # Add boundaries to moving boundary list
        # Begin
        if len(self._dynamicMesh.movingBoundaries) == 0:
            rnames = db.getRegions()

            if len(rnames) == 1:  # Dynamic Mesh does not support multi-region
                boundaries = [str(bcid) for bcid, bcname, typeStr in db.getBoundaryConditions(rnames[0])]
                self._dynamicMesh.movingBoundaries = self._generateMovingBoundaries(boundaries)
        # End

    def saveToCoreDB(self):
        coredb.CoreDB().replaceElement(DYNAMIC_MESH_PATH, self._dynamicMesh.toElement('dynamicMesh'))

    async def _handleProjectOpen(self):
        await self.load()

    async def _handleProjectClose(self):
        self._dynamicMesh.replaceWith(DynamicMesh())

    async def _handleMeshUpdate(self,
                                oldMesh: dict[str, RegionComponents],
                                newMesh: dict[str, RegionComponents]):

        if len(newMesh) == 0:
            return

        # dynamic mesh does not support multi-region
        if len(newMesh) > 1:
            self._dynamicMesh.replaceWith(DynamicMesh())
            return

        newDefaultRegion = list(newMesh.values())[0]
        newBoundaries = bidict(newDefaultRegion['boundaries'])
        newCellZones  = bidict(newDefaultRegion['cellZones'])

        if len(oldMesh) == 0:
            self._dynamicMesh.replaceWith(DynamicMesh())
            boundaries = [bcid for bcname, bcid in newBoundaries.items()]
            self._dynamicMesh.movingBoundaries = self._generateMovingBoundaries(boundaries)
            return

        oldDefaultRegion = list(oldMesh.values())[0]
        oldBoundaries = bidict(oldDefaultRegion['boundaries'])
        oldCellZones  = bidict(oldDefaultRegion['cellZones'])

        for md in self._dynamicMesh.motionDefinitions:
            md.processMeshUpdate(oldCellZones, newCellZones)

        newMovingBoundaries: list[MovingBoundaryEntry] = []
        for bcname, bcid in newBoundaries.items():
            if bcname in oldBoundaries:
                mb = next(mb for mb in self._dynamicMesh.movingBoundaries if mb.boundary == oldBoundaries[bcname])
            else:
                mb = MovingBoundaryEntry(boundary=bcid)

            newMovingBoundaries.append(mb)

        self._dynamicMesh.movingBoundaries = newMovingBoundaries

        for body in self._dynamicMesh.rigidBodyDynamics.bodies:
            body.processMeshUpdate(oldBoundaries, newBoundaries)

    # This method is left here just to leave a scaffold for future evolution
    async def _handleBoundaryTypeChange(self, bcid: str, oldType: BoundaryType, newType: BoundaryType):
        boundaryEntry = next((be for be in self._dynamicMesh.movingBoundaries if be.boundary == bcid), None)
        if boundaryEntry is None:
            raise AssertionError

    def _handleSave(self):
        self.saveToCoreDB()

    def _generateMovingBoundaries(self, boundaries: list[str]):
        movingBoundaries = []
        for bcid in boundaries:
            mb = MovingBoundaryEntry(boundary=str(bcid))
            movingBoundaries.append(mb)

        return movingBoundaries

# Auto-instantiate the singleton so that event bus connections are established at import time
_instance = DynamicMeshService()
