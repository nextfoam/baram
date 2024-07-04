#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile
from libbaram.simple_db.simple_db import elementToVector

from baramMesh.app import app
from baramMesh.db.configurations_schema import GeometryType, Shape, CFDType, ThicknessModel, FeatureSnapType
from baramMesh.db.configurations_schema import GapRefinementMode


def boolToText(value):
    return 'true' if value else 'false'


class SnappyHexMeshDict(DictionaryFile):
    def __init__(self, castellationMesh=False, snap=False, addLayers=False):
        super().__init__(app.fileSystem.caseRoot(), self.systemLocation(), 'snappyHexMeshDict')

        self._casterllationMesh = castellationMesh
        self._snap = snap
        self._addLayers = addLayers

    def build(self):
        if self._data is not None:
            return self

        self._data = {
            'castellatedMesh': boolToText(self._casterllationMesh),
            'snap': boolToText(self._snap),
            'addLayers': boolToText(self._addLayers),
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
                'locationInMesh': list(app.db.getElements('region').values())[0].vector('point'),
                # 'faceZoneControls': self._constructFaceZoneControls()
            },
            'snapControls': {
                'nSmoothPatch': app.db.getValue('snap/nSmoothPatch'),
                'nSmoothInternal': app.db.getValue('snap/nSmoothInternal'),
                'tolerance': app.db.getValue('snap/tolerance'),
                'nSolveIter': app.db.getValue('snap/nSolveIter'),
                'nRelaxIter': app.db.getValue('snap/nRelaxIter'),
                'implicitFeatureSnap':
                    boolToText(app.db.getValue('snap/featureSnapType') == FeatureSnapType.IMPLICIT.value),
                'explicitFeatureSnap':
                    boolToText(app.db.getValue('snap/featureSnapType') == FeatureSnapType.EXPLICIT.value),
                'nFeatureSnapIter': app.db.getValue('snap/nFeatureSnapIter'),
                'multiRegionFeatureSnap': app.db.getValue('snap/multiRegionFeatureSnap'),
                'concaveAngle': app.db.getValue('snap/concaveAngle'),
                'minAreaRatio': app.db.getValue('snap/minAreaRatio')
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
                'geometry', lambda i, e: e['cfdType'] == CFDType.INTERFACE.value and not e['interRegion']).values():
            self._data['castellatedMeshControls']['refinementSurfaces'][interface.value('name')]['faceType'] = (
                'boundary' if interface.value('nonConformal') else 'baffle')

        return self

    def _constructGeometries(self):
        data = {}
        geometries = app.db.getElements('geometry')
        for gId, geometry in geometries.items():
            volume = geometries[geometry.value('volume')] if geometry.value('volume') else geometry
            if (geometry.value('cfdType') != CFDType.NONE.value
                    or geometry.value('castellationGroup')
                    or volume.value('cfdType') != CFDType.NONE.value):
                shape = geometry.value('shape')

                if shape == Shape.TRI_SURFACE_MESH.value:
                    data[geometry.value('name') + '.stl'] = {
                        'type': 'triSurfaceMesh',
                        'name': geometry.value('name')
                    }
                elif shape == Shape.HEX.value:
                    data[geometry.value('name')] = {
                        'type': 'searchableBox',
                        'min': volume.vector('point1'),
                        'max': volume.vector('point2')
                    }
                elif shape == Shape.HEX6.value:
                    if not app.window.geometryManager.isBoundingHex6(gId):
                        data[geometry.value('name')] = {
                            'type': 'searchableBox',
                            'min': volume.vector('point1'),
                            'max': volume.vector('point2')
                        }
                elif shape == Shape.SPHERE.value:
                    data[geometry.value('name')] = {
                        'type': 'searchableSphere',
                        'centre': volume.vector('point1'),
                        'radius': volume.value('radius')
                    }
                elif shape == Shape.CYLINDER.value:
                    data[geometry.value('name')] = {
                        'type': 'searchableCylinder',
                        'point1': volume.vector('point1'),
                        'point2': volume.vector('point2'),
                        'radius': volume.value('radius')
                    }
                elif shape in Shape.PLATES.value:
                    if not app.window.geometryManager.isBoundingHex6(gId):
                        x1, y1, z1 = volume.vector('point1')
                        x2, y2, z2 = volume.vector('point2')
                        xs, ys, zs = x2 - x1, y2 - y1, z2 - z1

                        if shape == Shape.X_MIN.value:
                            data[geometry.value('name')] = {
                                'type': 'searchablePlate',
                                'origin': [x1, y1, z1],
                                'span': [0, ys, zs]
                            }
                        elif shape == Shape.X_MAX.value:
                            data[geometry.value('name')] = {
                                'type': 'searchablePlate',
                                'origin': [x2, y1, z1],
                                'span': [0, ys, zs]
                            }
                        elif shape == Shape.Y_MIN.value:
                            data[geometry.value('name')] = {
                                'type': 'searchablePlate',
                                'origin': [x1, y1, z1],
                                'span': [xs, 0, zs]
                            }
                        elif shape == Shape.Y_MAX.value:
                            data[geometry.value('name')] = {
                                'type': 'searchablePlate',
                                'origin': [x1, y2, z1],
                                'span': [xs, 0, zs]
                            }
                        elif shape == Shape.Z_MIN.value:
                            data[geometry.value('name')] = {
                                'type': 'searchablePlate',
                                'origin': [x1, y1, z1],
                                'span': [xs, ys, 0]
                            }
                        elif shape == Shape.Z_MAX.value:
                            data[geometry.value('name')] = {
                                'type': 'searchablePlate',
                                'origin': [x1, y1, z2],
                                'span': [xs, ys, 0]
                            }

        return data

    def _constructFeatures(self):
        data = []

        boundingHex6 = app.db.getValue('baseGrid/boundingHex6')  # can be "None"
        refinements = app.db.getElements('castellation/refinementSurfaces')
        for surface in app.db.getElements('geometry', lambda i, e: e['gType'] == GeometryType.SURFACE.value).values():
            if surface.value('shape') in Shape.PLATES.value and surface.value('volume') == boundingHex6:
                continue

            group = surface.value('castellationGroup')
            data.append({
                'file': '"' + surface.value('name') + '.obj' + '"',
                'level': refinements[group].value('featureEdgeRefinementLevel') if group in refinements else 0
            })

        return data

    def _constructRefinementSurfaces(self):
        data = {}

        boundingHex6 = app.db.getValue('baseGrid/boundingHex6')  # can be "None"
        refinements = app.db.getElements('castellation/refinementSurfaces')

        cellZones = app.db.getElements(
            'geometry', lambda i, e: e['gType'] == GeometryType.VOLUME.value and e['cfdType'] != CFDType.NONE.value)

        # Target is a boundary, interface, or surface included in a castellation group
        surfaces = app.db.getElements(
            'geometry',
            lambda i, e: e['gType'] == GeometryType.SURFACE.value
                         and (e['cfdType'] != CFDType.NONE.value or e['castellationGroup'] or e['volume'] in cellZones))

        for surface in surfaces.values():
            if surface.value('shape') in Shape.PLATES.value and surface.value('volume') == boundingHex6:
                continue

            minLevel = 0
            maxLevel = 0
            if group := surface.value('castellationGroup'):
                minLevel = int(refinements[group].element('surfaceRefinement').value('minimumLevel'))
                maxLevel = int(refinements[group].element('surfaceRefinement').value('maximumLevel'))

            name = surface.value('name')
            cfdType = surface.value('cfdType')

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
                if self._addLayers or surface.value('interRegion'):
                    faceType = 'boundary' if surface.value('nonConformal') else 'baffle'
                else:
                    faceType = 'internal'

                data[name] = {
                    'faceZone': name,
                    'faceType': faceType,
                    'patchInfo': {'type': 'patch'}
                }

            data[name]['level'] = [minLevel, maxLevel]

        return data

    def _constructRefinementRegions(self):
        groups = app.db.getElements('castellation/refinementVolumes')

        volumes = {key: [] for key in groups}
        for geometry in app.db.getElements(
                'geometry', lambda i, e: e['gType'] == GeometryType.VOLUME.value and e['castellationGroup']).values():
            group = geometry.value('castellationGroup')
            if group in volumes:
                volumes[group].append(geometry)

        data = {}
        for group, refinement in groups.items():
            for volume in volumes[group]:
                data[volume.value('name')] = {
                    'mode': 'inside',
                    'levels': [[1E15, refinement.value('volumeRefinementLevel')]],
                }

                gapRefinement = refinement.element('gapRefinement')
                gapMode = gapRefinement.value('direction')
                if gapMode != GapRefinementMode.NONE.value:
                    data[volume.value('name')]['gapLevel'] = [
                        gapRefinement.value('minCellLayers'),
                        gapRefinement.value('detectionStartLevel'),
                        gapRefinement.value('maxRefinementLevel')]
                    data[volume.value('name')]['gapMode'] = gapMode
                    data[volume.value('name')]['gapSelf'] = 'true' if gapRefinement.value('gapSelf') else 'false'

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
            data[name] = {'nSurfaceLayers': layer.value('nSurfaceLayers')}
            data[name].update(thickness)

        if not self._addLayers:
            return {}

        groups = app.db.getElements('addLayers/layers')

        boundaries = {key: [] for key in groups}
        slaves = {key: [] for key in groups}
        for geometry in app.db.getElements('geometry', lambda i, e: e['layerGroup'] or e['slaveLayerGroup']).values():
            if group := geometry.value('layerGroup'):
                boundaries[group].append(geometry)
            if group := geometry.value('slaveLayerGroup'):
                slaves[group].append(geometry)

        data = {}
        for group, layer in groups.items():
            thickness = self._addLayerThickness(layer)
            for boundary in boundaries[group]:
                addLayerDictionary(boundary.value('name'), layer, thickness)
            for boundary in slaves[group]:
                addLayerDictionary(f'{boundary.value("name")}_slave', layer, thickness)

        return data

    def _addLayerThickness(self, thickness):
        data = {}

        model = thickness.value('thicknessModel')
        data['thicknessModel'] = model

        if model != ThicknessModel.FIRST_AND_RELATIVE_FINAL.value:
            data['relativeSizes'] = 'on' if thickness.value('relativeSizes') else 'off'

        if model in (ThicknessModel.FIRST_AND_EXPANSION.value,
                     ThicknessModel.FINAL_AND_EXPANSION.value,
                     ThicknessModel.OVERALL_AND_EXPANSION.value):
            data['expansionRatio'] = thickness.value('expansionRatio')

        if model in (ThicknessModel.FINAL_AND_OVERALL.value,
                     ThicknessModel.FINAL_AND_EXPANSION.value,
                     ThicknessModel.FIRST_AND_RELATIVE_FINAL.value):
            data['finalLayerThickness'] = thickness.value('finalLayerThickness')

        if model in (ThicknessModel.FIRST_AND_OVERALL.value,
                     ThicknessModel.FIRST_AND_EXPANSION.value,
                     ThicknessModel.FIRST_AND_RELATIVE_FINAL.value):
            data['firstLayerThickness'] = thickness.value('firstLayerThickness')

        if model in (ThicknessModel.FIRST_AND_OVERALL.value,
                     ThicknessModel.FINAL_AND_OVERALL.value,
                     ThicknessModel.OVERALL_AND_EXPANSION.value):
            data['thickness'] = thickness.value('thickness')

        data['minThickness'] = thickness.value('minThickness')

        return data



