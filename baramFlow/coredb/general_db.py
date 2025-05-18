#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from baramFlow.coredb import coredb


class SolverType(Enum):
    PRESSURE_BASED = 'pressureBased'
    DENSITY_BASED = 'densityBased'


class GeneralDB:
    GENERAL_XPATH = '/general'
    OPERATING_CONDITIONS_XPATH = '/general/operatingConditions'

    @classmethod
    def isTimeTransient(cls):
        return coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/timeTransient') == 'true'

    @classmethod
    def isCompressible(cls):
        return coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/flowType') == 'compressible'

    @classmethod
    def getSolverType(cls):
        return SolverType(coredb.CoreDB().getValue(cls.GENERAL_XPATH + '/solverType'))

    @classmethod
    def isDensityBased(cls):
        return cls.getSolverType() == SolverType.DENSITY_BASED

    @classmethod
    def isPressureBased(cls):
        return cls.getSolverType() == SolverType.PRESSURE_BASED

    @classmethod
    def isCompressibleDensity(cls):
        return cls.isCompressible() and cls.isDensityBased()
#
#
# class ScalarObserver(IUserDefinedScalarObserver):
#     ABL_SCALARS_XPATH = GeneralDB.GENERAL_XPATH + '/atmosphericBoundaryLayer/userDefinedScalars'
#
#     def scalarAdded(self, db, scalarID):
#         ABLScalars = db.getElement(self.ABL_SCALARS_XPATH)
#
#         ABLScalars.append(xml.createElement('<scalar xmlns="http://www.baramcfd.org/baram">'
#                                             f'  <scalarID>{scalarID}</scalarID>'
#                                             '   <value>0</value>'
#                                             '</scalar>'))
#
#     def scalarRemoving(self, db, scalarID):
#         xml.removeElement(db.getElement(self.ABL_SCALARS_XPATH), f'scalar[scalarID="{scalarID}"]')
#
#     def scalarsCleared(self, db):
#         db.clearElement(self.ABL_SCALARS_XPATH)
#
#
# class MaterialObserver(IMaterialObserver):
#     ABL_SPECIES_XPATH = GeneralDB.GENERAL_XPATH + '/atmosphericBoundaryLayer/species'
#
#     def mixtureAdded(self, db, mid: str, species, primary):
#         mixture = xml.createElement(f'<mixture xmlns="http://www.baramcfd.org/baram"><mid>{mid}</mid></mixture>')
#         for sid in species:
#             mixture.append(xml.createElement(f'<specie xmlns="http://www.baramcfd.org/baram">'
#                                              f' <mid>{sid}</mid><value>{1 if sid == primary else 0}</value>'
#                                              f'</specie>'))
#
#         db.getElement(self.ABL_SPECIES_XPATH).append(mixture)
#
#     def mixtureRemoving(self, db, mid: str):
#         xml.removeElement(db.getElement(self.ABL_SPECIES_XPATH), f'mixture[mid="{mid}"]')
#
#     def specieAdded(self, db, mid: str, mixtureID):
#         mixture = db.getElements(f'{self.ABL_SPECIES_XPATH}/mixture[mid="{mixtureID}"]')
#         mixture.append(xml.createElement('<specie xmlns="http://www.baramcfd.org/baram">'
#                                          f' <mid>{mid}</mid><value>0</value>'
#                                          '</specie>'))
#
#     def specieRemoving(self, db, mid: str, primarySpecie):
#         specie = db.getElement(f'{self.ABL_SPECIES_XPATH}/mixture/specie[mid="{mid}"]')
#         mixture = specie.getparent()
#         mixture.remove(specie)
#
#         # allZero = True
#         for specie in xml.getElements(mixture, 'specie'):
#             self._removeSpecieInComposition(primarySpecie, specie)
#         #     allZero = allZero and (float(xml.getText(specie, 'value')) == 0)
#         #
#         # if allZero:
#         #     element = xml.getElement(mixture, f'specie[mid="{primarySpecie}"]')
#         #     xml.setText(element, 'value', '1')
