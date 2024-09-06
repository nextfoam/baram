#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.of_utils import openfoamLibraryPath


def _foComponentsBase(field: str):
    data = {
        'type':            'components',
        'libs':            [openfoamLibraryPath('libfieldFunctionObjects')],

        'field':           field,

        'updateHeader': 'false',
        'log': 'false',
    }

    return data


def foComponentsReport(field: str):
    data = _foComponentsBase(field)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'none',
    })

    return data


def foComponentsMonitor(field: str, interval: int):
    data = _foComponentsBase(field)
    data.update({
        'executeControl':  'timeStep',
        'executeInterval': interval,

        'writeControl': 'none',
    })

    return data

