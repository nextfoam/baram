#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations
from math import sqrt

import logging

from lxml import etree
import pandas as pd

from resources import resource

logger = logging.getLogger(__name__)

_ns = 'http://www.baramcfd.org/baram'
_nsmap = {'': _ns}

MATERIALS_PATH = 'materials.csv'


def _addShowChartAndWriteIntervalV1(parent):
    if parent.find('showChart', namespaces=_nsmap) is None:
        logger.debug(f'    Adding showChart to {parent}')
        child = etree.Element(f'{{{_ns}}}showChart')
        child.text = 'false'
        parent.insert(1, child)

    if parent.find('writeInterval', namespaces=_nsmap) is None:
        logger.debug(f'    Adding writeInterval to {parent}')
        child = etree.Element(f'{{{_ns}}}writeInterval')
        child.text = '1'
        parent.insert(2, child)


def _version_1(root: etree.Element):
    logger.debug('  Upgrading to v2')
    # print(etree.tostring(root, xml_declaration=True, encoding='UTF-8'))
    root.set('version', '2')

    for p in root.findall(f'materials/material/density', namespaces=_nsmap):
        if p.find('polynomial', namespaces=_nsmap) is None:
            logger.debug(f'    Adding polynomial to {p}')
            # Add "polynomial" at the end of child elements
            etree.SubElement(p, f'{{{_ns}}}polynomial').text = ''

    for p in root.findall(f'regions/region/cellZones/cellZone/actuatorDisk', namespaces=_nsmap):
        if p.find('upstreamPoint', namespaces=_nsmap) is None:
            e = etree.fromstring('''
                <upstreamPoint xmlns="http://www.baramcfd.org/baram">
                    <x>0</x>
                    <y>0</y>
                    <z>0</z>
                </upstreamPoint>
            ''')
            p.insert(4, e)

    for p in root.findall(f'monitors/forces/forceMonitor', namespaces=_nsmap):
        _addShowChartAndWriteIntervalV1(p)

    for p in root.findall(f'monitors/points/pointMonitor', namespaces=_nsmap):
        _addShowChartAndWriteIntervalV1(p)

    for p in root.findall(f'monitors/surfaces/surfaceMonitor', namespaces=_nsmap):
        _addShowChartAndWriteIntervalV1(p)

        e = p.find('reportType', namespaces=_nsmap)
        if e.text == 'flowRate':
            logger.debug(f'    Changing flowRate to massFlowRate in {p}')
            e.text = 'massFlowRate'

    for p in root.findall(f'monitor/volumes/volumeMonitor', namespaces=_nsmap):
        _addShowChartAndWriteIntervalV1(p)

    # print(etree.tostring(root, xml_declaration=True, encoding='UTF-8'))


