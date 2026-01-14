#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from typing import Optional

from baramFlow.openfoam.file_system import FileSystem
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile


class SetType(Enum):
    POINT = 'pointSet'
    FACE  = 'faceSet'
    CELL  = 'cellSet'
    POINT_ZONE = 'pointZoneSet'
    FACE_ZONE  = 'faceZoneSet'
    CELL_ZONE  = 'cellZoneSet'


class ActionType(Enum):
    ADD      = 'add'
    SUBTRACT = 'subtract'
    NEW      = 'new'
    SUBSET   = 'subset'
    INVERT   = 'invert'
    CLEAR    = 'clear'
    REMOVE   = 'remove'
    LIST     = 'list'
    IGNORE   = 'ignore'
    DELETE   = 'delete'


class SourceType(Enum):
    # pointSet

    BOX_TO_POINT       = 'boxToPoint'
    CELL_TO_POINT      = 'cellToPoint'
    CLIP_PLANE_TO_POINT = 'clipPlaneToPoint'
    CYLINDER_TO_POINT  = 'cylinderToPoint'
    FACE_TO_POINT      = 'faceToPoint'
    LABEL_TO_POINT     = 'labelToPoint'
    NEAREST_TO_POINT   = 'nearestToPoint'
    POINT_TO_POINT     = 'pointToPoint'
    SEARCHABLE_SURFACE_TO_POINT = 'searchableSurfaceToPoint'
    SET_TO_POINTZONE   = 'setToPointZone'
    SPHERE_TO_POINT    = 'sphereToPoint'
    SURFACE_TO_POINT   = 'surfaceToPoint'
    ZONE_TO_POINT      = 'zoneToPoint'

    # faceSet

    BOX_TO_FACE        = 'boxToFace'
    CELL_TO_FACE       = 'cellToFace'
    CLIP_PLANE_TO_FACE = 'clipPlaneToFace'
    CYLINDER_ANNULUS_TO_FACE = 'cylinderAnnulusToFace'
    CYLINDER_TO_FACE   = 'cylinderToFace'
    FACE_TO_FACE       = 'faceToFace'
    HOLE_TO_FACE       = 'holeToFace'
    LABEL_TO_FACE      = 'labelToFace'
    NORMAL_TO_FACE     = 'normalToFace'
    PATCH_TO_FACE      = 'patchToFace'
    POINT_TO_FACE      = 'pointToFace'
    REGION_TO_FACE     = 'regionToFace'
    SEARCHABLE_SURFACE_TO_FACE = 'searchableSurfaceToFace'
    SPHERE_TO_FACE     = 'sphereToFace'
    ZONE_TO_FACE       = 'zoneToFace'

    # faceZoneSet

    CELL_TO_FACEZONE     = 'cellToFaceZone'
    FACEZONE_TO_FACEZONE = 'faceZoneToFaceZone'
    PLANE_TO_FACEZONE    = 'planeToFaceZone'
    SEARCHABLESURFACE_TO_FACEZONE = 'searchableSurfaceToFaceZone'
    SETANDNORMAL_TO_FACEZONE = 'setAndNormalToFaceZone'
    SET_TO_FACEZONE      = 'setToFaceZone'
    SETS_TO_FACEZONE     = 'setsToFaceZone'

    # cellSet

    BOX_TO_CELL          = 'boxToCell'
    CELL_TO_CELL         = 'cellToCell'
    CLIP_PLANE_TO_CELL   = 'clipPlaneToCell'
    CYLINDER_ANNULUS_TO_CELL = 'cylinderAnnulusToCell'
    CYLINDER_TO_CELL     = 'cylinderToCell'
    FACE_TO_CELL         = 'faceToCell'
    FACEZONE_TO_CELL     = 'faceZoneToCell'
    FIELD_TO_CELL        = 'fieldToCell'
    HALO_TO_CELL         = 'haloToCell'
    LABEL_TO_CELL        = 'labelToCell'
    NBR_TO_CELL          = 'nbrToCell'
    NEAREST_TO_CELL      = 'nearestToCell'
    PATCH_TO_CELL        = 'patchToCell'
    POINT_TO_CELL        = 'pointToCell'
    REGION_TO_CELL       = 'regionToCell'
    ROTATED_BOX_TO_CELL  = 'rotatedBoxToCell'
    SEARCHABLE_SURFACE_TO_CELL = 'searchableSurfaceToCell'
    SHAPE_TO_CELL        = 'shapeToCell'
    SPHERE_TO_CELL       = 'sphereToCell'
    SURFACE_TO_CELL      = 'surfaceToCell'
    TARGET_VOLUME_TO_CELL = 'targetVolumeToCell'
    ZONE_TO_CELL         = 'zoneToCell'

    # cellZoneSet

    SET_TO_CELLZONE = 'setToCellZone'




def topoOp(name: str, type_: SetType, action: ActionType, source: Optional[SourceType] = None, options: dict = {}):
    data: dict = {
        'name': name,
        'type': type_.value,
        'action': action.value,
    }

    if source:
        data['source'] = source.value
        data.update(options)

    return data


class TopoSetDict(DictionaryFile):
    def __init__(self, rname: str = ''):
        super().__init__(FileSystem.caseRoot(), self.systemLocation(rname), 'topoSetDict')
        self._rname = rname
        self._actions = []

    def build(self):
        if self._data is not None:
            return self

        if self._actions:
            self._data = {
                'actions': self._actions
            }

        return self

    def setupCoupleSets(self, couples: dict[str, tuple[str, str]]):
        """Set face sets for coupled boundaries

        Set face sets for coupled boundaries.
        Each face set has two patches that are couple.
        This face sets will be used as "singleProcessorFaceSets" constraint in decomposeParDict.

        Args:
            couples: dict where key is the name of face set and value is a tuple of the two coupled patches.
                    {
                        <faceSetName> : (<patch1>, <patch2>),
                        # ...
                    }
        Raises:
            LookupError: Less or more than one item are matched
            ValueError: Invalid configuration value
            RuntimeError: Called not in "with" context
        """
        for k, v in couples.items():
            self._actions.append(topoOp(k, SetType.FACE, ActionType.NEW, SourceType.PATCH_TO_FACE, {'patches': list(v)}))

        return self