#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.coredb.general_db import GeneralDB

from libbaram.openfoam.of_utils import openfoamLibraryPath


def _foAgeBase():
    data = {
        'type': 'age',
        'libs': [openfoamLibraryPath('libfieldFunctionObjects')],
        'tolerance': 1e-4,
        'nCorr': 1000,
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


def _additionalEntriesForMonitor(rname: str, interval):
    if GeneralDB.isTimeTransient():
        data =  {
            'executeControl': 'writeTime',
            'executeInterval': interval,
            'writeControl': 'writeTime',
            'writeInterval': interval,
        }
    else:
        data = {
            'executeControl': 'onEnd',
            'writeControl': 'onEnd',
        }

    if rname != '':
        data.update({'region': rname})

    return data


def _additionalEntriesForReport(rname: str):
    if GeneralDB.isTimeTransient():
        data = {
            'executeControl': 'writeTime',
            'executeInterval': 1,
            'writeControl': 'writeTime',
            'writeInterval': 1,
        }
    else:
        data = {
            'executeControl': 'onEnd',
            'writeControl': 'onEnd',
        }

    if rname != '':
        data.update({'region': rname})

    return data


def foAgeMonitor(rname: str, interval):
    data = _foAgeBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foHeatTransferCoefficientMonitor(rname: str, patches, interval):
    data = _foHeatTransferCoefficientBase(patches)
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foMachNumberMonitor(rname: str, interval):
    data = _foMachNumberBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foQMonitor(rname: str, interval):
    data = _foQBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foTotalPressureMonitor(rname: str, interval):
    data = _foTotalPressureBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foVorticityMonitor(rname: str, interval):
    data = _foVorticityBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foWallHeatFluxMonitor(rname: str, interval):
    data = _foWallHeatFluxBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foWallShearStressMonitor(rname: str, interval):
    data = _foWallShearStressBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foWallYPlusMonitor(rname: str, interval):
    data = _foWallYPlusBase()
    data.update(_additionalEntriesForMonitor(rname, interval))

    return data


def foAgeReport(rname: str):
    data = _foAgeBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foHeatTransferCoefficientReport(rname: str, patches):
    data = _foHeatTransferCoefficientBase(patches)
    data.update(_additionalEntriesForReport(rname))

    return data


def foMachNumberReport(rname: str):
    data = _foMachNumberBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foQReport(rname: str):
    data = _foQBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foTotalPressureReport(rname: str):
    data = _foTotalPressureBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foVorticityReport(rname: str):
    data = _foVorticityBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foWallHeatFluxReport(rname: str):
    data = _foWallHeatFluxBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foWallShearStressReport(rname: str):
    data = _foWallShearStressBase()
    data.update(_additionalEntriesForReport(rname))

    return data


def foWallYPlusReport(rname: str):
    data = _foWallYPlusBase()
    data.update(_additionalEntriesForReport(rname))

    return data
