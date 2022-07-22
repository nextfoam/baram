#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from coredb import coredb
from openfoam.system.fv_options import FvOptions


class TestFvOptions(unittest.TestCase):
    def setUp(self):
        self._db = coredb.CoreDB()

        self.rname = 'testRegion'
        self.czname = 'testZone'
        self.czname_all = 'All'
        self._db.addRegion(self.rname)
        self._db.addCellZone(self.rname, self.czname)

        self.xpath = f'.//region[name="{self.rname}"]/cellZones/cellZone[name="{self.czname}"]'
        self.xpath_all = f'.//region[name="{self.rname}"]/cellZones/cellZone[name="All"]'

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    # --------------------------------------------------------------------------
    def testZoneTypePorousDarcyForchheimer(self):
        self._db.setValue(self.xpath + '/zoneType', 'porous')
        xpath = self.xpath + '/porous'
        self._db.setValue(xpath + '/model', 'darcyForchheimer')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('darcyForchheimer', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['type'])
        self.assertEqual([0.0, 0.0, 0.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['d'][2])
        self.assertEqual([0.0, 0.0, 0.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['f'][2])
        self.assertEqual([1.0, 0.0, 0.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['coordinateSystem']['coordinateRotation']['e1'])
        self.assertEqual([0.0, 0.0, 1.0], content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['DarcyForchheimerCoeffs']['coordinateSystem']['coordinateRotation']['e2'])
        self.assertEqual('cellZone', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['selectionMode'])
        self.assertEqual('porosity', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['cellZone'])

    def testZoneTypePorousPowerLaw(self):
        self._db.setValue(self.xpath + '/zoneType', 'porous')
        xpath = self.xpath + '/porous'
        self._db.setValue(xpath + '/model', 'powerLaw')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('powerLaw', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['type'])
        self.assertEqual('0', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['powerLawCoeffs']['C0'])
        self.assertEqual('0', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['powerLawCoeffs']['C1'])
        self.assertEqual('cellZone', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['selectionMode'])
        self.assertEqual('porosity', content[f'porosity_{self.czname}']['explicitPorositySourceCoeffs']['cellZone'])

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
        self.assertEqual('0', content[f'actuationDiskSource_{self.czname}']['Cp'])
        self.assertEqual('0', content[f'actuationDiskSource_{self.czname}']['Ct'])
        self.assertEqual('0', content[f'actuationDiskSource_{self.czname}']['diskArea'])
        self.assertEqual([0.0, 0.0, 0.0], content[f'actuationDiskSource_{self.czname}']['upstreamPoint'])
        self.assertEqual('cellZone', content[f'actuationDiskSource_{self.czname}']['selectionMode'])
        self.assertEqual('porosity', content[f'actuationDiskSource_{self.czname}']['cellZone'])

    # --------------------------------------------------------------------------
    def testSourceTermsMass_constant(self):
        xpath = self.xpath + '/sourceTerms/mass'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_rho']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_rho']['injectionRateSuSp']['rho']['Su'])

    def testSourceTermsMass_piecewiseLinear(self):
        xpath = self.xpath + '/sourceTerms/mass'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'piecewiseLinear')
        self._db.setValue(xpath + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpath + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_rho']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.czname}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsMass_polynomial(self):
        xpath = self.xpath + '/sourceTerms/mass'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'polynomial')
        self._db.setValue(xpath + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_rho']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.czname}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsEnergy_constant(self):
        xpath = self.xpath + '/sourceTerms/energy'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_h']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_h']['injectionRateSuSp']['h']['Su'])

    def testSourceTermsEnergy_piecewiseLinear(self):
        xpath = self.xpath + '/sourceTerms/energy'
        self._db.setAttribute(xpath, 'disabled', 'false')
        self._db.setValue(xpath + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath + '/specification', 'piecewiseLinear')
        self._db.setValue(xpath + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpath + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_h']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.czname}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsEnergy_polynomial(self):
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
        self.assertEqual('porosity', content[f'scalarSource_{self.czname}_nuTilda']['cellZone'])

    def testSourceTermsK(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/sourceTerms/turbulentKineticEnergy'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_k']['volumeMode'])

        self.assertEqual('0', content[f'scalarSource_{self.czname}_k']['injectionRateSuSp']['k']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_k']['selectionMode'])
        self.assertEqual('porosity', content[f'scalarSource_{self.czname}_k']['cellZone'])

    def testSourceTermsEpsilon(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/sourceTerms/turbulentDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_epsilon']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_epsilon']['injectionRateSuSp']['epsilon']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_epsilon']['selectionMode'])
        self.assertEqual('porosity', content[f'scalarSource_{self.czname}_epsilon']['cellZone'])

    def testSourceTermsOmega(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpath = self.xpath + '/sourceTerms/specificDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname}_omega']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname}_omega']['injectionRateSuSp']['omega']['Su'])
        self.assertEqual('cellZone', content[f'scalarSource_{self.czname}_omega']['selectionMode'])
        self.assertEqual('porosity', content[f'scalarSource_{self.czname}_omega']['cellZone'])

    # --------------------------------------------------------------------------
    def testFixedValuesVelocity(self):
        xpath = self.xpath + '/fixedValues/velocity'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual([0, 0, 0], content[f'fixedVelocity_{self.czname}']['Ubar'])
        self.assertEqual('0', content[f'fixedVelocity_{self.czname}']['relaxation'])
        self.assertEqual('cellZone', content[f'fixedVelocity_{self.czname}']['selectionMode'])
        self.assertEqual('porosity', content[f'fixedVelocity_{self.czname}']['cellZone'])

    def testFixedValuesTemperature(self):
        xpath = self.xpath + '/fixedValues/temperature'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('300', content[f'fixedTemperature_{self.czname}']['temperature'][1])
        self.assertEqual('cellZone', content[f'fixedTemperature_{self.czname}']['selectionMode'])
        self.assertEqual('porosity', content[f'fixedTemperature_{self.czname}']['cellZone'])

    def testFixedValuesNutilda(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')
        xpath = self.xpath + '/fixedValues/modifiedTurbulentViscosity'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_nuTilda']['fieldValues']['nuTilda'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_nuTilda']['selectionMode'])
        self.assertEqual('porosity', content[f'fixedValue_{self.czname}_nuTilda']['cellZone'])

    def testFixedValuesK(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/fixedValues/turbulentKineticEnergy'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_k']['fieldValues']['k'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_k']['selectionMode'])
        self.assertEqual('porosity', content[f'fixedValue_{self.czname}_k']['cellZone'])

    def testFixedValuesEpsilon(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath = self.xpath + '/fixedValues/turbulentDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_epsilon']['fieldValues']['epsilon'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_epsilon']['selectionMode'])
        self.assertEqual('porosity', content[f'fixedValue_{self.czname}_epsilon']['cellZone'])

    def testFixedValuesOmega(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpath = self.xpath + '/fixedValues/specificDissipationRate'
        self._db.setAttribute(xpath, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname}_omega']['fieldValues']['omega'])
        self.assertEqual('cellZone', content[f'fixedValue_{self.czname}_omega']['selectionMode'])
        self.assertEqual('porosity', content[f'fixedValue_{self.czname}_omega']['cellZone'])

    # --------------------------------------------------------------------------
    # All Region
    # --------------------------------------------------------------------------
    def testSourceTermsMass_constant_all(self):
        xpath_all = self.xpath_all + '/sourceTerms/mass'
        self._db.setAttribute(xpath_all, 'disabled', 'false')
        self._db.setValue(xpath_all + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath_all + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_rho']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname_all}_rho']['injectionRateSuSp']['rho']['Su'])

    def testSourceTermsMass_piecewiseLinear_all(self):
        xpath_all = self.xpath_all + '/sourceTerms/mass'
        self._db.setAttribute(xpath_all, 'disabled', 'false')
        self._db.setValue(xpath_all + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath_all + '/specification', 'piecewiseLinear')
        self._db.setValue(xpath_all + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpath_all + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_rho']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.czname_all}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsMass_polynomial_all(self):
        xpath_all = self.xpath_all + '/sourceTerms/mass'
        self._db.setAttribute(xpath_all, 'disabled', 'false')
        self._db.setValue(xpath_all + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath_all + '/specification', 'polynomial')
        self._db.setValue(xpath_all + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_rho']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.czname_all}_rho']['injectionRateSuSp']['rho']['Su'][1])

    def testSourceTermsEnergy_constant_all(self):
        xpath_all = self.xpath_all + '/sourceTerms/energy'
        self._db.setAttribute(xpath_all, 'disabled', 'false')
        self._db.setValue(xpath_all + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath_all + '/specification', 'constant')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_h']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname_all}_h']['injectionRateSuSp']['h']['Su'])

    def testSourceTermsEnergy_piecewiseLinear_all(self):
        xpath_all = self.xpath_all + '/sourceTerms/energy'
        self._db.setAttribute(xpath_all, 'disabled', 'false')
        self._db.setValue(xpath_all + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath_all + '/specification', 'piecewiseLinear')
        self._db.setValue(xpath_all + '/piecewiseLinear/t', '0 1 2 3')
        self._db.setValue(xpath_all + '/piecewiseLinear/v', '4 5 6 7')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_h']['volumeMode'])
        self.assertEqual([['0', '4'], ['1', '5'], ['2', '6'], ['3', '7']], content[f'scalarSource_{self.czname_all}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsEnergy_polynomial_all(self):
        xpath_all = self.xpath_all + '/sourceTerms/energy'
        self._db.setAttribute(xpath_all, 'disabled', 'false')
        self._db.setValue(xpath_all + '/unit', 'valueForEntireCellZone')

        self._db.setValue(xpath_all + '/specification', 'polynomial')
        self._db.setValue(xpath_all + '/polynomial', '2 3 4 5')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_h']['volumeMode'])
        self.assertEqual([['2', 0], ['3', 1], ['4', 2], ['5', 3]], content[f'scalarSource_{self.czname_all}_h']['injectionRateSuSp']['h']['Su'][1])

    def testSourceTermsNutilda_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')

        xpath_all = self.xpath_all + '/sourceTerms/modifiedTurbulentViscosity'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_nuTilda']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname_all}_nuTilda']['injectionRateSuSp']['nuTilda']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.czname_all}_nuTilda']['selectionMode'])

    def testSourceTermsK_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')

        xpath_all = self.xpath_all + '/sourceTerms/turbulentKineticEnergy'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_k']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname_all}_k']['injectionRateSuSp']['k']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.czname_all}_k']['selectionMode'])

    def testSourceTermsEpsilon_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath_all = self.xpath_all + '/sourceTerms/turbulentDissipationRate'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_epsilon']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname_all}_epsilon']['injectionRateSuSp']['epsilon']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.czname_all}_epsilon']['selectionMode'])

    def testSourceTermsOmega_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpath_all = self.xpath_all + '/sourceTerms/specificDissipationRate'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('absolute', content[f'scalarSource_{self.czname_all}_omega']['volumeMode'])
        self.assertEqual('0', content[f'scalarSource_{self.czname_all}_omega']['injectionRateSuSp']['omega']['Su'])
        self.assertEqual('all', content[f'scalarSource_{self.czname_all}_omega']['selectionMode'])

    # --------------------------------------------------------------------------
    def testFixedValuesVelocity_all(self):
        xpath_all = self.xpath_all + '/fixedValues/velocity'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual([0, 0, 0], content[f'fixedVelocity_All']['Ubar'])
        self.assertEqual('0', content[f'fixedVelocity_All']['relaxation'])
        self.assertEqual('all', content[f'fixedVelocity_All']['selectionMode'])

    def testFixedValuesTemperature_all(self):
        xpath_all = self.xpath_all + '/fixedValues/temperature'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('300', content[f'fixedTemperature_All']['temperature'][1])
        self.assertEqual('all', content[f'fixedTemperature_All']['selectionMode'])

    def testFixedValuesNutilda_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'spalartAllmaras')
        xpath_all = self.xpath_all + '/fixedValues/modifiedTurbulentViscosity'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname_all}_nuTilda']['fieldValues']['nuTilda'])
        self.assertEqual('all', content[f'fixedValue_{self.czname_all}_nuTilda']['selectionMode'])

    def testFixedValuesK_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath_all = self.xpath_all + '/fixedValues/turbulentKineticEnergy'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname_all}_k']['fieldValues']['k'])
        self.assertEqual('all', content[f'fixedValue_{self.czname_all}_k']['selectionMode'])

    def testFixedValuesEpsilon_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-epsilon')
        xpath_all = self.xpath_all + '/fixedValues/turbulentDissipationRate'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname_all}_epsilon']['fieldValues']['epsilon'])
        self.assertEqual('all', content[f'fixedValue_{self.czname_all}_epsilon']['selectionMode'])

    def testFixedValuesOmega_all(self):
        self._db.setValue('.//models/turbulenceModels/model', 'k-omega')
        xpath_all = self.xpath_all + '/fixedValues/specificDissipationRate'
        self._db.setAttribute(xpath_all, 'disabled', 'false')

        content = FvOptions(self.rname).build().asDict()

        self.assertEqual('0', content[f'fixedValue_{self.czname_all}_omega']['fieldValues']['omega'])
        self.assertEqual('all', content[f'fixedValue_{self.czname_all}_omega']['selectionMode'])


if __name__ == '__main__':
    unittest.main()
