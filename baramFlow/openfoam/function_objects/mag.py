#!/usr/bin/env python
# -*- coding: utf-8 -*-

from libbaram.openfoam.of_utils import openfoamLibraryPath


def _foMagBase(field: str):
    data = {
        'type':            'mag',
        'libs':            [openfoamLibraryPath('libfieldFunctionObjects')],

        'field':           field,

        'updateHeader': 'false',
        'log': 'false',
    }

    return data


def foMagReport(field: str):
    data = _foMagBase(field)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'none',
    })

    return data


def foMagMonitor(field: str, interval: int):
    data = _foMagBase(field)
    data.update({
        'executeControl':  'timeStep',
        'executeInterval': interval,

        'writeControl': 'none',
    })

    return data

