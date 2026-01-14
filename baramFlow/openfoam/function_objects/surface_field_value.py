#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum


class SurfaceReportType(Enum):
    AREA_WEIGHTED_AVERAGE = 'areaWeightedAverage'
    MASS_WEIGHTED_AVERAGE = 'massWeightedAverage'
    INTEGRAL = 'Integral'
    MASS_FLOW_RATE = 'massFlowRate'
    VOLUME_FLOW_RATE = 'volumeFlowRate'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    COEFFICIENT_OF_VARIATION = 'cov'


SURFACE_MONITOR_OPERATION = {
    SurfaceReportType.AREA_WEIGHTED_AVERAGE: 'areaAverage',
    SurfaceReportType.MASS_WEIGHTED_AVERAGE: 'weightedAverage',
    SurfaceReportType.INTEGRAL: 'areaIntegrate',
    SurfaceReportType.MASS_FLOW_RATE: 'sum',
    SurfaceReportType.VOLUME_FLOW_RATE: 'areaNormalIntegrate',
    SurfaceReportType.MINIMUM: 'min',
    SurfaceReportType.MAXIMUM: 'max',
    SurfaceReportType.COEFFICIENT_OF_VARIATION: 'CoV',
}


def _foSurfaceFieldValueBase(surface: str, field: str, reportType: SurfaceReportType, rname: str) -> dict:
    data = {
        'type': 'surfaceFieldValue',
        'libs': ['fieldFunctionObjects'],

        'regionType': 'patch',
        'name': surface,
        'surfaceFormat': 'none',
        'fields': [field],
        'operation': SURFACE_MONITOR_OPERATION[reportType],

        'writeFields': 'false',

        'updateHeader': 'false',
        'log': 'false',
    }

    if reportType == SurfaceReportType.MASS_WEIGHTED_AVERAGE:
        data['weightField'] = 'phi'

    if rname:
        data['region'] = rname

    return data


def foSurfaceFieldValueReport(surface: str, field: str, reportType: SurfaceReportType, rname: str) -> dict:
    data = _foSurfaceFieldValueBase(surface, field, reportType, rname)
    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foSurfaceFieldValueMonitor(surface: str, field: str, reportType: SurfaceReportType, rname: str, interval: int) -> dict:
    data = _foSurfaceFieldValueBase(surface, field, reportType, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data

