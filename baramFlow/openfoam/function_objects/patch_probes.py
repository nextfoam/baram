#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _foPatchProbesBase(boundary: str, field: str, probeLocation: [float, float, float], rname: str) -> dict:
    data = {
        'type': 'patchProbes',
        'libs': ['sampling'],

        'patches': [boundary],
        'fields': [field],
        'probeLocations': [probeLocation],

        'updateHeader': 'false',
        'log': 'false',
    }

    if rname:
        data['region'] = rname

    return data


def foPatchProbesReport(boundary: str, field: str, probeLocation: [float, float, float], rname: str) -> dict:
    data = _foPatchProbesBase(boundary, field, probeLocation, rname)
    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foPatchProbesMonitor(boundary: str, field: str, probeLocation: [float, float, float], rname: str, interval: int) -> dict:
    data = _foPatchProbesBase(boundary, field, probeLocation, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data

