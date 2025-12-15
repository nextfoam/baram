#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.model.DPM_model import DPMModelManager
from baramFlow.base.model.model import DPMParticleType
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import MaterialDB, IMaterialObserver
from baramFlow.coredb.region_db import IRegionMaterialObserver, RegionDB


class  MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: str):
        if DPMModelManager.inertParticle() == mid:
            if DPMModelManager.particleType() == DPMParticleType.INERT:
                raise ConfigurationException(
                    self.tr('Material {} is the inert particle of DPM Model, '
                            'so it cannot be changed to a different material.').format(MaterialDB.getName(mid)))

            DPMModelManager.removeInertParticle(db)

    def specieRemoving(self, db, mid: str, primarySpecie: str):
        if mid in DPMModelManager.dropletCompositionMaterials():
            if DPMModelManager.particleType() == DPMParticleType.DROPLET:
                raise ConfigurationException(
                    self.tr('Material {} is included in the droplet composition of DPM Model, '
                            'so it cannot be changed to a different material.').format(MaterialDB.getName(mid)))

            DPMModelManager.clearDropletComposition(db)


class RegionMaterialObserver(IRegionMaterialObserver):
    def materialsUpdating(self, db, rname, primary, secondaries, species):
        oldMaterial = RegionDB.getMaterial(rname)

        if DPMModelManager.particleType() == DPMParticleType.DROPLET:
            raise ConfigurationException(
                self.tr('Material {} is included in the droplet composition of DPM Model, '
                        'so it cannot be changed to a different material.').format(MaterialDB.getName(oldMaterial)))

        DPMModelManager.clearDropletComposition(db)
