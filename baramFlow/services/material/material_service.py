#!/usr/bin/env python
# -*- coding: utf-8 -*-

from baramFlow.base.material.constants import MATERIAL_XPATH, MaterialType, Phase, MATERIALS_XPATH
from baramFlow.base.material.constants import NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS, TransportSpecification
from baramFlow.base.material.database import materialsBase
from baramFlow.base.material.material import MaterialBase, Material, createMixture, createSpecie, createNonMixture
from baramFlow.base.material.material import MixtureProperties
from baramFlow.coredb.coredb import CoreDB
from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.material_db import MaterialDB


class Materials:
    def __init__(self):
        self._materials: dict[str, MaterialBase] = {}

    def load(self):
        self._materials.clear()

        for e in CoreDB().getElements(MATERIAL_XPATH):
            mid = e.get('mid')
            self._materials[mid] = MaterialBase(mid=mid,
                                                name=e.find('name', namespaces=nsmap).text,
                                                type=MaterialType(e.find('type', namespaces=nsmap).text),
                                                phase=Phase(e.find('phase', namespaces=nsmap).text))

    def getMaterials(self, types=None, phases=None):
        return [m for m in self._materials.values()
                if (types is None or m.type in types) and (phases is None or m.phase in phases)]

    def getMaterial(self, mid):
        return self._materials[mid]


class MaterialService:
    @staticmethod
    def loadMaterials() -> Materials:
        materials = Materials()
        materials.load()

        return materials

    @staticmethod
    def getMaterial(mid: str):
        return Material.fromElement(CoreDB().getElement(MaterialDB.getXPath(mid)))

    @staticmethod
    def getSpeciesIDSInMixture(mid: str) -> dict[str, str]:
        return {e.getparent().get('mid'): e.getparent().find('name', namespaces=nsmap).text
                for e in CoreDB().getElements(f'{MATERIAL_XPATH}/specie[mixture="{mid}"]')}

    @classmethod
    def updateMaterial(cls, data: Material):
        def copyTransportProperties(mid: str, properties: tuple):
            tag, new = properties
            material = db.getElement(MaterialDB.getXPath(mid) + '/transport')
            old = material.find(tag, namespaces=nsmap)
            material.replace(old, new.toElement())

        with CoreDB() as db:
            db.replaceElement(MaterialDB.getXPath(data.mid), data.toElement())

            # All the species in a mixture should have same configuration for Non-Newtonian fluid
            # because it's configured in "turbulenceProperties" dict file in "OpenFOAM"
            if (data.type == MaterialType.SPECIE
                    and data.transport.specification in NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS):
                if data.transport.specification == TransportSpecification.CROSS_POWER_LAW:
                    properties = ('cross', data.transport.crossPowerLaw)
                elif data.transport.specification == TransportSpecification.HERSCHEL_BULKLEY:
                    properties = ('herschelBulkley', data.transport.herschelBulkley)
                elif data.transport.specification == TransportSpecification.BIRD_CARREAU:
                    properties = ('carreau', data.transport.birdCarreau)
                elif data.transport.specification == TransportSpecification.POWER_LAW:
                    properties = ('nonNewtonianPowerLaw', data.transport.nonNewtonianPowerLaw)

                mixtureID = data.specieProperties.mixtureID
                copyTransportProperties(mixtureID, properties)
                for mid in cls.getSpeciesIDSInMixture(mixtureID):
                    copyTransportProperties(mid, properties)

            db.increaseConfigCount()

    @classmethod
    def addMixture(cls, specieBases: list) -> str:
        with CoreDB() as db:
            parent = db.getElement(MATERIALS_XPATH)

            mixture = createMixture(
                cls._newID(), cls._newName('mixture'), Phase(materialsBase.getMaterial(specieBases[0])['phase']))
            element = mixture.toElement()
            # from lxml import etree
            # print(str(etree.tostring(mixture.transport.toElement(), xml_declaration=True, encoding='UTF-8'), 'UTF-8'))
            parent.append(element)

            for index, baseName in enumerate(specieBases):
                specie = createSpecie(cls._newID(), cls._newName(baseName), materialsBase.getMaterial(baseName), mixture)
                parent.append(specie.toElement())

                if index == 0:
                    element.append(MixtureProperties(primarySpecieID=specie.mid).toElement())

            db.increaseConfigCount()

        return mixture.mid

    @classmethod
    def addSpecies(cls, baseNames: list[str], mixtureID: str) -> list[str]:
        mids = []

        mixture = cls.getMaterial(mixtureID)
        with CoreDB() as db:
            parent = db.getElement(MATERIALS_XPATH)
            for baseName in baseNames:
                specie = createSpecie(cls._newID(), cls._newName(baseName), materialsBase.getMaterial(baseName), mixture)
                parent.append(specie.toElement())
                mids.append(specie.mid)

                for observer in MaterialDB._observers:
                    observer.specieAdded(db, specie.mid, mixtureID)

            db.increaseConfigCount()

        return mids

    @classmethod
    def addNonMixtures(cls, baseNames: list[str] ) -> list[str]:
        mids = []

        with CoreDB() as db:
            parent = db.getElement(MATERIALS_XPATH)
            for baseName in baseNames:
                material = createNonMixture(cls._newID(), cls._newName(baseName), materialsBase.getMaterial(baseName))
                parent.append(material.toElement())
                mids.append(material.mid)

            db.increaseConfigCount()

        return mids

    @classmethod
    def _newID(cls):
        return CoreDB().availableID(MATERIAL_XPATH, 'mid')

    @classmethod
    def _newName(cls, name):
        return CoreDB().toUniqueText(MATERIAL_XPATH, 'name', name)
