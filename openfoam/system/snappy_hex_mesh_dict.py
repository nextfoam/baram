#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app
from db.configurations_schema import GeometryType, Shape, CFDType
from db.simple_db import elementToVector
from openfoam.dictionary_file import DictionaryFile


class SnappyHexMeshDict(DictionaryFile):
    def __init__(self, castellationMesh=False, snap=False, addLayers=False):
        super().__init__(self.systemLocation(), 'snappyHexMeshDict')

        self._casterllationMesh = castellationMesh
        self._snap = snap
        self._addLayers = addLayers

        self._volumes = []
        self._surfaces = []

    def build(self):
        if self._data is not None:
            return self

        self._data = {
            'castellatedMesh': 'true' if self._casterllationMesh else 'false',
            'snap': 'true' if self._snap else 'false',
            'addLayers': 'true' if self._addLayers else 'false',
            'geometry': self._constructGeometries(),
            'castellatedMeshControls': {
                'maxLocalCells': app.db.getValue('castellation/maxLocalCells'),
                'maxGlobalCells': app.db.getValue('castellation/maxGlobalCells'),
                'minRefinementCells': app.db.getValue('castellation/minRefinementCells'),
                'maxLoadUnbalance': app.db.getValue('castellation/maxLoadUnbalance'),
                'nCellsBetweenLevels': app.db.getValue('castellation/nCellsBetweenLevels'),
                'features': self._constructFeatures(),
                'refinementSurfaces': self._constructRefinementSurfaces(),
                'resolveFeatureAngle': app.db.getValue('castellation/resolveFeatureAngle'),
                'refinementRegions': self._constructRefinementRegions(),
                'allowFreeStandingZoneFaces': app.db.getValue('castellation/allowFreeStandingZoneFaces'),
                'locationsInMesh': self._constructLocationsInMesh(),
                # 'faceZoneControls': self._constructFaceZoneControls()
            },
            'snapControls': {
                'nSmoothPatch': app.db.getValue('snap/nSmoothPatch'),
                'nSmoothInternal': app.db.getValue('snap/nSmoothInternal'),
                'tolerance': app.db.getValue('snap/tolerance'),
                'nSolveIter': app.db.getValue('snap/nSolveIter'),
                'nRelaxIter': app.db.getValue('snap/nRelaxIter'),
                'nFeatureSnapIter': app.db.getValue('snap/nFeatureSnapIter'),
                'multiRegionFeatureSnap': app.db.getValue('snap/multiRegionFeatureSnap'),
                'concaveAngle': app.db.getValue('snap/concaveAngle'),
                'minAreaRation': app.db.getValue('snap/concaveAngle')
            },
            'addLayersControls': {
                'relativeSizes': app.db.getValue('addLayers/relativeSizes'),
                'expansionRatio': app.db.getValue('addLayers/expansionRatio'),
                'finalLayerThickness': app.db.getValue('addLayers/finalLayerThickness'),
                'firstLayerThickness': app.db.getValue('addLayers/firstLayerThickness'),
                'thickness': app.db.getValue('addLayers/thickness'),
                'minThickness': app.db.getValue('addLayers/minThickness'),

                'nGrow': app.db.getValue('addLayers/nGrow'),
                # 'featureAngle': app.db.getValue('addLayers/maxNonOrtho'),
                'maxFaceThicknessRatio': app.db.getValue('addLayers/maxFaceThicknessRatio'),
                'nSmoothSurfaceNormals': app.db.getValue('addLayers/nSmoothSurfaceNormals'),
                'nSmoothThickness': app.db.getValue('addLayers/nSmoothThickness'),
                'minMedialAxisAngle': app.db.getValue('addLayers/minMedialAxisAngle'),
                'maxThicknessToMedialRatio': app.db.getValue('addLayers/maxThicknessToMedialRatio'),
                'nSmoothNormals': app.db.getValue('addLayers/nSmoothNormals'),
                'slipFeatureAngle': app.db.getValue('addLayers/slipFeatureAngle'),
                'nRelaxIter': app.db.getValue('addLayers/nRelaxIter'),
                'nBufferCellsNoExtrude': app.db.getValue('addLayers/nBufferCellsNoExtrude'),
                'nLayerIter': app.db.getValue('addLayers/nLayerIter'),
                'nRelaxedIter': app.db.getValue('addLayers/nRelaxedIter'),
            },
            'meshQualityControls': {
                'maxNonOrtho': app.db.getValue('meshQuality/maxNonOrtho'),
                'maxBoundarySkewness': app.db.getValue('meshQuality/maxBoundarySkewness'),
                'maxInternalSkewness': app.db.getValue('meshQuality/maxInternalSkewness'),
                'maxConcave': app.db.getValue('meshQuality/maxConcave'),
                'minVol': app.db.getValue('meshQuality/minVol'),
                'minTetQuality': app.db.getValue('meshQuality/minTetQuality'),
                'minVolCollapseRatio': app.db.getValue('meshQuality/minVolCollapseRatio'),
                'minArea': app.db.getValue('meshQuality/minArea'),
                'minTwist': app.db.getValue('meshQuality/minTwist'),
                'minDeterminant': app.db.getValue('meshQuality/minDeterminant'),
                'minFaceWeight': app.db.getValue('meshQuality/minFaceWeight'),
                'minFaceFlatness': app.db.getValue('meshQuality/minFaceFlatness'),
                'minVolRatio': app.db.getValue('meshQuality/minVolRatio'),
                'minTriangleTwist': app.db.getValue('meshQuality/minTriangleTwist'),
                'relaxed': {
                    'maxNonOrtho': app.db.getValue('meshQuality/relaxed/maxNonOrtho')
                },
                'nSmoothScale': app.db.getValue('meshQuality/nSmoothScale'),
                'errorReduction': app.db.getValue('meshQuality/errorReduction')
            },
            'mergeTolerance': app.db.getValue('meshQuality/mergeTolerance')
        }

        return self

    def _constructGeometries(self):
        data = {}

        geometries = app.db.getElements('geometry')
        for gId, geometry in geometries.items():
            if geometry['cfdType'] != CFDType.NONE.value:
                volume = geometries[geometry['volume']] if geometry['volume'] else geometry
                shape = geometry['shape']

                if shape == Shape.TRI_SURFACE_MESH.value:
                    data[geometry['name'] + '.stl'] = {
                        'type': 'triSurfaceMesh',
                    }
                elif shape == Shape.HEX.value or shape == Shape.HEX6.value:
                    data[geometry['name']] = {
                        'type': 'searchableBox',
                        'min': elementToVector(volume['point1']),
                        'max': elementToVector(volume['point2'])
                    }
                elif shape == Shape.SPHERE.value:
                    data[geometry['name']] = {
                        'type': 'searchableSphere',
                        'centre': elementToVector(volume['point1']),
                        'radius': volume['radius']
                    }
                elif shape == Shape.CYLINDER.value:
                    data[geometry['name']] = {
                        'type': 'searchableCylinder',
                        'point1': elementToVector(volume['point1']),
                        'point2': elementToVector(volume['point2']),
                        'radius': volume['radius']
                    }
                elif shape in Shape.PLATES.value:
                    x1, y1, z1 = elementToVector(volume['point1'])
                    x2, y2, z2 = elementToVector(volume['point2'])
                    xo, yo, zo = (x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2
                    xs, ys, zs = x2 - x1, y2 - y1, z2 - z1

                    if shape == Shape.X_MIN.value:
                        data[geometry['name']] = {
                            'type': 'searchablePlate',
                            'origin': [x1, y1, z1],
                            'span': [0, ys, zs]
                        }
                    elif shape == Shape.X_MAX.value:
                        data[geometry['name']] = {
                            'type': 'searchablePlate',
                            'origin': [x2, y1, z1],
                            'span': [0, ys, zs]
                        }
                    elif shape == Shape.Y_MIN.value:
                        data[geometry['name']] = {
                            'type': 'searchablePlate',
                            'origin': [x1, y1, z1],
                            'span': [xs, 0, zs]
                        }
                    elif shape == Shape.Y_MAX.value:
                        data[geometry['name']] = {
                            'type': 'searchablePlate',
                            'origin': [x1, y2, z1],
                            'span': [xs, 0, zs]
                        }
                    elif shape == Shape.Z_MIN.value:
                        data[geometry['name']] = {
                            'type': 'searchablePlate',
                            'origin': [x1, y1, z1],
                            'span': [xs, ys, 0]
                        }
                    elif shape == Shape.Z_MAX.value:
                        data[geometry['name']] = {
                            'type': 'searchablePlate',
                            'origin': [x1, y1, z2],
                            'span': [xs, ys, 0]
                        }

                if geometry['gType'] == GeometryType.SURFACE.value:
                    self._surfaces.append((gId, geometry))
                else:
                    self._volumes.append((gId, geometry))

        return data

    def _constructFeatures(self):
        data = []
        for gId, surface in self._surfaces:
            if surface['shape'] not in (Shape.CYLINDER.value, Shape.SPHERE.value):
                data.append({
                    'file': surface['name'] + '.obj',
                    'levels': [[0.01, app.db.getValue(f'castellation/features/{gId}/level')]]
                })

        return data

    def _constructRefinementSurfaces(self):
        data = {}
        for gId, surface in self._surfaces:
            if surface['shape'] == Shape.TRI_SURFACE_MESH.value:
                name = surface['name'] + '.stl'
            else:
                name = surface['name']

            level = app.db.getValue(f'castellation/refinementSurfaces/{gId}/level')
            data[name] = {
                'level': [level, level],
                'patchInfo': {
                    'type': 'patch'
                }
            }

        return data

    def _constructRefinementRegions(self):
        data = {}
        for gId, volume in self._volumes:
            if volume['shape'] == Shape.TRI_SURFACE_MESH.value:
                name = volume['name'] + '.stl'
            else:
                name = volume['name']

            data[name] = {
                'mode': 'inside',
                'levels': [[1E15, app.db.getValue(f'castellation/refinementRegions/{gId}/level')]],
                'patchInfo': {
                    'type': 'patch'
                }
            }

        return data

    def _constructLocationsInMesh(self):
        data = []
        for region in app.db.getElements(f'region').values():
            data.append([elementToVector(region['point']), region['name']])

        return data
