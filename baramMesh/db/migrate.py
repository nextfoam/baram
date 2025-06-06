#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .configurations_schema import CURRENT_CONFIGURATIONS_VERSION, CONFIGURATIONS_VERSION_KEY
from .configurations_schema import FeatureSnapType, GapRefinementMode, BufferLayerPointSmoothingMethod


def _to_v1(data):
    # Loaded data has no version information. It is assumed as version 1.
    return


def _to_v2(data):
    if 'featureSnapType' not in data['snap']:
        data['snap']['featureSnapType'] = FeatureSnapType.EXPLICIT

    for surfaceRefinement in data['castellation']['refinementSurfaces'].values():
        if 'surfaceRefinement' not in surfaceRefinement:
            orgSurfaceRefinementLevel = surfaceRefinement.pop('surfaceRefinementLevel')
            surfaceRefinement['surfaceRefinement'] = {
                'minimumLevel': orgSurfaceRefinementLevel,
                'maximumLevel': str(int(orgSurfaceRefinementLevel) + 1)
            }

    value = data['snap'].pop('minAreaRation', None)
    if value is not None:
        data['snap']['minAreaRatio'] = value


def _to_v3(data):
    for refinementVolumes in data['castellation']['refinementVolumes'].values():
        if 'gapRefinement' not in refinementVolumes:
            refinementVolumes['gapRefinement'] = {
                'minCellLayers': '4',
                'detectionStartLevel': '1',
                'maxRefinementLevel': '2',
                'direction': GapRefinementMode.NONE,
                'gapSelf': True
            }


def _to_v4(data):
    for surfaceRefinement in data['castellation']['refinementSurfaces'].values():
        if 'curvatureRefinement' not in surfaceRefinement:
            surfaceRefinement['curvatureRefinement'] = {
                'disabled': True,
                'numberOfCells': '1',
                'maxLevel': '1',
                'excludeSharpSurface': False,
                'minRadius': '0'
            }


def _to_v5(data):
    for geometry in data['geometry'].values():
        if 'addBufferLayers' not in geometry:
            geometry['addBufferLayers'] = False
            
    for volumeRefinement in data['castellation']['refinementVolumes'].values():
        if 'levelIncrement' not in volumeRefinement:
            volumeRefinement['levelIncrement'] = {
                'disabled': True,
                'splitCountX': 1,
                'splitCountY': 0,
                'splitCountZ': 0,
                'minLevel': 0,
                'maxLevel': 10
            }
            
    if 'bufferLayer' not in data['snap']:
        data['snap']['bufferLayer'] = {
            'disabled': True,
            'pointSmoothingMethod': BufferLayerPointSmoothingMethod.LAPLACIAN,
            'numberOfPointSmoothingIteration': 10,
            'GETMeTransformationParameter': 0.667
        }


_migrates = {
    0: _to_v1,
    1: _to_v2,
    2: _to_v3,
    3: _to_v4,
    4: _to_v5,
}


def migrate(data):
    version = int(data.get(CONFIGURATIONS_VERSION_KEY, 0))
    assert version <= CURRENT_CONFIGURATIONS_VERSION

    for v in range(version, len(_migrates)):
        _migrates[v](data)

    data[CONFIGURATIONS_VERSION_KEY] = CURRENT_CONFIGURATIONS_VERSION

    return data
