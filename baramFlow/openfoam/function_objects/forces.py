#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.of_utils import openfoamLibraryPath


def _foForcesBase(boundaries: [str], cofr: [float, float, float], rname: str) -> dict:
    data = {
        'type': 'forces',
        'libs': [openfoamLibraryPath('libforces')],

        'patches': boundaries,
        'CofR': cofr,

        'updateHeader': 'false',
        'log': 'false',
    }

    if rname:
        data['region'] = rname

    return data


def foForcesReport(boundaries: [str], cofr: [float, float, float], rname: str) -> dict:
    data = _foForcesBase(boundaries, cofr, rname)
    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foForcesMonitor(boundaries: [str], cofr: [float, float, float], rname: str, interval: int) -> dict:
    data = _foForcesBase(boundaries, cofr, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data

