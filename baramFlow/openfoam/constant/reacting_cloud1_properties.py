#!/usr/bin/env python
# -*- coding: , # utf-8 -*-

from baramFlow.base.material.material import MaterialType, Phase
from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMEvaporationModel
from baramFlow.coredb.coredb_reader import CoreDBReader
from baramFlow.coredb.material_db import MaterialDB
from baramFlow.coredb.region_db import RegionDB
from baramFlow.openfoam.constant.cloud_properties import CloudProperties


def _getGasName(liquidMid: str, rname: str):
    db = CoreDBReader()

    mid = RegionDB.getMaterial(rname)
    if MaterialDB.getType(mid) != MaterialType.MIXTURE:  # Requirement for SLG Thermo
        return ''

    # Build species table to find a specie corresponding to liquids in the droplet
    species: dict[str, str] = {}  # {<chemicalFormula>: <specieName>}
    for specie, name in MaterialDB.getSpecies(mid).items():
        chemicalFormula = MaterialDB.getChemicalFormula(specie)
        species[chemicalFormula] = name

    chemicalFormula = MaterialDB.getChemicalFormula(liquidMid)

    if chemicalFormula in species:  # It should be in the fluid mixture
        return species[chemicalFormula]  # use the name of corresponding specie in the fluid
    else:
        return ''


class ReactingCloud1Properties(CloudProperties):
    def __init__(self, rname: str):
        super().__init__(rname, 'reactingCloud1Properties')

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
                liquid[_getGasName(material.mid, self._rname)] = composition
                liquidTot += float(material.composition)

        subModels = {
            'compositionModel': 'singleMixtureFraction',
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