def _version_2(root: etree.Element):
    logger.debug('  Upgrading to v3')

    # print(etree.tostring(root, xml_declaration=True, encoding='UTF-8'))

    root.set('version', '3')

    for p in root.findall(f'regions/region', namespaces=_nsmap):
        if p.find('secondaryMaterials', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "secondaryMaterials" to {p}')
            e = etree.Element(f'{{{_ns}}}secondaryMaterials')
            p.insert(2, e)
        if p.find('phaseInteractions', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "phaseInteractions" to {p}')
            e = etree.fromstring('''
                <phaseInteractions xmlns="http://www.baramcfd.org/baram">
                    <surfaceTensions><material1/><material2/><surfaceTension/></surfaceTensions>
                </phaseInteractions>
            ''')
            p.insert(3, e)

    for p in root.findall(f'regions/region/cellZones/cellZone/sourceTerms', namespaces=_nsmap):
        if p.find('materials', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "materials" to {p}')
            e = etree.Element(f'{{{_ns}}}materials')
            p.insert(1, e)

    for p in root.findall(f'regions/region/boundaryConditions/boundaryCondition', namespaces=_nsmap):
        if p.find('volumeFractions', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "volumeFractions" to {p}')
            etree.SubElement(p, f'{{{_ns}}}volumeFractions')

    for p in root.findall(f'regions/region/boundaryConditions/boundaryCondition/wall', namespaces=_nsmap):
        if p.find('wallAdhesions', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "wallAdhesions" to {p}')
            e = etree.fromstring('''
                <wallAdhesions xmlns="http://www.baramcfd.org/baram">
                    <model>none</model>
                    <limit>none</limit>
                </wallAdhesions>
            ''')
            p.append(e)

    for p in root.findall(f'numericalConditions/underRelaxationFactors', namespaces=_nsmap):
        if p.find('volumeFraction', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "volumeFraction" to {p}')
            etree.SubElement(p, f'{{{_ns}}}volumeFraction').text = '0.7'
            etree.SubElement(p, f'{{{_ns}}}volumeFractionFinal').text = '1'

    for p in root.findall(f'numericalConditions', namespaces=_nsmap):
        if p.find('multiphase', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "multiphase" to {p}')
            e = etree.fromstring('''
                <multiphase xmlns="http://www.baramcfd.org/baram">
                    <maxIterationsPerTimeStep>2</maxIterationsPerTimeStep>
                    <numberOfCorrectors>1</numberOfCorrectors>
                    <useSemiImplicitMules>true</useSemiImplicitMules>
                    <phaseInterfaceCompressionFactor>1</phaseInterfaceCompressionFactor>
                    <numberOfMulesIterations>3</numberOfMulesIterations>
                </multiphase>
            ''')
            p.insert(7, e)

    for p in root.findall(f'numericalConditions/convergenceCriteria', namespaces=_nsmap):
        if p.find('volumeFraction', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "volumeFraction" to {p}')
            e = etree.fromstring('''
                <volumeFraction xmlns="http://www.baramcfd.org/baram">
                    <absolute>0.001</absolute>
                    <relative>0.05</relative>
                </volumeFraction>
            ''')
            p.append(e)

    if (p := root.find('initialization/initialValues', namespaces=_nsmap)) is not None:
        ux = p.find('velocity/x', namespaces=_nsmap).text
        uy = p.find('velocity/y', namespaces=_nsmap).text
        uz = p.find('velocity/z', namespaces=_nsmap).text
        pr = p.find('pressure', namespaces=_nsmap).text
        t = p.find('temperature', namespaces=_nsmap).text
        v = p.find('scaleOfVelocity', namespaces=_nsmap).text
        i = p.find('turbulentIntensity', namespaces=_nsmap).text
        b = p.find('turbulentViscosity', namespaces=_nsmap).text

        e = root.find('initialization', namespaces=_nsmap)
        root.remove(e)

        for p in root.findall(f'regions/region', namespaces=_nsmap):
            logger.debug(f'    Adding "initialization" to {p}')
            e = etree.fromstring(f'''
                    <initialization xmlns="http://www.baramcfd.org/baram">
                        <initialValues>
                            <velocity><x>{ux}</x><y>{uy}</y><z>{uz}</z></velocity>
                            <pressure>{pr}</pressure>
                            <temperature>{t}</temperature>
                            <scaleOfVelocity>{v}</scaleOfVelocity>
                            <turbulentIntensity>{i}</turbulentIntensity>
                            <turbulentViscosity>{b}</turbulentViscosity>
                            <volumeFractions></volumeFractions>
                        </initialValues>
                        <advanced>
                            <sections></sections>
                        </advanced>
                    </initialization>
                ''')
            p.append(e)

    for p in root.findall(f'runCalculation/runConditions', namespaces=_nsmap):
        if p.find('VoFMaxCourantNumber', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "VoFMaxCourantNumber" to {p}')
            e = etree.Element(f'{{{_ns}}}VoFMaxCourantNumber')
            e.text = '1'
            p.insert(4, e)

    for p in root.findall(f'materials/material', namespaces=_nsmap):
        if (e := p.find('surfaceTension', namespaces=_nsmap)) is not None:
            p.remove(e)

    if (p := root.find('general/operatingConditions/gravity', namespaces=_nsmap)) is not None:
        p.set('disabled', 'false')


def _version_3(root: etree.Element):
    logger.debug('  Upgrading to v4')

    root.set('version', '4')

    if (p := root.find('runCalculation', namespaces=_nsmap)) is not None:
        if p.find('batch', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "batch" to {p}')
            e = etree.fromstring('<batch xmlns="http://www.baramcfd.org/baram"><parameters/></batch>')
            p.append(e)

    if (p := root.find('models/turbulenceModels/k-epsilon/realizable', namespaces=_nsmap)) is not None:
        if p.find('threshold', namespaces=_nsmap) is None:
            e = etree.Element(f'{{{_ns}}}threshold')
            e.text = '60'
            p.append(e)

        if p.find('blendingWidth', namespaces=_nsmap) is None:
            e = etree.Element(f'{{{_ns}}}blendingWidth')
            e.text = '10'
            p.append(e)

    for p in root.findall(f'regions/region/phaseInteractions/surfaceTensions', namespaces=_nsmap):
        e1 = p.find('material1', namespaces=_nsmap)
        if e1 is not None:
            logger.debug(f'    Splitting surface tensions in {p}')
            e2 = p.find('material2', namespaces=_nsmap)
            e = p.find('surfaceTension', namespaces=_nsmap)

            p.remove(e)
            p.remove(e1)
            p.remove(e2)

            if e1.text is not None:
                mids1 = e1.text.split()
                mids2 = e2.text.split()
                values = e.text.split()

                for i in range(len(values)):
                    e = etree.fromstring(f'<surfaceTension xmlns="http://www.baramcfd.org/baram">'
                                         f' <mid>{mids1[i]}</mid><mid>{mids2[i]}</mid><value>{values[i]}</value>'
                                         f'</surfaceTension>')
                    p.append(e)


def _version_4(root: etree.Element):
    logger.debug('  Upgrading to v5')

    root.set('version', '5')

    if (pp := root.find('numericalConditions', namespaces=_nsmap)) is not None:
        if (p := pp.find('discretizationSchemes', namespaces=_nsmap)) is not None:
            if p.find('pressure', namespaces=_nsmap) is None:
                logger.debug(f'    Adding "pressure" to {p}')
                e = etree.fromstring(
                    '<pressure xmlns="http://www.baramcfd.org/baram">momentumWeightedReconstruct</pressure>')
                p.append(e)

        if pp.find('densityBasedSolverParameters', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "densityBasedSolverParameters" to {p}')
            e = etree.fromstring(
                '<densityBasedSolverParameters xmlns="http://www.baramcfd.org/baram">'
                '   <formulation>implicit</formulation>'
                '   <fluxType>roeFlux</fluxType>'
                '   <entropyFixCoefficient>0.5</entropyFixCoefficient>'
                '   <cutOffMachNumber>0.729</cutOffMachNumber>'
                '</densityBasedSolverParameters>')
            pp.insert(1, e)

    for e in root.findall('monitors/*/*/field/field[.="modifiedPressure"]', namespaces=_nsmap):
        logger.debug(f'    Replacing text of {e} to "pressure"')
        e.text = 'pressure'

    for p in root.findall('regions/region/boundaryConditions', namespaces=_nsmap):
        for e in p.findall('boundaryCondition/subsonicInflow', namespaces=_nsmap):
            e.tag = '{http://www.baramcfd.org/baram}subsonicInlet'

    if (p := root.find('numericalConditions/convergenceCriteria', namespaces=_nsmap)) is not None:
        if p.find('density', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "density" to {p}')
            e = etree.fromstring(
                '<density xmlns="http://www.baramcfd.org/baram">'
                '   <absolute>0.001</absolute><relative>0.05</relative>'
                '</density>')
            p.insert(1, e)

    for p in root.findall('regions/region/boundaryConditions/boundaryCondition/farFieldRiemann', namespaces=_nsmap):
        if p.find('flowDirection/specificationMethod', namespaces=_nsmap) is None:
            logger.debug(f'    Updating "flowDirection" to {p}')
            e = p.find('flowDirection', namespaces=_nsmap)
            logger.debug(e)
            x = e.find('x', namespaces=_nsmap).text
            y = e.find('y', namespaces=_nsmap).text
            z = e.find('z', namespaces=_nsmap).text
            p.remove(e)

            e = etree.fromstring(
                '<flowDirection xmlns="http://www.baramcfd.org/baram">'
                '   <specificationMethod>direct</specificationMethod>'
                f'  <dragDirection><x>{x}</x><y>{y}</y><z>{z}</z></dragDirection>'
                '   <liftDirection><x>0</x><y>1</y><z>0</z></liftDirection>'
                '   <angleOfAttack>0</angleOfAttack><angleOfSideslip>0</angleOfSideslip>'
                '</flowDirection>')
            p.insert(0, e)

    for p in root.findall('monitors/forces/forceMonitor', namespaces=_nsmap):
        if p.find('forceDirection', namespaces=_nsmap) is None:
            logger.debug(f'    Changing directions to "forceDirection" in {p}')
            e = p.find('liftDirection', namespaces=_nsmap)
            liftX = e.find('x', namespaces=_nsmap).text
            liftY = e.find('y', namespaces=_nsmap).text
            liftZ = e.find('z', namespaces=_nsmap).text
            p.remove(e)

            e = p.find('dragDirection', namespaces=_nsmap)
            dragX = e.find('x', namespaces=_nsmap).text
            dragY = e.find('y', namespaces=_nsmap).text
            dragZ = e.find('z', namespaces=_nsmap).text
            p.remove(e)

            e = etree.fromstring(
                '<forceDirection xmlns="http://www.baramcfd.org/baram">'
                '   <specificationMethod>direct</specificationMethod>'
                f'  <dragDirection><x>{dragX}</x><y>{dragY}</y><z>{dragZ}</z></dragDirection>'
                f'  <liftDirection><x>{liftX}</x><y>{liftY}</y><z>{liftZ}</z></liftDirection>'
                '   <angleOfAttack>0</angleOfAttack><angleOfSideslip>0</angleOfSideslip>'
                '</forceDirection>')
            p.insert(3, e)


def _version_5(root: etree.Element):
    logger.debug('  Upgrading to v6')

    root.set('version', '6')

    for p in root.findall('models/turbulenceModels', namespaces=_nsmap):
        if p.find('des', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "des" to {p}')
            e = etree.fromstring(
                '<des xmlns="http://www.baramcfd.org/baram">'
                '   <RANSModel>spalartAllmaras</RANSModel>'
                '   <spalartAllmarasOptions>'
                '       <lowReDamping>true</lowReDamping>'
                '   </spalartAllmarasOptions>'
                '   <DESOptions>'
                '       <delayedDES>false</delayedDES>'
                '   </DESOptions>'
                '   <modelConstants>'
                '       <DES>0.65</DES>'
                '       <DESKOmega>0.82</DESKOmega>'
                '       <DESKEpsilon>0.6</DESKEpsilon>'
                '   </modelConstants>'
                '   <shieldingFunctions>DDES</shieldingFunctions>'
                '   <lengthScaleModel>cubeRootVol</lengthScaleModel>'
                '</des>')
            p.insert(3, e)

    for p in root.findall('models/turbulenceModels', namespaces=_nsmap):
        if p.find('les', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "les" to {p}')
            e = etree.fromstring(
                '<les xmlns="http://www.baramcfd.org/baram">'
                '   <subgridScaleModel>Smagorinsky</subgridScaleModel>'
                '   <lengthScaleModel>cubeRootVol</lengthScaleModel>'
                '   <modelConstants><k>0.094</k><e>1.048</e><w>0.325</w></modelConstants>'
                '</les>')
            p.insert(4, e)

    for p in root.findall('regions/region/boundaryConditions/boundaryCondition/turbulence', namespaces=_nsmap):
        if p.find('les', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "les" to {p}')

            e = etree.fromstring(
                '<les xmlns="http://www.baramcfd.org/baram">'
                '   <specification>subgridScaleK</specification>'
                '   <subgridKineticEnergy>1</subgridKineticEnergy>'
                '   <subgridTurbulentIntensity>1</subgridTurbulentIntensity>'
                '   <turbulentViscosityRatio>10</turbulentViscosityRatio>'
                '</les>')
            p.append(e)

    for p in root.findall(f'monitors/points/pointMonitor', namespaces=_nsmap):
        if p.find('region', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "region" to {p}')
            etree.SubElement(p, f'{{{_ns}}}region').text = ''

    if (p := root.find('models', namespaces=_nsmap)) is not None:
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.fromstring(
                '<userDefinedScalars xmlns="http://www.baramcfd.org/baram">'
                '   <scalar scalarID="0">'
                '       <fieldName/>'
                '       <region/>'
                '       <material>0</material>'
                '       <diffusivity>'
                '           <specificationMethod>constant</specificationMethod>'
                '           <constant>0</constant>'
                '           <laminarAndTurbulentViscosity>'
                '               <laminarViscosityCoefficient>1</laminarViscosityCoefficient>'
                '               <turbulentViscosityCoefficient>1</turbulentViscosityCoefficient>'
                '           </laminarAndTurbulentViscosity>'
                '       </diffusivity>'
                '   </scalar>'
                '</userDefinedScalars>')
            p.append(e)

    if (p := root.find('general/atmosphericBoundaryLayer', namespaces=_nsmap)) is not None:
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.Element(f'{{{_ns}}}userDefinedScalars')
            p.append(e)

    for p in root.findall('regions/region/cellZones/cellZone/sourceTerms', namespaces=_nsmap):
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.Element(f'{{{_ns}}}userDefinedScalars')
            p.append(e)

    for p in root.findall('regions/region/cellZones/cellZone/fixedValues', namespaces=_nsmap):
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.Element(f'{{{_ns}}}userDefinedScalars')
            p.append(e)

    for p in root.findall('regions/region/boundaryConditions/boundaryCondition', namespaces=_nsmap):
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.Element(f'{{{_ns}}}userDefinedScalars')
            p.append(e)

    for p in root.findall('regions/region/initialization/initialValues', namespaces=_nsmap):
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.Element(f'{{{_ns}}}userDefinedScalars')
            p.append(e)

    for p in root.findall('regions/region/initialization/advanced/sections/section', namespaces=_nsmap):
        if p.find('userDefinedScalars', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "userDefinedScalars" to {p}')

            e = etree.Element(f'{{{_ns}}}userDefinedScalars')
            p.insert(10, e)

    if (p := root.find('numericalConditions/discretizationSchemes', namespaces=_nsmap)) is not None:
        if p.find('scalar', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "scalar" to {p}')

            e = etree.Element(f'{{{_ns}}}scalar')
            e.text = 'secondOrderUpwind'
            p.append(e)

    if (p := root.find('numericalConditions/underRelaxationFactors', namespaces=_nsmap)) is not None:
        if p.find('scalar', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "scalar, scalarFinal" to {p}')

            e = etree.Element(f'{{{_ns}}}scalar')
            e.text = '0.7'
            p.append(e)

            e = etree.Element(f'{{{_ns}}}scalarFinal')
            e.text = '1'
            p.append(e)

    if (p := root.find('numericalConditions/convergenceCriteria', namespaces=_nsmap)) is not None:
        if p.find('scalar', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "scalar" to {p}')

            e = etree.fromstring(
                '<scalar xmlns="http://www.baramcfd.org/baram">'
                '   <absolute>0.001</absolute><relative>0.05</relative>'
                '</scalar>')
            p.append(e)

    for e in root.findall('monitors/*/*/field/mid', namespaces=_nsmap):
        e.tag = f'{{{_ns}}}fieldID'

    if (p := root.find('numericalConditions/advanced/limits', namespaces=_nsmap)) is not None:
        if p.find('maximumViscosityRatio', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "maximumViscosityRatio" to {p}')

            e = etree.Element(f'{{{_ns}}}maximumViscosityRatio')
            e.text = '1e5'
            p.append(e)

    for p in root.findall('regions/region/boundaryConditions/boundaryCondition/pressureOutlet', namespaces=_nsmap):
        if p.find('nonReflective', namespaces=_nsmap) is None:
            logger.debug(f'    nonReflective option to {p}')

            e = etree.Element(f'{{{_ns}}}nonReflective')
            e.text = 'false'
            p.insert(1, e)


def _version_6(root: etree.Element):
    logger.debug('  Upgrading to v7')

    root.set('version', '7')
    if (p := root.find('numericalConditions/advanced', namespaces=_nsmap)) is not None:
        if p.find('equations', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "equations" to {p}')

            includeEnergyTerms = ('true'
                                  if root.find('general/solverType', namespaces=_nsmap).text == 'densityBased'
                                  else 'false')

            e = etree.fromstring(
                '<equations xmlns="http://www.baramcfd.org/baram">'
                '   <flow>true</flow>'
                '   <energy disabled="false">'
                f'      <includeViscousDissipationTerms>{includeEnergyTerms}</includeViscousDissipationTerms>'
                f'      <includeKineticEnergyTerms>{includeEnergyTerms}</includeKineticEnergyTerms>'
                f'      <includePressureWorkTerms>{includeEnergyTerms}</includePressureWorkTerms>'
                '   </energy>'
                '   <UDS>true</UDS>'
                '</equations>')
            p.append(e)

    df = pd.read_csv(resource.file(MATERIALS_PATH), header=0, index_col=0).transpose()
    materialDB = df.where(pd.notnull(df), None).fillna(1).to_dict()

    air = materialDB['aluminum']
    for p in root.findall('materials/material', namespaces=_nsmap):
        name = p.find('name', namespaces=_nsmap).text
        properties = materialDB.get(name, air)

        if p.find('type', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "type" to {p}')

            e = etree.Element(f'{{{_ns}}}type')
            e.text = 'nonmixture'
            p.insert(1, e)

        if p.find('phase', namespaces=_nsmap).text == 'gas':
            if (density := p.find('density', namespaces=_nsmap)) is not None:
                if density.find('pengRobinsonParameters', namespaces=_nsmap) is None:
                    logger.debug(f'    Adding "pengRobinsonParameters" to {p}')

                    e = etree.fromstring('<pengRobinsonParameters xmlns="http://www.baramcfd.org/baram">'
                                         f' <criticalTemperature>{properties["criticalTemperature"]}</criticalTemperature>'
                                         f' <criticalPressure>{properties["criticalPressure"]}</criticalPressure>'
                                         f' <criticalSpecificVolume>'
                                         f'     {round(1 / float(properties["criticalDensity"]), 4)}'
                                         f' </criticalSpecificVolume>'
                                         f' <acentricFactor>{properties["acentricFactor"]}</acentricFactor>'
                                         '</pengRobinsonParameters>')
                    density.append(e)

    if (p := root.find('models/turbulenceModels', namespaces=_nsmap)) is not None:
        if p.find('turbulentSchmidtNumber', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "turbulentSchmidtNumber" to {p}')

            e = etree.Element(f'{{{_ns}}}turbulentSchmidtNumber')
            e.text = '0.7'
            p.append(e)

    for p in root.findall('regions/region/cellZones/cellZone/fixedValues', namespaces=_nsmap):
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            p.append(e)

    for p in root.findall('regions/region/boundaryConditions/boundaryCondition', namespaces=_nsmap):
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            p.append(e)

    for p in root.findall('regions/region/initialization/initialValues', namespaces=_nsmap):
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            p.append(e)

    for p in root.findall('regions/region/initialization/advanced/sections/section', namespaces=_nsmap):
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            p.insert(11, e)

    if (p := root.find('numericalConditions/discretizationSchemes', namespaces=_nsmap)) is not None:
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            e.text = 'firstOrderUpwind'
            p.append(e)

    if (p := root.find('numericalConditions/underRelaxationFactors', namespaces=_nsmap)) is not None:
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species, speciesFinal" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            e.text = '0.3'
            p.append(e)

            e = etree.Element(f'{{{_ns}}}speciesFinal')
            e.text = '1'
            p.append(e)

    if (p := root.find('numericalConditions/convergenceCriteria', namespaces=_nsmap)) is not None:
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.fromstring(
                '<species xmlns="http://www.baramcfd.org/baram">'
                '   <absolute>0.001</absolute><relative>0.05</relative>'
                '</species>')
            p.append(e)

    if (p := root.find('numericalConditions/advanced/equations', namespaces=_nsmap)) is not None:
        if p.find('species', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "species" to {p}')

            e = etree.Element(f'{{{_ns}}}species')
            e.text = 'true'
            p.append(e)


def _version_7(root: etree.Element):
    logger.debug('  Upgrading to v8')

    root.set('version', '8')

    if (p := root.find('general/atmosphericBoundaryLayer', namespaces=_nsmap)) is not None:
        if (e := p.find('userDefinedScalars', namespaces=_nsmap)) is not None:
            logger.debug(f'    Removing "userDefinedScalars" from {p}')
            p.remove(e)

    for p in root.findall('materials/material/viscosity', namespaces=_nsmap):
        if p.find('../phase', namespaces=_nsmap).text == 'liquid':
            if p.find('cross', namespaces=_nsmap) is None:
                logger.debug(f'    Adding "cross" to {p}')

                e = etree.fromstring(
                    '<cross xmlns="http://www.baramcfd.org/baram">'
                    '   <zeroShearViscosity>1e-01</zeroShearViscosity>'
                    '   <infiniteShearViscosity>1.5e-05</infiniteShearViscosity>'
                    '   <naturalTime>1</naturalTime>'
                    '   <powerLawIndex>0.5</powerLawIndex>'
                    '</cross>')
                p.append(e)

            if p.find('herschelBulkley', namespaces=_nsmap) is None:
                logger.debug(f'    Adding "herschelBulkley" to {p}')

                e = etree.fromstring(
                    '<herschelBulkley xmlns="http://www.baramcfd.org/baram">'
                    '   <zeroShearViscosity>1.5e-04</zeroShearViscosity>'
                    '   <yieldStressThreshold>1.75e-05</yieldStressThreshold>'
                    '   <consistencyIndex>8.9721e-3</consistencyIndex>'
                    '   <powerLawIndex>0.8601</powerLawIndex>'
                    '</herschelBulkley>')
                p.append(e)

            if p.find('carreau', namespaces=_nsmap) is None:
                logger.debug(f'    Adding "carreau" to {p}')

                e = etree.fromstring(
                    '<carreau xmlns="http://www.baramcfd.org/baram">'
                    '   <zeroShearViscosity>1e-01</zeroShearViscosity>'
                    '   <infiniteShearViscosity>0</infiniteShearViscosity>'
                    '   <relaxationTime>0.0084033613</relaxationTime>'
                    '   <powerLawIndex>0.353</powerLawIndex>'
                    '   <linearityDeviation>1.433</linearityDeviation>'
                    '</carreau>')
                p.append(e)

            if p.find('nonNewtonianPowerLaw', namespaces=_nsmap) is None:
                logger.debug(f'    Adding "nonNewtonianPowerLaw" to {p}')

                e = etree.fromstring(
                    '<nonNewtonianPowerLaw xmlns="http://www.baramcfd.org/baram">'
                    '   <maximumViscosity>1e-03</maximumViscosity>'
                    '   <minimumViscosity>1e-06</minimumViscosity>'
                    '   <consistencyIndex>8.42</consistencyIndex>'
                    '   <powerLawIndex>0.61</powerLawIndex>'
                    '</nonNewtonianPowerLaw>')
                p.append(e)

    for p in root.findall('models/userDefinedScalars/scalar', namespaces=_nsmap):
        e = p.find('diffusivity/specificationMethod', namespaces=_nsmap)
        if e.text == 'turbulentViscosity':
            logger.debug(f'    Updating "diffusivity" of {p}')

            e.text = 'laminarAndTurbulentViscosity'
            p.find('diffusivity/laminarAndTurbulentViscosity/laminarViscosityCoefficient', namespaces=_nsmap).text = '0'
            p.find('diffusivity/laminarAndTurbulentViscosity/turbulentViscosityCoefficient', namespaces=_nsmap).text = '1'

    for p in root.findall('regions/region/phaseInteractions', namespaces=_nsmap):
        if p.find('massTransfers', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "massTransfers" to {p}')
            e = etree.fromstring('<massTransfers xmlns="http://www.baramcfd.org/baram">'
                                 '  <massTransfer>'
                                 '      <from>0</from>'
                                 '      <to>0</to>'
                                 '      <mechanism>cavitation</mechanism>'
                                 '      <cavitation>'
                                 '          <model>none</model>'
                                 '          <vaporizationPressure>2300</vaporizationPressure>'
                                 '          <schnerrSauer>'
                                 '              <evaporationCoefficient>1</evaporationCoefficient>'
                                 '              <condensationCoefficient>1</condensationCoefficient>'
                                 '              <bubbleDiameter>2.0e-06</bubbleDiameter>'
                                 '              <bubbleNumberDensity>1.6e+13</bubbleNumberDensity>'
                                 '          </schnerrSauer>'
                                 '          <kunz>'
                                 '              <evaporationCoefficient>1000</evaporationCoefficient>'
                                 '              <condensationCoefficient>1000</condensationCoefficient>'
                                 '              <meanFlowTimeScale>0.005</meanFlowTimeScale>'
                                 '              <freeStreamVelocity>20.0</freeStreamVelocity>'
                                 '          </kunz>'
                                 '          <merkle>'
                                 '              <evaporationCoefficient>1e-3</evaporationCoefficient>'
                                 '              <condensationCoefficient>80</condensationCoefficient>'
                                 '              <meanFlowTimeScale>0.005</meanFlowTimeScale>'
                                 '              <freeStreamVelocity>20.0</freeStreamVelocity>'
                                 '          </merkle>'
                                 '          <zwartGerberBelamri>'
                                 '              <evaporationCoefficient>1</evaporationCoefficient>'
                                 '              <condensationCoefficient>1</condensationCoefficient>'
                                 '              <bubbleDiameter>2e-6</bubbleDiameter>'
                                 '              <nucleationSiteVolumeFraction>1e-3</nucleationSiteVolumeFraction>'
                                 '          </zwartGerberBelamri>'
                                 '      </cavitation>'
                                 '  </massTransfer>'
                                 '</massTransfers>')
            p.append(e)

    for p in root.findall('regions/region/boundaryConditions/boundaryCondition/wall/temperature', namespaces=_nsmap):
        if p.find('wallLayers', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "wallLayers" to {p}')
            e = etree.fromstring('<wallLayers disabled="true" xmlns="http://www.baramcfd.org/baram">'
                                 '  <thicknessLayers>0.001</thicknessLayers>'
                                 '  <thermalConductivityLayers>10</thermalConductivityLayers>'
                                 '</wallLayers>')
            p.append(e)

    for p in root.findall('runCalculation/runConditions', namespaces=_nsmap):
        if p.find('maxDiffusionNumber', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "maxDiffusionNumber" to {p}')
            e = etree.Element(f'{{{_ns}}}maxDiffusionNumber')
            e.text = '10'
            p.insert(5, e)


def _version_8(root: etree.Element):
    logger.debug('  Upgrading to v9')

    root.set('version', '9')

    for p in root.findall(f'regions/region/boundaryConditions/boundaryCondition/freeStream', namespaces=_nsmap):
        speed = '1'
        if p.find('flowDirection', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "flowDirection" to {p}')

            x, y, z = 1, 0, 0
            if (e := p.find('streamVelocity', namespaces=_nsmap)) is not None:
                x = e.find('x', namespaces=_nsmap).text
                y = e.find('y', namespaces=_nsmap).text
                z = e.find('z', namespaces=_nsmap).text

                p.remove(e)

                if s := sqrt(float(x) ** 2 + float(y) ** 2 + float(z) ** 2):
                    speed = '{:.6g}'.format(s)

            e = etree.fromstring('<flowDirection xmlns="http://www.baramcfd.org/baram">'
                                 '  <specificationMethod>direct</specificationMethod>'
                                 f' <flowDirection><x>{x}</x><y>{y}</y><z>{z}</z></flowDirection>'
                                 '  <dragDirection><x>1</x><y>0</y><z>0</z></dragDirection>'
                                 '  <liftDirection><x>0</x><y>1</y><z>0</z></liftDirection>'
                                 '  <angleOfAttack>0</angleOfAttack>'
                                 '  <angleOfSideslip>0</angleOfSideslip>'
                                 '</flowDirection>')
            p.insert(0, e)

        if p.find('speed', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "speed" to {p}')

            child = etree.Element(f'{{{_ns}}}speed')
            child.text = speed
            p.insert(1, child)

    for p in root.findall(f'regions/region/boundaryConditions/boundaryCondition/farFieldRiemann/flowDirection', namespaces=_nsmap):
        if p.find('flowDirection', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "flowDirection" to {p}')

            x, y, z = 1, 0, 0
            if (e := p.find('dragDirection', namespaces=_nsmap)) is not None:
                x = e.find('x', namespaces=_nsmap).text
                y = e.find('y', namespaces=_nsmap).text
                z = e.find('z', namespaces=_nsmap).text

            e = etree.fromstring(
                f'<flowDirection xmlns="http://www.baramcfd.org/baram"><x>{x}</x><y>{y}</y><z>{z}</z></flowDirection>')
            p.insert(1, e)

    if (p := root.find('numericalConditions/advanced', namespaces=_nsmap)) is not None:
        if p.find('collateralFields', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "collateralFields" to {p}')

            e = etree.fromstring('<collateralFields xmlns="http://www.baramcfd.org/baram">'
                                 '  <age>false</age>'
                                 '  <heatTransferCoefficient>false</heatTransferCoefficient>'
                                 '  <machNumber>false</machNumber>'
                                 '  <q>false</q>'
                                 '  <totalPressure>false</totalPressure>'
                                 '  <vorticity>false</vorticity>'
                                 '  <wallHeatFlux>false</wallHeatFlux>'
                                 '  <wallShearStress>false</wallShearStress>'
                                 '  <wallYPlus>false</wallYPlus>'
                                 '</collateralFields>')
            p.append(e)


def _version_9(root: etree.Element):
    logger.debug('  Upgrading to v10')

    root.set('version', '10')

    for p in root.findall(f'regions/region/boundaryConditions/boundaryCondition/wall/velocity', namespaces=_nsmap):
        if p.find('wallMotion', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "wallMotion" to {p}')

            e = p.find('type', namespaces=_nsmap)
            type_ = e.text

            wallMotion = 'stationaryWall'
            atmospheric = 'false'
            movingMotion = 'translationalMotion'
            shearCondition = 'noSlip'
            if type_ == 'slip':
                shearCondition = 'slip'
            elif type_ == 'atmosphericWall':
                atmospheric = 'true'
            elif type_ != 'noSlip':
                wallMotion = 'movingWall'

                if type_ == 'movingWall':
                    movingMotion = 'meshMotion'
                elif type_ == 'translationalMovingWall':
                    movingMotion = 'translationalMotion'
                elif type_ == 'rotationalMovingWall':
                    movingMotion = 'rotationalMotion'

            p.remove(e)

            e = etree.fromstring('<wallMotion xmlns="http://www.baramcfd.org/baram">'
                                 f' <type>{wallMotion}</type>'
                                 f' <stationaryWall><atmosphericWall>{atmospheric}</atmosphericWall></stationaryWall>'
                                 f' <movingWall><motion>{movingMotion}</motion></movingWall>'
                                 '</wallMotion>')
            p.insert(0, e)

            e = etree.fromstring(
                f'<shearCondition xmlns="http://www.baramcfd.org/baram">{shearCondition}</shearCondition>')
            p.insert(1, e)

            e = etree.fromstring('<wallRoughness xmlns="http://www.baramcfd.org/baram">'
                                 '  <height>0</height><constant>0.5</constant>'
                                 '</wallRoughness>')
            p.insert(2, e)

    for p in root.findall(f'regions/region/boundaryConditions/boundaryCondition/wall/temperature', namespaces=_nsmap):
        if p.find('externalEmissivity', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "externalEmissivity" to {p}')

            e = etree.Element(f'{{{_ns}}}externalEmissivity')
            e.text = '0'
            p.insert(5, e)

    if root.find('scaffolds', namespaces=_nsmap) is None:
        index = root.index(root.find('monitors', namespaces=_nsmap))
        p = etree.Element(f'{{{_ns}}}scaffolds')
        root.insert(index + 1, p)

        e = etree.Element(f'{{{_ns}}}boundaries')
        p.append(e)
        e = etree.Element(f'{{{_ns}}}diskScaffolds')
        p.append(e)
        e = etree.Element(f'{{{_ns}}}isoSurfaces')
        p.append(e)
        e = etree.Element(f'{{{_ns}}}lineScaffolds')
        p.append(e)
        e = etree.Element(f'{{{_ns}}}parallelograms')
        p.append(e)
        e = etree.Element(f'{{{_ns}}}planeScaffolds')
        p.append(e)
        e = etree.Element(f'{{{_ns}}}sphereScaffolds')
        p.append(e)

    if root.find('graphics', namespaces=_nsmap) is None:
        index = root.index(root.find('scaffolds', namespaces=_nsmap))
        p = etree.Element(f'{{{_ns}}}graphics')
        root.insert(index + 1, p)

    if (p := root.find('numericalConditions', namespaces=_nsmap)) is not None:
        if p.find('numberOfNonOrthogonalCorrectors', namespaces=_nsmap) is None:
            logger.debug(f'    Adding "numberOfNonOrthogonalCorrectors" to {p}')

            e = etree.Element(f'{{{_ns}}}numberOfNonOrthogonalCorrectors')
            e.text = '0'
            p.insert(8, e)


_fTable = [
    None,
    _version_1,
    _version_2,
    _version_3,
    _version_4,
    _version_5,
    _version_6,
    _version_7,
    _version_8,
    _version_9,
]

currentVersion = int(etree.parse(resource.file('configurations/baram.cfg.xsd')).getroot().get('version'))


def migrate(root: etree.Element):
    version = int(root.get('version'))
    logger.debug(f'Migrating from v{version} to v{currentVersion}')

    if version == currentVersion:
        logger.debug('Migration not necessary')
        return root
    elif version > currentVersion:
        logger.debug(f'Invalid version {version}(Latest {currentVersion})')
        raise IndexError
    else:
        for i in range(version, currentVersion):
            if i < len(_fTable):
                _fTable[i](root)
