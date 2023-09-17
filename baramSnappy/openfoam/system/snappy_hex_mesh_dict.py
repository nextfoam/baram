#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramSnappy.app import app
from baramSnappy.db.configurations_schema import GeometryType, Shape, CFDType, ThicknessModel
from baramSnappy.db.simple_db import elementToVector
from baramSnappy.openfoam.dictionary_file import DictionaryFile


class SnappyHexMeshDict(DictionaryFile):
    def __init__(self, castellationMesh=False, snap=False, addLayers=False):
        super().__init__()
        self._setHeader(self.systemLocation(), 'snappyHexMeshDict')

        self._casterllationMesh = castellationMesh
        self._snap = snap
        self._addLayers = addLayers

        self._geometries = None

    def build(self):
        if self._data is not None:
            return self

        self._geometries = app.db.getElements('geometry')

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
                'locationInMesh': elementToVector(list(app.db.getElements('region').values())[0]['point']),
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
            'addLayersControls': self._constructAddLayerControls(),
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

    def updateForCellZoneInterfacesSnap(self):
        if self._data is None:
            return self

        for interface in app.db.getElements(
                'geometry',
                lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and not e['interRegion'], ['name']).values():
            self._data['castellatedMeshControls']['refinementSurfaces'][interface['name']]['faceType'] = 'baffle'

        return self

    def _constructGeometries(self):
        data = {}

        for gId, geometry in self._geometries.items():
            if geometry['cfdType'] != CFDType.NONE.value:
                volume = self._geometries[geometry['volume']] if geometry['volume'] else geometry
                shape = geometry['shape']

                if shape == Shape.TRI_SURFACE_MESH.value:
                    data[geometry['name'] + '.stl'] = {
                        'type': 'triSurfaceMesh',
                        'name': geometry['name']
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

        return data

    def _constructFeatures(self):
        surfaces = {}
        for geometry in app.db.getElements(
                'geometry', lambda i, e: e['gType'] == GeometryType.SURFACE.value and e['castellationGroup'],
                ['name', 'castellationGroup']).values():
            group = geometry['castellationGroup']
            if group in surfaces:
                surfaces[group].append(geometry)
            else:
                surfaces[group] = [geometry]

        data = []
        for group, refinement in app.db.getElements('castellation/refinementSurfaces').items():
            if level := int(refinement['featureEdgeRefinementLevel']):
                for surface in surfaces[group]:
                    data.append({
                        'file': surface['name'] + '.obj',
                        'levels': [[0.01, level]]
                    })

        return data

    def _constructRefinementSurfaces(self):
        data = {}

        refinements = app.db.getElements('castellation/refinementSurfaces')
        # Target is a boundary, interface, or surface included in a castellation group
        surfaces = app.db.getElements(
            'geometry',
            lambda i, e: e['gType'] == GeometryType.SURFACE.value
                         and (e['cfdType'] != CFDType.NONE.value or e['castellationGroup']),
            ['name', 'cfdType', 'nonConformal', 'interRegion', 'castellationGroup'])

        for surface in surfaces.values():
            level = 0
            if group := surface['castellationGroup']:
                level = int(refinements[group]['surfaceRefinementLevel'])

            name = surface['name']
            cfdType = surface['cfdType']

            if cfdType == CFDType.NONE.value:
                data[name] = {
                    'faceZone': name,
                    'faceType': 'internal'
                }
            elif cfdType == CFDType.BOUNDARY.value:
                data[name] = {
                    'patchInfo': {'type': 'patch'}
                }
            else:
                if self._addLayers or surface['interRegion']:
                    faceType = 'boundary' if surface['nonConformal'] else 'baffle'
                else:
                    faceType = 'internal'

                data[name] = {
                    'faceZone': name,
                    'faceType': faceType,
                    'patchInfo': {'type': 'patch'}
                }

            data[name]['level'] = [level, level]

        return data

    def _constructRefinementRegions(self):
        groups = app.db.getElements('castellation/refinementVolumes')

        volumes = {key: [] for key in groups}
        for geometry in app.db.getElements(
                'geometry', lambda i, e: e['gType'] == GeometryType.VOLUME.value and e['castellationGroup'],
                ['name', 'castellationGroup']).values():
            group = geometry['castellationGroup']
            if group in volumes:
                volumes[group].append(geometry)

        data = {}
        for group, refinement in groups.items():
            for volume in volumes[group]:
                data[volume['name']] = {
                    'mode': 'inside',
                    'levels': [[1E15, refinement['volumeRefinementLevel']]]
                }

        return data

    def _constructLocationsInMesh(self):
        data = []
        for region in app.db.getElements('region').values():
            data.append([elementToVector(region['point']), region['name']])

        return data

    def _constructAddLayerControls(self):
        db = app.db.checkout('addLayers')

        data = {
            'layers': self._constructLayers(),
            'nGrow': db.getValue('nGrow'),
            'featureAngle': db.getValue('featureAngle'),
            'maxFaceThicknessRatio': db.getValue('maxFaceThicknessRatio'),
            'nSmoothSurfaceNormals': db.getValue('nSmoothSurfaceNormals'),
            'nSmoothThickness': db.getValue('nSmoothThickness'),
            'minMedialAxisAngle': db.getValue('minMedialAxisAngle'),
            'maxThicknessToMedialRatio': db.getValue('maxThicknessToMedialRatio'),
            'nSmoothNormals': db.getValue('nSmoothNormals'),
            'slipFeatureAngle': db.getValue('slipFeatureAngle'),
            'nRelaxIter': db.getValue('nRelaxIter'),
            'nBufferCellsNoExtrude': db.getValue('nBufferCellsNoExtrude'),
            'nLayerIter': db.getValue('nLayerIter'),
            'nRelaxedIter': db.getValue('nRelaxedIter'),
            'thicknessModel': 'finalAndExpansion',
            'relativeSizes': 'on',
            'finalLayerThickness': 0.5,
            'expansionRatio': 1.2,
            'minThickness': 0.3
        }

        return data

    def _constructLayers(self):
        def addLayerDictionary(name, layer, thickness):
            data[name] = {'nSurfaceLayers': layer['nSurfaceLayers']}
            data[name].update(thickness)

        if not self._addLayers:
            return {}

        groups = app.db.getElements('addLayers/layers')

        boundaries = {key: [] for key in groups}
        slaves = {key: [] for key in groups}
        for geometry in app.db.getElements(
                'geometry', lambda i, e: e['layerGroup'] or e['slaveLayerGroup'],
                ['name', 'layerGroup', 'slaveLayerGroup']).values():
            if group := geometry['layerGroup']:
                boundaries[group].append(geometry)
            if group := geometry['slaveLayerGroup']:
                slaves[group].append(geometry)

        data = {}
        for group, layer in groups.items():
            thickness = self._addLayerThickness(layer)
            for boundary in boundaries[group]:
                addLayerDictionary(boundary['name'], layer, thickness)
            for boundary in slaves[group]:
                addLayerDictionary(f'{boundary["name"]}_slave', layer, thickness)

        return data

    def _addLayerThickness(self, thickness):
        data = {}

        model = thickness['thicknessModel']
        data['thicknessModel'] = model

        if model != ThicknessModel.FIRST_AND_RELATIVE_FINAL.value:
            data['relativeSizes'] = 'on' if thickness['relativeSizes'] else 'off'

        if model in (ThicknessModel.FIRST_AND_EXPANSION.value,
                     ThicknessModel.FINAL_AND_EXPANSION.value,
                     ThicknessModel.OVERALL_AND_EXPANSION.value):
            data['expansionRatio'] = thickness['expansionRatio']

        if model in (ThicknessModel.FINAL_AND_OVERALL.value,
                     ThicknessModel.FINAL_AND_EXPANSION.value,
                     ThicknessModel.FIRST_AND_RELATIVE_FINAL.value):
            data['finalLayerThickness'] = thickness['finalLayerThickness']

        if model in (ThicknessModel.FIRST_AND_OVERALL.value,
                     ThicknessModel.FIRST_AND_EXPANSION.value,
                     ThicknessModel.FIRST_AND_RELATIVE_FINAL.value):
            data['firstLayerThickness'] = thickness['firstLayerThickness']

        if model in (ThicknessModel.FIRST_AND_OVERALL.value,
                     ThicknessModel.FINAL_AND_OVERALL.value,
                     ThicknessModel.OVERALL_AND_EXPANSION.value):
            data['thickness'] = thickness['thickness']

        data['minThickness'] = thickness['minThickness']

        return data



