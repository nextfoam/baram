#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _foMagBase(field: str, rname: str | None) -> dict:
    data = {
        'type':            'mag',
        'libs':            ['fieldFunctionObjects'],

        'field':           field,

        'updateHeader': 'false',
        'log': 'false',
    }

    if rname:
        data['region'] = rname

    return data


def foMagReport(field: str, rname: str | None) -> dict:
    data = _foMagBase(field, rname)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'none',
    })

    return data


def foMagMonitor(field: str, rname: str | None, interval: int) -> dict:
    data = _foMagBase(field, rname)
    data.update({
        'executeControl':  'timeStep',
        'executeInterval': interval,

        'writeControl': 'none',
    })

    return data

