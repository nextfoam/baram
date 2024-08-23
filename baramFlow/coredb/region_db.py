#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import MaterialDB, MaterialType, IMaterialObserver
from baramFlow.coredb.specie_model_db import ISpecieModelObserver

REGION_XPATH = '/regions/region'
DEFAULT_REGION_NAME = 'region0'


class IRegionMaterialObserver(QObject):
    def materialsUpdating(self, db, rname, primary, secondaries, species):
        pass

    def _specieRatiosXML(self, species):
        text = ''
        for mid, isPrimary in species.items():
            text += f'<specie><mid>{mid}</mid><value>{1 if isPrimary else 0}</value></specie>'

        return text


class RegionDB:
    _materialObservers = []

    @classmethod
    def registerMaterialObserver(cls, observer):
        cls._materialObservers.append(observer)

    @classmethod
    def getXPath(cls, rname):
        return f'{REGION_XPATH}[name="{rname}"]'

    @classmethod
    def getPhase(cls, rname):
        return MaterialDB.getPhase(coredb.CoreDB().getValue(cls.getXPath(rname) + '/material'))

    @classmethod
    def getMaterial(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/material')

    @classmethod
    def getSecondaryMaterials(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/secondaryMaterials').split()

    @classmethod
    def getNumberOfRegions(cls):
        return len(coredb.CoreDB().getRegions())

    @classmethod
    def getMixturesInRegions(cls):
        db = coredb.CoreDB()
        mixtures = {str(mid): name for mid, name, _, _ in db.getMaterials('mixture')}
        materialsInRegions = set(xml.getText(region, 'material') for region in db.getElements(f'{REGION_XPATH}'))

        return [(mid, name) for mid, name in mixtures.items() if mid in materialsInRegions]

    @classmethod
    def updateMaterials(cls, rname, primary, secondaries):
        def addSurfaceTension(parent, mid1, mid2):
            if xml.getElement(parent, f'surfaceTension[mid="{mid1}"][mid="{mid2}"]') is None:
                parent.append(xml.createElement(f'<surfaceTension xmlns="http://www.baramcfd.org/baram">'
                                                f'  <mid>{mid1}</mid><mid>{mid2}</mid><value>0</value>'
                                                f'</surfaceTension>'))

        db = coredb.CoreDB()

        currentPrimary = int(RegionDB.getMaterial(rname))
        currentSecondaries = RegionDB.getSecondaryMaterials(rname)

        if primary == currentPrimary and set(secondaries) == set(currentSecondaries):
            return

        if currentPrimary != primary and MaterialDB.getType(primary) == MaterialType.MIXTURE:
            primarySpecie = MaterialDB.getPrimarySpecie(primary)
            species = {mid: mid == primarySpecie for mid, _ in MaterialDB.getSpecies(primary).items()}
        else:
            species = {}

        for observer in cls._materialObservers:
            observer.materialsUpdating(db, rname, primary, secondaries, species)

        xpath = cls.getXPath(rname)
        db.setValue(xpath + '/material', str(primary))
        db.setValue(xpath + '/secondaryMaterials', ' '.join(secondaries))

        region = getRegionElement(rname)
        surfaceTensions = xml.getElement(region, 'phaseInteractions/surfaceTensions')
        surfaceTensions.clear()
        #
        # for i in range(len(secondaries)):
        #     addSurfaceTension(surfaceTensions, primary, secondaries[i])
        #     for j in range(len(secondaries)):
        #         addSurfaceTension(surfaceTensions, secondaries[i], secondaries[j])


def getRegionElement(rname):
    return coredb.CoreDB().getElement(RegionDB.getXPath(rname))


class MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: int):
        for region in db.getElements(REGION_XPATH):
            if int(xml.getText(region, 'material')) == mid or f' {mid} ' in f" {xml.getText(region, 'secondaryMaterials')} ":
                raise ConfigurationException(self.tr('{} is set as material of region {}').format(
                    MaterialDB.getName(mid), xml.getText(region, 'name')))
        #
        # surfaceTensions = db.getElement(f'{REGION_XPATH}/phaseInteractions/surfaceTensions')
        # for element in xml.getElement(surfaceTensions, f'surfaceTension[mid="{mid}"]'):
        #     surfaceTensions.remove(element)


class SpecieModelObserver(ISpecieModelObserver):
    def turningOff(self, db, mixtures):
        for region in db.getElements(REGION_XPATH):
            if (mid := int(xml.getText(region, 'material'))) in mixtures:
                raise ConfigurationException(
                    self.tr('Cannot turn off specie model, Mixture {} is material of region {}.').format(
                        MaterialDB.getName(mid), xml.getText(region, 'name')))
