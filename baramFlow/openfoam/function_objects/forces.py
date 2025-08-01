#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _foForcesBase(boundaries: list[str],
                  cofr: list[float],
                  pRef: float | None,
                  rname: str | None) -> dict:
    data = {
        'type': 'forces',
        'libs': ['forces'],

        'patches': boundaries,
        'CofR': cofr,

        'updateHeader': 'false',
        'log': 'false',
    }

    if pRef is not None:
        data['pRef'] = pRef

    if rname:
        data['region'] = rname

    return data


def foForcesReport(boundaries: list[str],
                   cofr: list[float],
                   pRef: float | None,
                   rname: str | None) -> dict:
    data = _foForcesBase(boundaries, cofr, pRef, rname)
    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foForcesMonitor(boundaries: list[str],
                    cofr: list[float],
                    pRef: float | None,
                    rname: str | None,
                    interval: int) -> dict:
    data = _foForcesBase(boundaries, cofr, pRef, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data

