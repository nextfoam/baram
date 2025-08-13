#!/usr/bin/env python
# -*- coding: utf-8 -*-


def _foForceCoeffsBase(boundaries: [str],
                      aRef: float,
                      lRef: float,
                      magUInf: float,
                      rhoInf: float,
                      dragDir: [float, float, float],
                      liftDir: [float, float, float],
                      cofr: [float, float, float],
                      pRef: float,
                      rname: str):
    data = {
        'type': 'forceCoeffs',
        'libs': ['forces'],

        'patches': boundaries,
        'coefficients': ['Cd', 'Cl', 'CmPitch'],
        'rho': 'rho',
        'Aref': aRef,
        'lRef': lRef,
        'magUInf': magUInf,
        'rhoInf': rhoInf,
        'dragDir': dragDir,
        'liftDir': liftDir,
        'CofR': cofr,

        'updateHeader': 'false',
        'log': 'false',
    }

    if pRef is not None:
        data['pRef'] = pRef

    if rname:
        data['region'] = rname

    return data


def foForceCoeffsReport(boundaries: [str],
                        aRef: float,
                        lRef: float,
                        magUInf: float,
                        rhoInf: float,
                        dragDir: [float, float, float],
                        liftDir: [float, float, float],
                        cofr: [float, float, float],
                        pRef: float,
                        rname: str):
    data = _foForceCoeffsBase(boundaries, aRef, lRef, magUInf, rhoInf, dragDir, liftDir, cofr, pRef, rname)

    data.update({
        'executeControl': 'onEnd',

        'writeControl': 'onEnd',
    })

    return data


def foForceCoeffsMonitor(boundaries: [str],
                         aRef: float,
                         lRef: float,
                         magUInf: float,
                         rhoInf: float,
                         dragDir: [float, float, float],
                         liftDir: [float, float, float],
                         cofr: [float, float, float],
                         pRef: float,
                         rname: str,
                         interval: int):
    data = _foForceCoeffsBase(boundaries, aRef, lRef, magUInf, rhoInf, dragDir, liftDir, cofr, pRef, rname)
    data.update({
        'executeControl': 'timeStep',
        'executeInterval': interval,

        'writeControl': 'timeStep',
        'writeInterval': interval,
    })

    return data

