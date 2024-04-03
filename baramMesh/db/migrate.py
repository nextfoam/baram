#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .configurations_schema import CURRENT_CONFIGURATIONS_VERSION, CONFIGURATIONS_VERSION_KEY
from .configurations_schema import FeatureSnapType


def _to_v1(data):
    if 'featureSnapType' not in data['snap']:
        data['snap']['featureSnapType'] = FeatureSnapType.EXPLICIT

    for surfaceRefinement in data['castellation']['refinementSurfaces'].values():
        if 'surfaceRefinement' not in surfaceRefinement:
            orgSurfaceRefinementLevel = surfaceRefinement.pop('surfaceRefinementLevel')
            surfaceRefinement['surfaceRefinement'] = {
                'minimumLevel': orgSurfaceRefinementLevel,
                'maximumLevel': str(int(orgSurfaceRefinementLevel) + 1)
            }


_migrates = {
    0: _to_v1,
}


def migrate(data):
    version = int(data.get(CONFIGURATIONS_VERSION_KEY, 0))
    assert version <= CURRENT_CONFIGURATIONS_VERSION

    for v in range(version, len(_migrates)):
        _migrates[v](data)

    data[CONFIGURATIONS_VERSION_KEY] = CURRENT_CONFIGURATIONS_VERSION

    return data
