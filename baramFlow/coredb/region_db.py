#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QObject

import baramFlow.coredb.libdb as xml
from baramFlow.base.material.material import MaterialType
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import MaterialDB, IMaterialObserver
from baramFlow.coredb.specie_model_db import ISpecieModelObserver

REGION_XPATH = '/regions/region'
DEFAULT_REGION_NAME = 'region0'
CELL_ZONE_NAME_FOR_REGION = 'All'


class CavitationModel(Enum):
    NONE= 'none'
    SCHNERR_SAUER = 'schnerrSauer'
    KUNZ = 'kunz'
    MERKLE = 'merkle'
    ZWART_GERBER_BELAMRI = 'zwartGerberBelamri'


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
        return MaterialDB.getPhase(cls.getMaterial(rname))

    @classmethod
    def getMaterial(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/material')

    @classmethod
    def getSecondaryMaterials(cls, rname):
        return coredb.CoreDB().getValue(cls.getXPath(rname) + '/secondaryMaterials').split()

    @classmethod
    def isMultiRegion(cls):
        return len(coredb.CoreDB().getRegions()) > 1

    @classmethod
    def addRegion(cls, rname: str):
        db = coredb.CoreDB()
        if db.exists(cls.getXPath(rname)):
            raise FileExistsError

        regions = db.getElement('/regions')
        regions.append(xml.createElement('<region xmlns="http://www.baramcfd.org/baram">'
                                         f' <name>{rname}</name>'
                                         f' <material>{MaterialDB.getMaterials()[0][0]}</material>'
                                         '  <secondaryMaterials/>'
                                         '  <phaseInteractions>'
                                         '      <surfaceTensions/>'
                                         '      <massTransfers>'
                                         '          <massTransfer>'
                                         '              <from>0</from>'
                                         '              <to>0</to>'
                                         '              <mechanism>cavitation</mechanism>'
                                         '              <cavitation>'
                                         '                  <model>none</model>'
                                         '                  <vaporizationPressure>2300</vaporizationPressure>'
                                         '                  <schnerrSauer>'
                                         '                      <evaporationCoefficient>1</evaporationCoefficient>'
                                         '                      <condensationCoefficient>1</condensationCoefficient>'
                                         '                      <bubbleDiameter>2.0e-06</bubbleDiameter>'
                                         '                      <bubbleNumberDensity>1.6e+13</bubbleNumberDensity>'
                                         '                  </schnerrSauer>'
                                         '                  <kunz>'
                                         '                      <evaporationCoefficient>1000</evaporationCoefficient>'
                                         '                      <condensationCoefficient>1000</condensationCoefficient>'
                                         '                      <meanFlowTimeScale>0.005</meanFlowTimeScale>'
                                         '                      <freeStreamVelocity>20.0</freeStreamVelocity>'
                                         '                  </kunz>'
                                         '                  <merkle>'
                                         '                      <evaporationCoefficient>1e-3</evaporationCoefficient>'
                                         '                      <condensationCoefficient>80</condensationCoefficient>'
                                         '                      <meanFlowTimeScale>0.005</meanFlowTimeScale>'
                                         '                      <freeStreamVelocity>20.0</freeStreamVelocity>'
                                         '                  </merkle>'
                                         '                  <zwartGerberBelamri>'
                                         '                      <evaporationCoefficient>1</evaporationCoefficient>'
                                         '                      <condensationCoefficient>1</condensationCoefficient>'
                                         '                      <bubbleDiameter>2e-6</bubbleDiameter>'
                                         '                      <nucleationSiteVolumeFraction>1e-3</nucleationSiteVolumeFraction>'
                                         '                  </zwartGerberBelamri>'
                                         '              </cavitation>'
                                         '          </massTransfer>'
                                         '      </massTransfers>'
                                         '  </phaseInteractions>'
                                         '  <cellZones/>'
                                         '  <boundaryConditions/>'
                                         '  <initialization>'
                                         '      <initialValues>'
                                         '          <velocity><x>0</x><y>0</y><z>0</z></velocity>'
                                         '          <pressure>0</pressure>'
                                         '          <temperature>300</temperature>'
                                         '          <scaleOfVelocity>1</scaleOfVelocity>'
                                         '          <turbulentIntensity>1</turbulentIntensity>'
                                         '          <turbulentViscosity>10</turbulentViscosity>'
                                         '          <volumeFractions/>'
                                         '          <userDefinedScalars/>'
                                         '          <species/>'
                                         '      </initialValues>'
                                         '      <advanced><sections/></advanced>'
                                         '  </initialization>'
                                         '</region>'))

        db.addCellZone(rname, CELL_ZONE_NAME_FOR_REGION)

    @classmethod
    def getMixturesInRegions(cls):
        mixtures = {mid: name for mid, name, _, _ in MaterialDB.getMaterials('mixture')}
        materialsInRegions = (set(xml.getText(region, 'material')
                                  for region in coredb.CoreDB().getElements(f'{REGION_XPATH}')))

        return [(mid, name) for mid, name in mixtures.items() if mid in materialsInRegions]

    @classmethod
    def updateMaterials(cls, rname, primary: str, secondaries: list[str]):
        def addSurfaceTension(parent, mid1, mid2):
            if xml.getElement(parent, f'surfaceTension[mid="{mid1}"][mid="{mid2}"]') is None:
                parent.append(xml.createElement(f'<surfaceTension xmlns="http://www.baramcfd.org/baram">'
                                                f'  <mid>{mid1}</mid><mid>{mid2}</mid><value>0</value>'
                                                f'</surfaceTension>'))

        db = coredb.CoreDB()

        currentPrimary = RegionDB.getMaterial(rname)
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
        db.setValue(xpath + '/material', primary)
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
    def materialRemoving(self, db, mid: str):
        for region in db.getElements(REGION_XPATH):
            if xml.getText(region, 'material') == mid or f' {mid} ' in f" {xml.getText(region, 'secondaryMaterials')} ":
                raise ConfigurationException(self.tr('{} is set as material of region {}').format(
                    MaterialDB.getName(mid), xml.getText(region, 'name')))
        #
        # surfaceTensions = db.getElement(f'{REGION_XPATH}/phaseInteractions/surfaceTensions')
        # for element in xml.getElement(surfaceTensions, f'surfaceTension[mid="{mid}"]'):
        #     surfaceTensions.remove(element)


class SpecieModelObserver(ISpecieModelObserver):
    def turningOff(self, db, mixtures):
        for region in db.getElements(REGION_XPATH):
            if (mid := xml.getText(region, 'material')) in mixtures:
                raise ConfigurationException(
                    self.tr('Cannot turn off specie model, Mixture {} is material of region {}.').format(
                        MaterialDB.getName(mid), xml.getText(region, 'name')))
