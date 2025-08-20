#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _foReadFieldsBase(fields: list[str], rname: str):
    data = {
        'type':            'readFields',
        'libs':            ['fieldFunctionObjects'],

        'fields':           fields,

        'updateHeader': 'false',
        'log': 'false',
    }

    if rname:
        data['region'] = rname

    return data


def foReadFieldsReport(fields: list[str], rname: str):
    data = _foReadFieldsBase(fields, rname)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'none',
    })

    return data


def foReadFieldsMonitor(fields: list[str], rname: str, interval: int):
    data = _foReadFieldsBase(fields, rname)
    data.update({
        'executeControl':  'timeStep',
        'executeInterval': interval,

        'writeControl': 'none',
    })

    return data

