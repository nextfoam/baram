#!/usr/bin/env python
# -*- coding: , # utf-8 -*-

from baramFlow.base.material.material import Phase
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMEvaporationModel
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.openfoam.constant.cloud_properties import CloudProperties


class ReactingCloud1Properties(CloudProperties):
    def __init__(self):
        super().__init__('reactingCloud1Properties')

    def build(self):
        if self._data is not None:
            return self

        properties = DPMModelManager.properties()

        self._buildBaseCloudProperties(properties)

        solid = {}
        liquid = {}
        solidTot = 0
        liquidTot = 0
        for material in properties.droplet.composition:
            phase = MaterialDB.getPhase(material.mid)
            composition = float(material.composition)
            if phase == Phase.SOLID:
                solid[MaterialDB.getName(material.mid)] = composition
                solidTot += float(material.composition)
            elif phase == Phase.LIQUID:
                liquid[MaterialDB.getName(material.mid)] = composition
                liquidTot += float(material.composition)

        subModels = {
            'heatTransferModel': properties.heatTransfer.specification.value,
            'compositionModel': 'singleMixtureFraction',
            'radiation': 'off',
            'RanzMarshallCoeffs': {
                'BirdCorrection': self._helper.boolValue(properties.heatTransfer.ranzMarsahll.birdCorrection),
            },
            'singleMixtureFractionCoeffs': {
                'phases': [
                    'gas', {},
                    'liquid', {material: round(composition / liquidTot, 6) for material, composition in liquid.items()},
                    'solid', {material: round(composition / solidTot, 6) for material, composition in solid.items()}
                ],
                'YGasTot0': 0,
                'YLiquidTot0': liquidTot,
                'YSolidTot0': solidTot
            },
            'liquidEvaporationCoeffs': {
                'enthalpyTransfer': properties.evaporation.enthalpyTransferType.value,
                'activeLiquids': list(liquid.keys())
            }
        }

        if properties.evaporation.model == DPMEvaporationModel.DIFFUSION_CONTROLLED:
            subModels['phaseChangeModel'] = 'liquidEvaporation'
        elif properties.evaporation.model == DPMEvaporationModel.CONVECTION_DIFFUSION_CONTROLLED:
            subModels['phaseChangeModel'] = 'liquidEvaporationBoil'

        self._data['subModels'].update(subModels)

        return self
