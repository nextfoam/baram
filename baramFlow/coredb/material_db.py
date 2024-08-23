#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, Flag

from PySide6.QtCore import QCoreApplication, QObject

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.meterial_templates import MaterialTemplates

UNIVERSAL_GAS_CONSTANT = 8314.46261815324

MATERIAL_XPATH = '/materials/material'


_materialTemplates = MaterialTemplates()


class Phase(Flag):
    GAS = 'gas'
    LIQUID = 'liquid'
    SOLID = 'solid'


class Specification(Enum):
    CONSTANT = 'constant'
    PERFECT_GAS = 'perfectGas'
    SUTHERLAND = 'sutherland'
    POLYNOMIAL = 'polynomial'
    INCOMPRESSIBLE_PERFECT_GAS = 'incompressiblePerfectGas'
    REAL_GAS_PENG_ROBINSON = 'PengRobinsonGas'


class MaterialType(Enum):
    NONMIXTURE = 'nonmixture'
    MIXTURE = 'mixture'
    SPECIE = 'specie'


class IMaterialObserver(QObject):
    def specieAdded(self, db, mid: int, mixtureID):
        pass

    def materialRemoving(self, db, mid: int):
        pass

    def specieRemoving(self, db, mid: int, primarySpecie):
        pass

    def _removeSpecieInComposition(self, primarySpecie, specieElement):
        mixture = specieElement.getparent()
        mixture.remove(specieElement)

        allZero = True
        for specie in xml.getElements(mixture, 'specie'):
            allZero = allZero and (float(xml.getText(specie, 'value')) == 0)

        if allZero:
            element = xml.getElement(mixture, f'specie[mid="{primarySpecie}"]')
            xml.setText(element, 'value', '1')


def _rootElement():
    return coredb.CoreDB().getElement('materials')


def _newID(db):
    return db.availableID(MATERIAL_XPATH, 'mid')


def _newName(db, name):
    return db.toUniqueText(MATERIAL_XPATH, 'name', name)


