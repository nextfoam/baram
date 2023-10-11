#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from baramFlow.coredb import coredb
from baramFlow.openfoam.system.fv_options import FvOptions


class TestFvOptions(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()

        self.rname = 'testRegion'
        self.czname = 'testZone'
        self.cznameAll = 'All'
        self._db.addRegion(self.rname)
        self._db.addCellZone(self.rname, self.czname)

        self.xpath = f'.//region[name="{self.rname}"]/cellZones/cellZone[name="{self.czname}"]'
        self.xpathAll = f'.//region[name="{self.rname}"]/cellZones/cellZone[name="All"]'

    def tearDown(self) -> None:
        coredb.destroy()

    # --------------------------------------------------------------------------
    def testZoneTypePorousDarcyForchheimer(self):
        self._db.setValue(self.xpath + '/zoneType', 'porous')
        xpath = self.xpath + '/porous'
        self._db.setValue(xpath + '/model', 'darcyForchheimer')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('DarcyForchheimer', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['type'])
        self.assertEqual([0.0, 0.0, 0.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['d'][2])
        self.assertEqual([0.0, 0.0, 0.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['f'][2])
        self.assertEqual([1.0, 0.0, 0.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['coordinateSystem']['rotation']['e1'])
        self.assertEqual([0.0, 0.0, 1.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['coordinateSystem']['rotation']['e2'])
        self.assertEqual('cellZone', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['selectionMode'])
        self.assertEqual(self.czname, content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['cellZone'])

    def testZoneTypePorousPowerLaw(self):
        self._db.setValue(self.xpath + '/zoneType', 'porous')
        xpath = self.xpath + '/porous'
        self._db.setValue(xpath + '/model', 'powerLaw')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('powerLaw', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['type'])
        self.assertEqual('0', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['powerLawCoeffs']['C0'])
        self.assertEqual('0', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['powerLawCoeffs']['C1'])
        self.assertEqual('cellZone', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['selectionMode'])
        self.assertEqual(self.czname, content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['cellZone'])

    # def testZoneTypeSlidingMesh(self):    # Not defined
    #     self._db.setValue(self.xpath + '/zoneType', 'slidingMesh')
    #     xpath = self.xpath + '/slidingMesh'
    #
    #     content = SlidingMeshDict(self.rname).build().asDict()
    #
    #     self.assertEqual('0', content[f'slidingMesh_{self.czname}']['rotatingSpeed'])
    #     self.assertEqual([0.0, 0.0, 0.0], content[f'slidingMesh_{self.czname}']['rotationAxisOrigin'])
    #     self.assertEqual([1.0, 0.0, 0.0], content[f'slidingMesh_{self.czname}']['rotationAxisDirection'])

    def testZoneTypeActuatorDisk(self):
        self._db.setValue(self.xpath + '/zoneType', 'actuatorDisk')
        xpath = self.xpath + '/actuatorDisk'

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual([1.0, 0.0, 0.0], content[f'actuationDiskSource_{self.czname}']['diskDir'])
        self.assertEqual(self._db.getValue(xpath + '/powerCoefficient'), content[f'actuationDiskSource_{self.czname}']['Cp'])
        self.assertEqual(self._db.getValue(xpath + '/thrustCoefficient'), content[f'actuationDiskSource_{self.czname}']['Ct'])
        self.assertEqual(self._db.getValue(xpath + '/diskArea'), content[f'actuationDiskSource_{self.czname}']['diskArea'])
        self.assertEqual('Froude', content[f'actuationDiskSource_{self.czname}']['variant'])
        self.assertEqual('points', content[f'actuationDiskSource_{self.czname}']['monitorMethod'])
        self.assertEqual(self._db.getVector(xpath + '/upstreamPoint'),
                         content[f'actuationDiskSource_{self.czname}']['monitorCoeffs']['points'][0])
        self.assertEqual('cellZone', content[f'actuationDiskSource_{self.czname}']['selectionMode'])
        self.assertEqual(self.czname, content[f'actuationDiskSource_{self.czname}']['cellZone'])

    # --------------------------------------------------------------------------
    def testSourceTermsMassConstant(self):
        xpath = self.xpath + '/sourceTerms/mass'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_rho']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_rho']['injectionRateSuSp']['rho']['Su'])

    def testSourceTermsMassPiecewiseLinear(self):
        xpath = self.xpath + '/sourceTerms/mass'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'piecewiseLinear')
        self._db.setValue(xpath + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpath + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_rho']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.czname}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsMassPolynomial(self):
        xpath = self.xpath + '/sourceTerms/mass'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'polynomial')
        self._db.setValue(xpath + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_rho']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.czname}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsEnergyConstant(self):
        xpath = self.xpath + '/sourceTerms/energy'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_h']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_h']['injectionRateSuSp']['h']['Su'])

    def testSourceTermsEnergyPiecewiseLinear(self):
        xpath = self.xpath + '/sourceTerms/energy'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'piecewiseLinear')
        self._db.setValue(xpath + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpath + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_h']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.czname}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsEnergyPolynomial(self):
        xpath = self.xpath + '/sourceTerms/energy'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'polynomial')
        self._db.setValue(xpath + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_h']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.czname}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsNutilda(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')

        xpath = self.xpath + '/sourceTerms/modifiedTurbulentViscosity'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_nuTilda']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_nuTilda']['injectionRateSuSp']['nuTilda']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_nuTilda']['selectionMode'])
        self.assertEqual(self.czname, content[f'scalarSource_{self.czname}_nuTilda']['cellZone'])

    def testSourceTermsK(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/sourceTerms/turbulentKineticEnergy'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_k']['volumeMode'])

        self.assertEqual('0', content[f'scalarSource_{self.czname}_k']['injectionRateSuSp']['k']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_k']['selectionMode'])
        self.assertEqual(self.czname, content[f'scalarSource_{self.czname}_k']['cellZone'])

    def testSourceTermsEpsilon(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/sourceTerms/turbulentDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_epsilon']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_epsilon']['injectionRateSuSp']['epsilon']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_epsilon']['selectionMode'])
        self.assertEqual(self.czname, content[f'scalarSource_{self.czname}_epsilon']['cellZone'])

    def testSourceTermsOmega(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpath = self.xpath + '/sourceTerms/specificDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_omega']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_omega']['injectionRateSuSp']['omega']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_omega']['selectionMode'])
        self.assertEqual(self.czname, content[f'scalarSource_{self.czname}_omega']['cellZone'])

    # --------------------------------------------------------------------------
    def testFixedValuesVelocity(self):
        xpath = self.xpath + '/fixedValues/velocity'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual([0, 0, 0], content[f'fixedVelocity_{self.czname}']['Ubar'])
        self.assertEqual('1', content[f'fixedVelocity_{self.czname}']['relaxation'])
        self.assertEqual('cellZone', content[f'fixedVelocity_{self.czname}']['selectionMode'])
        self.assertEqual(self.czname, content[f'fixedVelocity_{self.czname}']['cellZone'])

    def testFixedValuesTemperature(self):
        xpath = self.xpath + '/fixedValues/temperature'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('300', content[f'fixedTemperature_{self.czname}']['temperature'][1])
        self.assertEqual('cellZone', content[f'fixedTemperature_{self.czname}']['selectionMode'])
        self.assertEqual(self.czname, content[f'fixedTemperature_{self.czname}']['cellZone'])

    def testFixedValuesNutilda(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')
        xpath = self.xpath + '/fixedValues/modifiedTurbulentViscosity'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_nuTilda']['fieldValues']['nuTilda'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_nuTilda']['selectionMode'])
        self.assertEqual(self.czname, content[f'fixedValue_{self.czname}_nuTilda']['cellZone'])

    def testFixedValuesK(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/fixedValues/turbulentKineticEnergy'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_k']['fieldValues']['k'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_k']['selectionMode'])
        self.assertEqual(self.czname, content[f'fixedValue_{self.czname}_k']['cellZone'])

    def testFixedValuesEpsilon(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/fixedValues/turbulentDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_epsilon']['fieldValues']['epsilon'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_epsilon']['selectionMode'])
        self.assertEqual(self.czname, content[f'fixedValue_{self.czname}_epsilon']['cellZone'])

    def testFixedValuesOmega(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpath = self.xpath + '/fixedValues/specificDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_omega']['fieldValues']['omega'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_omega']['selectionMode'])
        self.assertEqual(self.czname, content[f'fixedValue_{self.czname}_omega']['cellZone'])

    # --------------------------------------------------------------------------
    # All Region
    # --------------------------------------------------------------------------
    def testSourceTermsMassConstantAll(self):
        xpathAll = self.xpathAll + '/sourceTerms/mass'
        self._db.setAttribute(xpathAll, 'disabled', 'false')
        self._db.setValue(xpathAll + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpathAll + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_rho']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.cznameAll}_rho']['injectionRateSuSp']['rho']['Su'])

    def testSourceTermsMassPiecewiseLinearAll(self):
        xpathAll = self.xpathAll + '/sourceTerms/mass'
        self._db.setAttribute(xpathAll, 'disabled', 'false')
        self._db.setValue(xpathAll + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpathAll + '/specification', 'piecewiseLinear')
        self._db.setValue(xpathAll + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpathAll + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_rho']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.cznameAll}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsMassPolynomialAll(self):
        xpathAll = self.xpathAll + '/sourceTerms/mass'
        self._db.setAttribute(xpathAll, 'disabled', 'false')
        self._db.setValue(xpathAll + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpathAll + '/specification', 'polynomial')
        self._db.setValue(xpathAll + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_rho']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.cznameAll}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsEnergyConstantAll(self):
        xpathAll = self.xpathAll + '/sourceTerms/energy'
        self._db.setAttribute(xpathAll, 'disabled', 'false')
        self._db.setValue(xpathAll + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpathAll + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_h']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.cznameAll}_h']['injectionRateSuSp']['h']['Su'])

    def testSourceTermsEnergyPiecewiseLinearAll(self):
        xpathAll = self.xpathAll + '/sourceTerms/energy'
        self._db.setAttribute(xpathAll, 'disabled', 'false')
        self._db.setValue(xpathAll + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpathAll + '/specification', 'piecewiseLinear')
        self._db.setValue(xpathAll + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpathAll + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_h']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.cznameAll}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsEnergyPolynomialAll(self):
        xpathAll = self.xpathAll + '/sourceTerms/energy'
        self._db.setAttribute(xpathAll, 'disabled', 'false')
        self._db.setValue(xpathAll + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpathAll + '/specification', 'polynomial')
        self._db.setValue(xpathAll + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_h']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.cznameAll}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsNutildaAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')

        xpathAll = self.xpathAll + '/sourceTerms/modifiedTurbulentViscosity'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_nuTilda']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.cznameAll}_nuTilda']['injectionRateSuSp']['nuTilda']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.cznameAll}_nuTilda']['selectionMode'])

    def testSourceTermsKAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')

        xpathAll = self.xpathAll + '/sourceTerms/turbulentKineticEnergy'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_k']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.cznameAll}_k']['injectionRateSuSp']['k']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.cznameAll}_k']['selectionMode'])

    def testSourceTermsEpsilonAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpathAll = self.xpathAll + '/sourceTerms/turbulentDissipationRate'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_epsilon']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.cznameAll}_epsilon']['injectionRateSuSp']['epsilon']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.cznameAll}_epsilon']['selectionMode'])

    def testSourceTermsOmegaAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpathAll = self.xpathAll + '/sourceTerms/specificDissipationRate'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.cznameAll}_omega']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.cznameAll}_omega']['injectionRateSuSp']['omega']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.cznameAll}_omega']['selectionMode'])

    # --------------------------------------------------------------------------
    def testFixedValuesVelocityAll(self):
        xpathAll = self.xpathAll + '/fixedValues/velocity'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual([0, 0, 0], content[f'fixedVelocity_All']['Ubar'])
        self.assertEqual('1', content[f'fixedVelocity_All']['relaxation'])
        self.assertEqual('all', content[f'fixedVelocity_All']['selectionMode'])

    def testFixedValuesTemperatureAll(self):
        xpathAll = self.xpathAll + '/fixedValues/temperature'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('300', content[f'fixedTemperature_All']['temperature'][1])
        self.assertEqual('all', content[f'fixedTemperature_All']['selectionMode'])

    def testFixedValuesNutildaAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')
        xpathAll = self.xpathAll + '/fixedValues/modifiedTurbulentViscosity'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.cznameAll}_nuTilda']['fieldValues']['nuTilda'])
        self.assertEqual('all', content[f'fixedValue_{self.cznameAll}_nuTilda']['selectionMode'])

    def testFixedValuesKAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpathAll = self.xpathAll + '/fixedValues/turbulentKineticEnergy'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.cznameAll}_k']['fieldValues']['k'])
        self.assertEqual('all', content[f'fixedValue_{self.cznameAll}_k']['selectionMode'])

    def testFixedValuesEpsilonAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpathAll = self.xpathAll + '/fixedValues/turbulentDissipationRate'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.cznameAll}_epsilon']['fieldValues']['epsilon'])
        self.assertEqual('all', content[f'fixedValue_{self.cznameAll}_epsilon']['selectionMode'])

    def testFixedValuesOmegaAll(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpathAll = self.xpathAll + '/fixedValues/specificDissipationRate'
        self._db.setAttribute(xpathAll, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.cznameAll}_omega']['fieldValues']['omega'])
        self.assertEqual('all', content[f'fixedValue_{self.cznameAll}_omega']['selectionMode'])


if __name__ == '__main__':
    unittest.main()
