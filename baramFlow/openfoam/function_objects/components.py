#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _foComponentsBase(field: str, rname: str | None) -> dict:
    data = {
        'type':            'components',
        'libs':            ['fieldFunctionObjects'],

        'field':           field,

        'updateHeader': 'false',
        'log': 'false',
    }

    if rname:
        data['region'] = rname

    return data


def foComponentsReport(field: str, rname: str | None) -> dict:
    data = _foComponentsBase(field, rname)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'none',
    })

    return data


def foComponentsMonitor(field: str, rname: str | None, interval: int):
    data = _foComponentsBase(field, rname)
    data.update({
        'executeControl':  'timeStep',
        'executeInterval': interval,

        'writeControl': 'none',
    })

    return data

