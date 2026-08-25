#!/usr/bin/env python
# -*- coding: utf-8 -*-

def _foComplementAlphaPhiBase(field: str, subtrahendField : str):
    return {
        'type': 'subtract',
        'libs': ['fieldFunctionObjects'],
        'fields': ['phi', 'alphaPhi0.' + subtrahendField],
        'result': field,
    }


def foComplementAlphaPhiMonitor(field: str, subtrahendField: str, interval: int):
    data = _foComplementAlphaPhiBase(field, subtrahendField)

    data.update({
        'executeControl':  'timeStep',
        'executeInterval': interval,

        'writeControl': 'none',
    })

    return data


def foComplementAlphaPhiReport(field: str, subtrahendField: str):
    data = _foComplementAlphaPhiBase(field, subtrahendField)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'none',
    })

    return data
