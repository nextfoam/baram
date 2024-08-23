#!/usr/bin/env python
# -*- coding: utf-8 -*-

import baramFlow.coredb.libdb as xml
from baramFlow.coredb import coredb
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import IMaterialObserver, MaterialDB
from baramFlow.coredb.region_db import IRegionMaterialObserver, RegionDB, REGION_XPATH
from baramFlow.coredb.scalar_model_db import IUserDefinedScalarObserver

INITIALIZATION_XPATH = REGION_XPATH + '/initialization'


class InitializationDB:
    @classmethod
    def getXPath(cls, rname):
        return f'{RegionDB.getXPath(rname)}/initialization'

    @classmethod
    def getSectionXPath(cls, rname, sectionName):
        return f'{cls.getXPath(rname)}/advanced/sections/section[name="{sectionName}"]'

    @classmethod
    def buildSectionUserDefinedScalar(cls, scalarId, value):
        return ('<scalar xmlns="http://www.baramcfd.org/baram">'
                f'  <scalarID>{scalarId}</scalarID>'
                f'  <value disabled="{"false" if value else "true"}">{value if value else 0}</value>'
                '</scalar>')


def getInitializationElement(rname):
    return coredb.CoreDB().getElement(InitializationDB.getXPath(rname))


class MaterialObserver(IMaterialObserver):
    def materialRemoving(self, db, mid: str):
        for volumeFraction in db.getElements(
                f'{INITIALIZATION_XPATH}/initialValues/volumeFractions/volumeFraction[material="{mid}"]'):
            volumeFraction.getparent().remove(volumeFraction)

        for volumeFraction in db.getElements(
                f'{INITIALIZATION_XPATH}/advanced/sections/section/volumeFractions/volumeFraction[material="{mid}"]'):
            volumeFraction.getparent().remove(volumeFraction)

    def specieAdded(self, db, mid: str, mixtureID):
        for mixture in db.getElements(f'{INITIALIZATION_XPATH}/initialValues/species/mixture[mid="{mixtureID}"]'):
            mixture.append(xml.createElement('<specie xmlns="http://www.baramcfd.org/baram">'
                                             f' <mid>{mid}</mid><value>0</value>'
                                             '</specie>'))

        for mixture in db.getElements(
                f'{INITIALIZATION_XPATH}/advanced/sections/section/species/mixture[mid="{mixtureID}"]'):
            mixture.append(xml.createElement('<specie xmlns="http://www.baramcfd.org/baram">'
                                             f' <mid>{mid}</mid><value>0</value>'
                                             '</specie>'))

    def specieRemoving(self, db, mid: str, primarySpecie: str):
        for specie in db.getElements(f'{INITIALIZATION_XPATH}/initialValues/species/mixture/specie[mid="{mid}"]'):
            self._removeSpecieInComposition(primarySpecie, specie)

        for specie in db.getElements(
                f'{INITIALIZATION_XPATH}/advanced/sections/section/species/mixture/specie[mid="{mid}"]'):
            self._removeSpecieInComposition(primarySpecie, specie)


class RegionMaterialObserver(IRegionMaterialObserver):
    def materialsUpdating(self, db, rname, primary, secondaries, species):
        ratiosXML = self._specieRatiosXML(species)
        initialValuesSpeciesXML = f'''<mixture xmlns="http://www.baramcfd.org/baram">
                                        <mid>{primary}</mid>{ratiosXML}
                                      </mixture>'''
        sectionSpeicesXML = f'''<mixture disabled="true" xmlns="http://www.baramcfd.org/baram">
                                    <mid>{primary}</mid>{ratiosXML}
                                </mixture>'''

        initialization = getInitializationElement(rname)

        volumeFractions = xml.getElement(initialization, 'initialValues/volumeFractions')
        # volumeFractions.clear()
        self._addVolumeFractions(volumeFractions, secondaries)

        initialSpecies = xml.getElement(initialization, 'initialValues/species')
        initialSpecies.clear()
        if species:
            initialSpecies.append(xml.createElement(initialValuesSpeciesXML))

        for section in xml.getElements(initialization, 'advanced/sections/section'):
            volumeFractions = xml.getElement(section, 'volumeFractions')
            # volumeFractions.clear()
            self._addVolumeFractions(volumeFractions, secondaries)

            if (not xml.getElements(section, '*[@disabled="false"]')
                    and not xml.getElements(section, 'userDefinedScalars/scalar/value[@disabled="false"]')):
                oldMaterial = RegionDB.getMaterial(rname)
                for mixture in xml.getElements(section, 'species/mixture[@disabled="false"]'):
                    if xml.getText(mixture, 'mid') != oldMaterial:
                        break
                else:

                    raise ConfigurationException(
                        self.tr('Material {0} has the only initialization setting in section {1},'
                                'so it cannot be changed to a different material.').format(
                            MaterialDB.getName(oldMaterial), xml.getText(section, 'name')))

            speciesElement = xml.getElement(section, 'species')
            speciesElement.clear()
            if species:
                speciesElement.append(xml.createElement(sectionSpeicesXML))

    def _addVolumeFractions(self, parent, mids: list[str]):
        for mid in mids:
            if xml.getElement(parent, f'volumeFraction[material="{mid}"]') is None:
                parent.append(xml.createElement('<volumeFraction xmlns="http://www.baramcfd.org/baram">'
                                                f'  <material>{mid}</material><fraction>0</fraction>'
                                                '</volumeFraction>'))


class ScalarObserver(IUserDefinedScalarObserver):
    def scalarAdded(self, db, scalarID):
        scalarXML = f'''<scalar xmlns="http://www.baramcfd.org/baram">
                            <scalarID>{scalarID}</scalarID>
                            <value disabled="true">0</value>
                        </scalar>'''

        for scalars in db.getElements(f'{INITIALIZATION_XPATH}/initialValues/userDefinedScalars'):
            scalars.append(xml.createElement(scalarXML))

        for scalars in db.getElements(f'{INITIALIZATION_XPATH}/advanced/sections/section/userDefinedScalars'):
            scalars.append(xml.createElement(scalarXML))

    def scalarRemoving(self, db, scalarID):
        for scalars in db.getElements(f'{INITIALIZATION_XPATH}/initialValues/userDefinedScalars'):
            xml.removeElement(scalars, f'scalar[scalarID="{scalarID}"]')

        for scalars in db.getElements(f'{INITIALIZATION_XPATH}/advanced/sections/section/userDefinedScalars'):
            xml.removeElement(scalars, f'scalar[scalarID="{scalarID}"]')
