#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb.cell_zone_db import SpecificationMethod
from baramFlow.coredb.turbulence_model_db import TurbulenceModel, TurbulenceFields, TurbulenceModelsDB


_modelFields = {
    TurbulenceModel.INVISCID: [],
    TurbulenceModel.LAMINAR: [],
    TurbulenceModel.SPALART_ALLMARAS: [TurbulenceFields.NU_TILDA],
    TurbulenceModel.K_EPSILON: [TurbulenceFields.K, TurbulenceFields.EPSILON],
    TurbulenceModel.K_OMEGA: [TurbulenceFields.K, TurbulenceFields.OMEGA],
    TurbulenceModel.LES: [],
}


class TurbulenceField:
    def __init__(self, field, symbol, unit, sourceUnits, xpathName):
        self._field = field
        self._symbol = symbol
        self._unit = unit
        self._sourceUnits = sourceUnits
        self._xpathName = xpathName

    @property
    def xpathName(self):
        return self._xpathName

    @property
    def symbol(self):
        return self._symbol

    @property
    def unit(self):
        return self._unit

    @property
    def sourceUnits(self):
        return self._sourceUnits

    def name(self):
        return {
            TurbulenceFields.K:         QCoreApplication.translate('TurbulenceModel', 'Turbulent Kinetic Energy'),
            TurbulenceFields.EPSILON:   QCoreApplication.translate('TurbulenceModel', 'Turbulent Dissipation Rate'),
            TurbulenceFields.OMEGA:     QCoreApplication.translate('TurbulenceModel', 'Specific Dissipation Rate'),
            TurbulenceFields.NU_TILDA:  QCoreApplication.translate('TurbulenceModel', 'Modified Turbulent Viscosity'),
        }.get(self._field)

    def getLabelText(self):
        return f'{self._symbol} ({self._unit})'


_fields = {
    TurbulenceFields.K:
        TurbulenceField(TurbulenceFields.K,
                        'k',
                        'm<sup>2</sup>/s<sup>2</sup>',
                        {
                            SpecificationMethod.VALUE_PER_UNIT_VOLUME: '1/ms<sup>3</sup>',
                            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: 'm<sup>2</sup>/s<sup>3</sup>'
                        },
                        'turbulentKineticEnergy'),
    TurbulenceFields.EPSILON:
        TurbulenceField(TurbulenceFields.EPSILON,
                        'ε',
                        'm<sup>2</sup>/s<sup>3</sup>',
                        {
                            SpecificationMethod.VALUE_PER_UNIT_VOLUME: '1/m<sup>2</sup>s<sup>4</sup>',
                            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: 'm<sup>2</sup>/s<sup>4</sup>'
                        }, 'turbulentDissipationRate'),
    TurbulenceFields.OMEGA:
        TurbulenceField(TurbulenceFields.OMEGA,
                        'ω',
                        '1/s',
                        {
                            SpecificationMethod.VALUE_PER_UNIT_VOLUME: '1/m<sup>3</sup>s<sup>2</sup>',
                            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: '1/s<sup>2</sup>'
                        },
                        'specificDissipationRate'),
    TurbulenceFields.NU_TILDA:
        TurbulenceField(TurbulenceFields.NU_TILDA,
                        'ν',
                        'm<sup>2</sup>/s',
                        {
                            SpecificationMethod.VALUE_PER_UNIT_VOLUME: '1/ms<sup>2</sup>',
                            SpecificationMethod.VALUE_FOR_ENTIRE_CELL_ZONE: 'm<sup>2</sup>/s<sup>2</sup>'
                        },
                        'modifiedTurbulentViscosity'),
}


def getTurbulenceFields():
    return [_fields[f] for f in _modelFields[TurbulenceModelsDB.getModel()]]
