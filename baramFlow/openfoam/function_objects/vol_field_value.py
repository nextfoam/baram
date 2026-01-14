#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum


class VolumeReportType(Enum):
    VOLUME_AVERAGE = 'volumeAverage'
    VOLUME_INTEGRAL = 'volumeIntegral'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    COEFFICIENT_OF_VARIATION = 'cov'


VOLUME_MONITOR_OPERATION = {
    VolumeReportType.VOLUME_AVERAGE: 'volAverage',
    VolumeReportType.VOLUME_INTEGRAL: 'volIntegrate',
    VolumeReportType.MINIMUM: 'min',
    VolumeReportType.MAXIMUM: 'max',
    VolumeReportType.COEFFICIENT_OF_VARIATION: 'CoV',
}


class VolumeType(Enum):
    All = 'all'
    CELLZONE = 'cellZone'


def _foVolFieldValueBase(volumeType: VolumeType, volumeName: str, field: str, reportType: VolumeReportType, rname: str) -> dict:
    data = {
        'type': 'volFieldValue',
        'libs': ['fieldFunctionObjects'],

        'fields': [field],
        'operation': VOLUME_MONITOR_OPERATION[reportType],

        'writeFields': 'false',

        'updateHeader': 'false',
        'log': 'false',
    }

    if volumeType == VolumeType.All:
        data['regionType'] = 'all'
    else:
        data['regionType'] = 'cellZone'
        data['name'] = volumeName

    if rname:
        data['region'] = rname

    return data


def foVolFieldValueReport(volumeType: VolumeType, volumeName: str, field: str, reportType: VolumeReportType, rname: str) -> dict:
    data = _foVolFieldValueBase(volumeType, volumeName, field, reportType, rname)
    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foVolFieldValueMonitor(volumeType: VolumeType, volumeName: str, field: str, reportType: VolumeReportType, rname: str, interval: int) -> dict:
    data = _foVolFieldValueBase(volumeType, volumeName, field, reportType, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data
