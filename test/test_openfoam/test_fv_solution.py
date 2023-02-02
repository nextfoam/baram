import unittest

from coredb import coredb
from openfoam.system.fv_solution import FvSolution
from coredb.general_db import GeneralDB
from coredb.region_db import RegionDB
from coredb.material_db import MaterialDB
from coredb.numerical_db import NumericalDB
from coredb.reference_values_db import ReferenceValuesDB

rname = "testRegion_1"


class TestFvSolution(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._db.addRegion(rname)
        self._air = self._db.getAttribute(f'{MaterialDB.MATERIALS_XPATH}/material[name="air"]', 'mid')
        self._steel = str(self._db.addMaterial('steel'))

    def tearDown(self) -> None:
        coredb.destroy()

    def testCompressible(self):
        self._db.setValue(GeneralDB.GENERAL_XPATH + '/flowType', "compressible")
        content = FvSolution(rname).build().asDict()
        self.assertEqual('PBiCGStab', content['solvers']['"(p|pcorr)"']['solver'])

    def testIncompressible(self):
        self._db.setValue(GeneralDB.GENERAL_XPATH + '/flowType', "incompressible")
        content = FvSolution(rname).build().asDict()
        self.assertEqual('PCG', content['solvers']['"(p|pcorr)"']['solver'])

    def testSolid(self):
        self._db.setValue(RegionDB.getXPath(rname) + '/material', self._steel)
        content = FvSolution(rname).build().asDict()
        self.assertEqual('DIC', content['solvers']['h']['preconditioner']['smoother'])

    def testFluid(self):
        self._db.setValue(RegionDB.getXPath(rname) + '/material', self._air)
        content = FvSolution(rname).build().asDict()
        self.assertEqual('DILU', content['solvers']['h']['preconditioner']['smoother'])

    def testSimpleSolid(self):
        self._db.setValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme', 'SIMPLE')
        self._db.setValue(RegionDB.getXPath(rname) + '/material', self._steel)
        content = FvSolution(rname).build().asDict()
        self.assertEqual('no', content['SIMPLE']['consistent'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p_rgh'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                         content['SIMPLE']['residualControl']['U'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/energy/absolute'),
                         content['SIMPLE']['residualControl']['h'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                         content['SIMPLE']['residualControl']['"(k|epsilon|omega|nuTilda)"'])
        self.assertEqual('no', content['PIMPLE']['consistent'])

    def testSimpleFluid(self):
        self._db.setValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme', 'SIMPLE')
        self._db.setValue(RegionDB.getXPath(rname) + '/material', self._air)
        content = FvSolution(rname).build().asDict()
        self.assertEqual('no', content['SIMPLE']['consistent'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p_rgh'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                         content['SIMPLE']['residualControl']['U'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/energy/absolute'),
                         content['SIMPLE']['residualControl']['h'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                         content['SIMPLE']['residualControl']['"(k|epsilon|omega|nuTilda)"'])
        self.assertEqual('no', content['PIMPLE']['consistent'])
        self.assertEqual(self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfCorrectors'),
                         content['PIMPLE']['nCorrectors'])

    def testSimplecSolid(self):
        self._db.setValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme', 'SIMPLEC')
        self._db.setValue(RegionDB.getXPath(rname) + '/material', self._steel)
        content = FvSolution(rname).build().asDict()
        self.assertEqual('no', content['SIMPLE']['consistent'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p_rgh'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                         content['SIMPLE']['residualControl']['U'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/energy/absolute'),
                         content['SIMPLE']['residualControl']['h'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                         content['SIMPLE']['residualControl']['"(k|epsilon|omega|nuTilda)"'])
        self.assertEqual('no', content['PIMPLE']['consistent'])

    def testSimplecFluid(self):
        self._db.setValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/pressureVelocityCouplingScheme', 'SIMPLEC')
        self._db.setValue(RegionDB.getXPath(rname) + '/material', self._air)
        content = FvSolution(rname).build().asDict()
        self.assertEqual(self._db.getVector(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/referencePressureLocation'),
                         content['SIMPLE']['pRefPoint'])
        self.assertEqual(self._db.getValue(ReferenceValuesDB.REFERENCE_VALUES_XPATH + '/pressure'),
                         content['SIMPLE']['pRefValue'])
        self.assertEqual('yes', content['SIMPLE']['consistent'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['SIMPLE']['residualControl']['p_rgh'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                         content['SIMPLE']['residualControl']['U'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/energy/absolute'),
                         content['SIMPLE']['residualControl']['h'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                         content['SIMPLE']['residualControl']['"(k|epsilon|omega|nuTilda)"'])
        self.assertEqual('yes', content['PIMPLE']['consistent'])
        self.assertEqual(self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/numberOfCorrectors'),
                         content['PIMPLE']['nCorrectors'])

    def testUseMomentumPredictor(self):
        self._db.setValue(GeneralDB.GENERAL_XPATH + '/timeTransient', 'true')
        self._db.setValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/useMomentumPredictor', 'true')
        content = FvSolution(rname).build().asDict()
        self.assertEqual('on', content['PIMPLE']['momentumPredictor'])
        self.assertEqual(self._db.getValue('.//runConditions/maxCourantNumber'), content['PIMPLE']['maxCo'])

    def testNotUseMomentumPredictor(self):
        self._db.setValue(GeneralDB.GENERAL_XPATH + '/timeTransient', 'true')
        self._db.setValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/useMomentumPredictor', 'false')
        content = FvSolution(rname).build().asDict()
        self.assertEqual('off', content['PIMPLE']['momentumPredictor'])
        self.assertEqual(self._db.getValue('.//runConditions/maxCourantNumber'), content['PIMPLE']['maxCo'])

    def testRegion(self):
        content = FvSolution(rname).build().asDict()
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['PIMPLE']['residualControl']['p']['tolerance'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/relative'),
                         content['PIMPLE']['residualControl']['p']['relTol'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/absolute'),
                         content['PIMPLE']['residualControl']['p_rgh']['tolerance'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/pressure/relative'),
                         content['PIMPLE']['residualControl']['p_rgh']['relTol'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/momentum/absolute'),
                         content['PIMPLE']['residualControl']['U']['tolerance'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/momentum/relative'),
                         content['PIMPLE']['residualControl']['U']['relTol'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/energy/absolute'),
                         content['PIMPLE']['residualControl']['h']['tolerance'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/energy/relative'),
                         content['PIMPLE']['residualControl']['h']['relTol'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/turbulence/absolute'),
                         content['PIMPLE']['residualControl']['"(k|epsilon|omega|nuTilda)"']['tolerance'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/turbulence/relative'),
                         content['PIMPLE']['residualControl']['"(k|epsilon|omega|nuTilda)"']['relTol'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/pressure'),
                         content['relaxationFactors']['fields']['p'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/pressureFinal'),
                         content['relaxationFactors']['fields']['pFinal'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/pressure'),
                         content['relaxationFactors']['fields']['p_rgh'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/pressureFinal'),
                         content['relaxationFactors']['fields']['p_rghFinal'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/density'),
                         content['relaxationFactors']['fields']['rho'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/densityFinal'),
                         content['relaxationFactors']['fields']['rhoFinal'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/momentum'),
                         content['relaxationFactors']['equations']['U'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/momentumFinal'),
                         content['relaxationFactors']['equations']['UFinal'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/energy'),
                         content['relaxationFactors']['equations']['h'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/energyFinal'),
                         content['relaxationFactors']['equations']['hFinal'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/turbulence'),
                         content['relaxationFactors']['equations']['"(k|epsilon|omega|nuTilda)"'])
        self.assertEqual(self._db.getValue('.//underRelaxationFactors/turbulenceFinal'),
                         content['relaxationFactors']['equations']['"(k|epsilon|omega|nuTilda)Final"'])

    def testNoRegion(self):
        content = FvSolution().build().asDict()
        self.assertEqual(self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/maxIterationsPerTimeStep'),
                         content['PIMPLE']['nOuterCorrectors'])

    def testMultiphase(self):
        material = 'oxygen'
        mid = self._db.addMaterial(material)
        self._db.setValue(RegionDB.getXPath(rname) + '/secondaryMaterials', str(mid))
        content = FvSolution(rname).build().asDict()
        self.assertEqual(self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/numberOfCorrectors'),
                         content['solvers']['"alpha.*"']['nAlphaCorr'])
        self.assertEqual(
            self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/maxIterationsPerTimeStep'),
            content['solvers']['"alpha.*"']['nAlphaSubCycles'])
        self.assertEqual(
            self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/phaseInterfaceCompressionFactor'),
            content['solvers']['"alpha.*"']['cAlpha'])
        self.assertEqual(
            'yes'
            if self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/useSemiImplicitMules') == 'true'
            else 'no',
            content['solvers']['"alpha.*"']['MULESCorr'])
        self.assertEqual(self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/multiphase/useSemiImplicitMules'),
                         content['solvers']['"alpha.*"']['nLimiterIter'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/volumeFraction/absolute'),
                         content['SIMPLE']['residualControl']['"alpha.*"'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/volumeFraction/absolute'),
                         content['PIMPLE']['residualControl']['"alpha.*"']['tolerance'])
        self.assertEqual(self._db.getValue('.//convergenceCriteria/volumeFraction/relative'),
                         content['PIMPLE']['residualControl']['"alpha.*"']['relTol'])
        self.assertEqual(
            self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/underRelaxationFactors/volumeFraction'),
            content['relaxationFactors']['equations'][f'alpha.{material}'])
        self.assertEqual(
            self._db.getValue(NumericalDB.NUMERICAL_CONDITIONS_XPATH + '/underRelaxationFactors/volumeFraction'),
            content['relaxationFactors']['equations'][f'alpha.{material}'])


if __name__ == '__main__':
    unittest.main()
