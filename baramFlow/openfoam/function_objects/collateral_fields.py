#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.general_db import GeneralDB

from libbaram.openfoam.of_utils import openfoamLibraryPath


def _foAgeBase():
    data = {
        'type': 'age',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],
    }

    return data


def _foHeatTransferCoefficientBase(patches):
    data = {
        'type': 'heatTransferCoeff',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'htcModel': 'localReferenceTemperature',
        'field': 'T',
        'result': 'heatTransferCoeff',
        'UInf': [0, 0, 0],
        'rho': 'rhoInf',

        'patches': patches
    }

    return data


def _foMachNumberBase():
    data = {
        'type': 'MachNo',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'result': 'machNo'
    }

    return data


def _foQBase():
    data = {
        'type': 'Q',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'result': 'Q'
    }

    return data


def _foTotalPressureBase():
    data = {
        'type': 'pressure',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'mode': 'total',
        'result': 'totalPressure'
    }

    return data


def _foVorticityBase():
    data = {
        'type': 'vorticity',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'result': 'vorticity'
    }

    return data


def _foWallHeatFluxBase():
    data = {
        'type': 'wallHeatFlux',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'writeToFile': 'false'
    }

    return data


def _foWallShearStressBase():
    data = {
        'type': 'wallShearStress',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'writeToFile': 'false'
    }

    return data


def _foWallYPlusBase():
    data = {
        'type': 'yPlus',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],

        'writeToFile': 'false'
    }

    return data


def _additionalEntriesForMonitor(interval):
    if GeneralDB.isTimeTransient():
        return {
            'executeControl': 'timeStep',
            'executeInterval': interval,
            'writeControl': 'timeStep',
            'writeInterval': interval,
        }
    else:
        return {
            'executeControl': 'onEnd',
            'writeControl': 'onEnd',
        }


def _additionalEntriesForReport():
    if GeneralDB.isTimeTransient():
        return {
            'executeControl': 'timeStep',
            'executeInterval': 1,
            'writeControl': 'timeStep',
            'writeInterval': 1,
        }
    else:
        return {
            'executeControl': 'onEnd',
            'writeControl': 'onEnd',
        }


def foAgeMonitor(interval):
    data = _foAgeBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foHeatTransferCoefficientMonitor(patches, interval):
    data = _foHeatTransferCoefficientBase(patches)
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foMachNumberMonitor(interval):
    data = _foMachNumberBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foQMonitor(interval):
    data = _foQBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foTotalPressureMonitor(interval):
    data = _foTotalPressureBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foVorticityMonitor(interval):
    data = _foVorticityBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foWallHeatFluxMonitor(interval):
    data = _foWallHeatFluxBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foWallShearStressMonitor(interval):
    data = _foWallShearStressBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foWallYPlusMonitor(interval):
    data = _foWallYPlusBase()
    data.update(_additionalEntriesForMonitor(interval))

    return data


def foAgeReport():
    data = _foAgeBase()
    data.update(_additionalEntriesForReport())

    return data


def foHeatTransferCoefficientReport(patches):
    data = _foHeatTransferCoefficientBase(patches)
    data.update(_additionalEntriesForReport())

    return data


def foMachNumberReport():
    data = _foMachNumberBase()
    data.update(_additionalEntriesForReport())

    return data


def foQReport():
    data = _foQBase()
    data.update(_additionalEntriesForReport())

    return data


def foTotalPressureReport():
    data = _foTotalPressureBase()
    data.update(_additionalEntriesForReport())

    return data


def foVorticityReport():
    data = _foVorticityBase()
    data.update(_additionalEntriesForReport())

    return data


def foWallHeatFluxReport():
    data = _foWallHeatFluxBase()
    data.update(_additionalEntriesForReport())

    return data


def foWallShearStressReport():
    data = _foWallShearStressBase()
    data.update(_additionalEntriesForReport())

    return data


def foWallYPlusReport():
    data = _foWallYPlusBase()
    data.update(_additionalEntriesForReport())

    return data
