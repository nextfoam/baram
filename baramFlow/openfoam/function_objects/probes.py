#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.of_utils import openfoamLibraryPath


def _foProbesBase(field: str, probeLocation: [float, float, float], rname: str) -> dict:
    data = {
        'type': 'probes',
        'libs': [openfoamLibraryPath('libsampling')],

        'fields': [field],
        'probeLocations': [probeLocation],

        'updateHeader': 'false',
        'log': 'false',
    }

    if rname:
        data['region'] = rname

    return data


def foProbesReport(field: str, probeLocation: [float, float, float], rname: str) -> dict:
    data = _foProbesBase(field, probeLocation, rname)
    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foProbesMonitor(field: str, probeLocation: [float, float, float], rname: str, interval: int) -> dict:
    data = _foProbesBase(field, probeLocation, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data

