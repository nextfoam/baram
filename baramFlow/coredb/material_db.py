#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication, QObject

from baramFlow.base.material.material import NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS
from baramFlow.coredb.general_db import GeneralDB
import baramFlow.coredb.libdb as xml
from baramFlow.base.material.material import Phase, MaterialType, SpecificHeatSpecification, DensitySpecification, TransportSpecification
from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from .configuraitions import ConfigurationException
from .material_schema import MaterialSchema
from .turbulence_model_db import ITurbulenceModelObserver, TurbulenceModelsDB, TurbulenceModel

MATERIAL_XPATH = '/materials/material'

class IMaterialObserver(QObject):
    def materialRemoving(self, db, mid: str):
        pass
    #
    # def mixtureAdded(self, db, mid: str, species, primary):
    #     pass
    #
    # def mixtureRemoving(self, db, mid: str):
    #     pass

    def specieAdded(self, db, mid: str, mixtureID):
        pass

    def specieRemoving(self, db, mid: str, primarySpecie: str):
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
    return coredb.CoreDB().getElement(MaterialDB.MATERIALS_XPATH)


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
    def getXPath(cls, mid: str) -> str:
        return f'{MATERIAL_XPATH}[@mid="{mid}"]'

    @classmethod
    def getXPathByName(cls, name: str) -> str:
        return f'{MATERIAL_XPATH}[name="{name}"]'

    @classmethod
    def getName(cls, mid: str):
        return coredb.CoreDB().getValue(cls.getXPath(mid) + '/name')

    @classmethod
    def getPhase(cls, mid: str) -> Phase:
        return Phase(coredb.CoreDB().getValue(cls.getXPath(mid) + '/phase'))

    @classmethod
    def getType(cls, mid: str):
        return MaterialType(coredb.CoreDB().getValue(cls.getXPath(mid) + '/type'))

    @classmethod
    def getChemicalFormula(cls, mid: str):
        return str(coredb.CoreDB().getValue(cls.getXPath(mid) + '/chemicalFormula'))

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
    def densitySpecToText(cls, spec) -> str:
        texts = {
            DensitySpecification.CONSTANT:                   QCoreApplication.translate('MaterialDB', 'Constant'),
            DensitySpecification.PERFECT_GAS:                QCoreApplication.translate('MaterialDB', 'Perfect Gas'),
            DensitySpecification.POLYNOMIAL:                 QCoreApplication.translate('MaterialDB', 'Polynomial'),
            DensitySpecification.INCOMPRESSIBLE_PERFECT_GAS: QCoreApplication.translate('MaterialDB',
                                                                                        'Incompressible-perfect-gas'),
            DensitySpecification.REAL_GAS_PENG_ROBINSON:     QCoreApplication.translate('MaterialDB',
                                                                                        'Real-gas-peng-robinson'),
            DensitySpecification.BOUSSINESQ:                 QCoreApplication.translate('MaterialDB', 'Boussinesq'),
            DensitySpecification.PERFECT_FLUID:              QCoreApplication.translate('MaterialDB', 'Perfect Fluid'),
            DensitySpecification.TABLE:                      QCoreApplication.translate('MaterialDB', 'Table'),
        }

        if spec in texts:
            return texts[spec]
        else:
            return 'Unknown Spec.'

    @classmethod
    def specificHeatSpecToText(cls, spec) -> str:
        texts = {
            SpecificHeatSpecification.CONSTANT:   QCoreApplication.translate('MaterialDB', 'Constant'),
            SpecificHeatSpecification.POLYNOMIAL: QCoreApplication.translate('MaterialDB', 'Polynomial'),
            SpecificHeatSpecification.JANAF:      QCoreApplication.translate('MaterialDB', 'JANAF'),
            SpecificHeatSpecification.TABLE:      QCoreApplication.translate('MaterialDB', 'Table'),
        }

        if spec in texts:
            return texts[spec]
        else:
            return 'Unknown Spec.'

    @classmethod
    def transportSpecToText(cls, spec) -> str:
        texts = {
            TransportSpecification.CONSTANT:         QCoreApplication.translate('MaterialDB', 'Constant'),
            TransportSpecification.SUTHERLAND:       QCoreApplication.translate('MaterialDB', 'Sutherland'),
            TransportSpecification.POLYNOMIAL:       QCoreApplication.translate('MaterialDB', 'Polynomial'),
            TransportSpecification.CROSS_POWER_LAW:  QCoreApplication.translate('MaterialDB', 'Cross'),
            TransportSpecification.HERSCHEL_BULKLEY: QCoreApplication.translate('MaterialDB', 'Herschel-bulkley'),
            TransportSpecification.BIRD_CARREAU:     QCoreApplication.translate('MaterialDB', 'Bird-Carreau'),
            TransportSpecification.POWER_LAW:        QCoreApplication.translate('MaterialDB', 'Non-newtonian-power-law'),
            TransportSpecification.TABLE:            QCoreApplication.translate('MaterialDB', 'Table'),
        }

        if spec in texts:
            return texts[spec]
        else:
            return 'Unknown Spec.'

    @classmethod
    def isMaterialExists(cls, name) -> bool:
        return coredb.CoreDB().exists(f'{cls.MATERIALS_XPATH}/material[name="{name}"]')

    @classmethod
    def isFluid(cls, mid):
        return cls.getPhase(mid) != Phase.SOLID

    @classmethod
    def isNonNewtonianSpecification(cls, specification):
        return specification in NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS

    @classmethod
    def getMaterialComposition(cls, xpath, mid: str):
        if MaterialDB.getType(mid) == MaterialType.MIXTURE:
            return [(xml.getText(e, 'mid'), float(xml.getText(e, 'value')))
                    for e in coredb.CoreDB().getElements(f'{xpath}/mixture[mid="{mid}"]/specie')]

        return [(mid, 1)]

    @classmethod
    def getPrimarySpecie(cls, mid: str) -> str:
        return xml.getText(_rootElement(), f'material[@mid="{mid}"]/mixture/primarySpecie')

    @classmethod
    def getSpecies(cls, mid: str):
        return {xml.getAttribute(e.getparent(), 'mid'): xml.getText(e.getparent(), 'name')
                for e in xml.getElements(_rootElement(), f'material/specie[mixture="{mid}"]')}

    @classmethod
    def getMixture(cls, mid: str):
        return xml.getText(coredb.CoreDB().getElement(MaterialDB.getXPath(mid) + '/specie'), 'mixture')

    @classmethod
    def getMaterials(cls, type_=None) -> list[(str, str, str, str)]:
        """Returns configured materials

        Returns configured materials with name, chemicalFormula and phase

        Args:
            type_: Material type (nonmixture, mixture, specie, or None)

        Returns:
            List of materials in tuple, '(id, name, chemicalFormula, phase)'
        """
        elements = coredb.CoreDB().getElements(f'/materials/material')

        if type_ is None:
            return [(xml.getAttribute(e, 'mid'),
                     xml.getText(e, 'name'),
                     xml.getText(e, 'type'),
                     xml.getText(e, 'phase'))
                    for e in elements if xml.getText(e, 'type') != 'specie']
        else:
            return [(xml.getAttribute(e, 'mid'),
                     xml.getText(e, 'name'),
                     xml.getText(e, 'type'),
                     xml.getText(e, 'phase'))
                    for e in elements if xml.getText(e, 'type') == type_]

    @classmethod
    def addNonMixture(cls, db, base: str) -> str:
        mid = _newID(db)
        name = _newName(db, base)
        _rootElement().append(MaterialSchema.newNonMixture(mid, name, base))
        db.setValue(MaterialDB.getXPath(mid) + '/name', name)   # For increase configuCount of CoreDB

        return mid

    @classmethod
    def addMixture(cls, db, name: str, specieBases: list) -> str:
        materials = _rootElement()

        mid = _newID(db)
        mixture = MaterialSchema.newMixture(mid,_newName(db, name), specieBases[0])
        materials.append(mixture)

        primary = None
        for base in specieBases:
            sid = _newID(db)
            materials.append(
                MaterialSchema.newSpecie(sid, _newName(db, base), base, MaterialSchema.defaultsToInherit(mixture), mid))
            if primary is None:
                primary = sid

        db.setValue(MaterialDB.getXPath(mid) + '/mixture/primarySpecie', primary)
        db.increaseConfigCount()

        return mid

    @classmethod
    def addSpecie(cls, db, base: str, mixtureID: str):
        mid = _newID(db)
        name = _newName(db, base)

        _rootElement().append(
            MaterialSchema.newSpecie(mid, name, base,
                                     MaterialSchema.defaultsToInherit(db.getElement(MaterialDB.getXPath(mixtureID))),
                                     mixtureID))

        for observer in cls._observers:
            observer.specieAdded(db, mid, mixtureID)

        db.increaseConfigCount()

        return mid

    @classmethod
    def removeMaterial(cls, db, mid: str):
        materials = _rootElement()

        material = xml.getElement(materials, f'material[@mid="{mid}"]')
        materialType = MaterialType(xml.getText(material, 'type'))
        if material is None or materialType == MaterialType.SPECIE:
            raise LookupError

        if len(xml.getElements(materials, f'material')) == 1:  # this is the last material in the list
            raise ConfigurationException(
                QCoreApplication.translate('MaterialDB',
                                           "Material cannot be removed. At least one material is required."))

        for observer in cls._observers:
            observer.materialRemoving(db, mid)

        if materialType == MaterialType.MIXTURE:
            for sid in MaterialDB.getSpecies(mid):
                xml.removeElement(materials, f'material[@mid="{sid}"]')

        materials.remove(material)

    @classmethod
    def removeSpecie(cls, db, mid: str):
        materials = _rootElement()

        specie = xml.getElement(materials, f'material[@mid="{mid}"]')
        if specie is None or xml.getText(specie, 'type') != 'specie':
            raise LookupError

        primarySpecie = None
        mixtureMid = xml.getText(specie, 'specie/mixture')
        mixture = xml.getElement(materials, f'material[@mid="{mixtureMid}"]')
        if xml.getText(mixture, f'mixture/primarySpecie') == mid:
            species = xml.getElements(materials, f'material/specie[mixture="{mixtureMid}"]')
            mid1 = xml.getAttribute(species[0].getparent(), 'mid')
            mid2 = xml.getAttribute(species[1].getparent(), 'mid')
            primarySpecie = mid2 if mid1 == mid else mid1

        for observer in cls._observers:
            observer.specieRemoving(db, mid, primarySpecie)

        if primarySpecie is not None:
            db.setValue(MaterialDB.getXPath(mixtureMid) + 'mixture/primarySpecie', primarySpecie)

        materials.remove(specie)

    @classmethod
    def availableDensitySpec(cls, mtype: MaterialType, phase: Phase) -> list[DensitySpecification]:
        densitySpecs = [
            DensitySpecification.CONSTANT,
        ]

        if ModelsDB.isEnergyModelOn():
            if phase == Phase.GAS:
                densitySpecs.extend([
                    DensitySpecification.PERFECT_GAS,
                    DensitySpecification.POLYNOMIAL,
                    DensitySpecification.INCOMPRESSIBLE_PERFECT_GAS,
                ])

                if GeneralDB.isPressureBased() \
                    and not ModelsDB().isMultiphaseModelOn() \
                    and mtype == MaterialType.NONMIXTURE:
                    densitySpecs.extend([
                        DensitySpecification.BOUSSINESQ,
                        DensitySpecification.REAL_GAS_PENG_ROBINSON,
                    ])

            elif phase == Phase.LIQUID:
                if not ModelsDB.isMultiphaseModelOn():
                    densitySpecs.append(DensitySpecification.POLYNOMIAL)

                if GeneralDB.isPressureBased() \
                    and not ModelsDB().isMultiphaseModelOn() \
                    and mtype == MaterialType.NONMIXTURE:
                    densitySpecs.append(DensitySpecification.PERFECT_FLUID)

            else:  #phase == Phase.SOLID
                densitySpecs.extend([
                    DensitySpecification.POLYNOMIAL,
                ])

        return densitySpecs


    @classmethod
    def availableSpecificHeatSpecs(cls, mtype: MaterialType, phase: Phase) -> list[SpecificHeatSpecification]:
        specificHeatSpecs = [
                SpecificHeatSpecification.CONSTANT,
        ]

        if ModelsDB.isEnergyModelOn():
            specificHeatSpecs.extend([
                    SpecificHeatSpecification.POLYNOMIAL,
            ])
            if phase == Phase.GAS:
                specificHeatSpecs.extend([
                    SpecificHeatSpecification.JANAF
                ])

        return specificHeatSpecs


    @classmethod
    def availableTransportSpecs(cls, mtype: MaterialType, phase: Phase) -> list[TransportSpecification]:
        transportSpecs = [
            TransportSpecification.CONSTANT,
        ]

        if phase == Phase.GAS:
            if ModelsDB.isEnergyModelOn():
                transportSpecs.extend([
                    TransportSpecification.SUTHERLAND,
                    TransportSpecification.POLYNOMIAL,
                ])

        elif phase == Phase.LIQUID:
            if ModelsDB.isEnergyModelOn():
                transportSpecs.extend([
                    TransportSpecification.POLYNOMIAL,
                ])

            if TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR:
                transportSpecs.extend([
                    TransportSpecification.CROSS_POWER_LAW,
                    TransportSpecification.HERSCHEL_BULKLEY,
                    TransportSpecification.BIRD_CARREAU,
                    TransportSpecification.POWER_LAW
                ])

        else:  #phase == Phase.SOLID
            if ModelsDB.isEnergyModelOn():
                transportSpecs.extend([
                    TransportSpecification.POLYNOMIAL,
                ])


        return transportSpecs


class TurbulenceModelObserver(ITurbulenceModelObserver):
    def modelUpdating(self, db, model):
        if TurbulenceModelsDB.getModel() == TurbulenceModel.LAMINAR:
            for transport in db.getElements(MaterialDB.MATERIALS_XPATH + '/material/transport'):
                if (TransportSpecification(xml.getText(transport, 'specification'))
                        in NON_NEWTONIAN_VISCOSITY_SPECIFICATIONS):
                    raise ConfigurationException(
                        self.tr('Non-newtonian material is configured, and turbulecne model must be laminar.'))