class MaterialDB(object):
    MATERIALS_XPATH = 'materials'

    _observers = []

    @classmethod
    def registerObserver(cls, observer):
        cls._observers.append(observer)

    @classmethod
    def getXPath(cls, mid) -> str:
        return f'{MATERIAL_XPATH}[@mid="{mid}"]'

    @classmethod
    def getXPathByName(cls, name) -> str:
        return f'{MATERIAL_XPATH}[name="{name}"]'

    @classmethod
    def getName(cls, mid):
        return coredb.CoreDB().getValue(cls.getXPath(mid) + '/name')

    @classmethod
    def getPhase(cls, mid) -> Phase:
        return Phase(coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase'))

    @classmethod
    def getType(cls, mid):
        return MaterialType(coredb.CoreDB().getValue(cls.getXPath(mid) + '/type'))

    @classmethod
    def getCoolPropName(cls, mid) -> str:
        name = coredb.CoreDB().getValue(f'{MaterialDB.getXPath(mid)}/name')
        return coredb.CoreDB().materialDB[name]['CoolPropName']

    @classmethod
    def dbTextToPhase(cls, DBText) -> Phase:
        if DBText == 'gas':
            return Phase.GAS
        elif DBText == 'liquid':
            return Phase.LIQUID
        elif DBText == 'solid':
            return Phase.SOLID
        
    @classmethod
    def getPhaseText(cls, phase) -> str:
        return {
            Phase.GAS:      QCoreApplication.translate('MaterialDB', 'Gas'),
            Phase.LIQUID:   QCoreApplication.translate('MaterialDB', 'Liquid'),
            Phase.SOLID:    QCoreApplication.translate('MaterialDB', 'Solid')
        }.get(phase)

    @classmethod
    def specificationToText(cls, specification) -> str:
        return {
            Specification.CONSTANT:                     QCoreApplication.translate('MaterialDB', 'Constant'),
            Specification.PERFECT_GAS:                  QCoreApplication.translate('MaterialDB', 'Perfect Gas'),
            Specification.SUTHERLAND:                   QCoreApplication.translate('MaterialDB', 'Sutherland'),
            Specification.POLYNOMIAL:                   QCoreApplication.translate('MaterialDB', 'Polynomial'),
            Specification.INCOMPRESSIBLE_PERFECT_GAS:   QCoreApplication.translate('MaterialDB',
                                                                                   'Incompressible-perfect-gas'),
            Specification.REAL_GAS_PENG_ROBINSON:       QCoreApplication.translate('MaterialDB',
                                                                                   'Real-gas-peng-robinson'),
        }.get(Specification(specification))

    @classmethod
    def dbSpecificationToText(cls, DBText) -> str:
        return cls.specificationToText(Specification(DBText))

    @classmethod
    def isMaterialExists(cls, name) -> bool:
        return coredb.CoreDB().exists(f'{cls.MATERIALS_XPATH}/material[name="{name}"]')

    @classmethod
    def isFluid(cls, mid):
        return cls.getPhase(mid) != Phase.SOLID

    @classmethod
    def getMaterialComposition(cls, xpath, mid):
        if MaterialDB.getType(mid) == MaterialType.MIXTURE:
            return [(xml.getText(e, 'mid'), float(xml.getText(e, 'value')))
                    for e in coredb.CoreDB().getElements(f'{xpath}/mixture[mid="{mid}"]/specie')]

        return [(mid, 1)]

    @classmethod
    def getPrimarySpecie(cls, mid):
        return int(xml.getText(_rootElement(), f'material[@mid="{mid}"]/mixture/primarySpecie'))

    @classmethod
    def getSpecies(cls, mid):
        return {int(xml.getAttribute(e.getparent(), 'mid')): xml.getText(e.getparent(), 'name')
                for e in xml.getElements(_rootElement(), f'material/specie[mixture="{mid}"]')}

    @classmethod
    def getMaterialsFromDB(cls, phase):
        return _materialTemplates.getMaterials(phase)

    @classmethod
    def addMaterial(cls, db, template: str) -> int:
        mid = _newID(db)
        name = _newName(db, template)
        _rootElement().append(
            xml.createElement(
                _materialTemplates.materialXML(mid, 'name', template, MaterialTemplates.DEFAULT_NONMIXTURE_SPEC)))

        db.setValue(MaterialDB.getXPath(mid) + '/name', name)

        return mid

    @classmethod
    def addMixture(cls, db, name: str, species: list) -> str:
        materials = _rootElement()

        mid = _newID(db)
        materials.append(
            xml.createElement(
                _materialTemplates.materialXML(
                    mid, _newName(db, name),
                    MaterialTemplates.MIXTURE_TEMPLATE_NAME,
                    MaterialTemplates.Specifications('mixture', _materialTemplates.template(species[0])['phase']),
                    _materialTemplates.mixtureXML())))

        primary = 0
        specieXML = _materialTemplates.specieXML(mid)
        for specie in species:
            sid = _newID(db)
            materials.append(
                xml.createElement(
                    _materialTemplates.materialXML(
                        sid, _newName(db, specie), specie, MaterialTemplates.Specifications('specie'), specieXML)))
            primary = primary or sid

        db.setValue(MaterialDB.getXPath(mid) + '/mixture/primarySpecie', str(primary))

        return mid

    @classmethod
    def addSpecie(cls, db, template, mixtureID):
        mid = _newID(db)
        name = _newName(db, template)

        mixture = db.getElement(MaterialDB.getXPath(mixtureID))
        _rootElement().append(
            xml.createElement(
                _materialTemplates.materialXML(
                    mid, 'name', template,
                    MaterialTemplates.Specifications(
                        type='specie',
                        density=xml.getText(mixture, 'density/specification'),
                        specificHeat=xml.getText(mixture, 'specificHeat/specification'),
                        thermalConductivity=xml.getText(mixture, 'thermalConductivity/specification'),
                        viscosity=xml.getText(mixture, 'viscosity/specification')),
                    _materialTemplates.specieXML(mixtureID))))

        db.setValue(MaterialDB.getXPath(mid) + '/name', name)

        for observer in cls._observers:
            observer.specieAdded(db, mid, mixtureID)

        return mid

    @classmethod
    def removeMaterial(cls, db, mid: str):
        materials = _rootElement()

        material = xml.getElement(materials, f'material[@mid="{mid}"]')
        if material is None or xml.getText(material, 'type') == 'apecie':
            raise LookupError

        if len(xml.getElements(materials, f'material')) == 1:  # this is the last material in the list
            raise ConfigurationException(
                QCoreApplication.translate('MaterialDB',
                                           "Material cannot be removed. At least one material is required."))

        for observer in cls._observers:
            observer.materialRemoving(db, mid)

        materials.remove(material)

    @classmethod
    def removeSpecie(cls, db, mid: int):
        materials = _rootElement()

        specie = xml.getElement(materials, f'material[@mid="{mid}"]')
        if specie is None or xml.getText(specie, 'type') != 'specie':
            raise LookupError

        primarySpecie = None
        mixtureMid = xml.getText(specie, 'specie/mixture')
        mixture = xml.getElement(materials, f'material[@mid="{mixtureMid}"]')
        if int(xml.getText(mixture, f'mixture/primarySpecie')) == mid:
            species = xml.getElements(materials, f'material/specie[mixture="{mixtureMid}"]')
            mid1 = xml.getAttribute(species[0].getparent(), 'mid')
            mid2 = xml.getAttribute(species[1].getparent(), 'mid')
            primarySpecie = mid2 if int(mid1) == mid else mid1

        for observer in cls._observers:
            observer.specieRemoving(db, mid, primarySpecie)

        if primarySpecie is not None:
            db.setValue(MaterialDB.getXPath(mixtureMid) + 'mixture/primarySpecie', primarySpecie)

        materials.remove(specie)
