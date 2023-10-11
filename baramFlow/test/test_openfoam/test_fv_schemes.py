import unittest

from baramFlow.coredb import coredb
from baramFlow.openfoam.system.fv_schemes import FvSchemes


class TestFvSchemes(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

        self.rname = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(self.rname)
        self.db.addCellZone(self.rname, zone)

        self.db.setValue('.//general/solverType', 'pressureBased')

        self.db.setValue('.//models/energyModels', 'on')
        self.db.setValue('.//models/multiphaseModels/model', 'off')
        self.db.setValue('.//models/speciesModels', 'off')

        self.db.setValue('.//turbulenceModels/model', 'k-epsilon')
        self.db.setValue('.//turbulenceModels/k-epsilon/model', 'realizable')

    def tearDown(self) -> None:
        coredb.destroy()

    def testSecondOrderTransient(self):  # PCNFoam
        self.db.setValue('.//general/timeTransient', 'true')

        self.db.setValue('.//general/flowType', 'compressible')

        self.db.setValue('.//discretizationSchemes/time', 'secondOrderImplicit')
        self.db.setValue('.//discretizationSchemes/momentum', 'secondOrderUpwind')
        self.db.setValue('.//discretizationSchemes/energy', 'secondOrderUpwind')
        self.db.setValue('.//discretizationSchemes/turbulentKineticEnergy', 'secondOrderUpwind')

        content = FvSchemes(self.rname).build().asDict()

        self.assertEqual('backward', content['ddtSchemes']['default'])

        self.assertEqual('Gauss linear', content['gradSchemes']['default'])
        self.assertEqual('BJLimited Gauss linear 1.0', content['gradSchemes']['turbulenceReconGrad'])

        self.assertEqual('Gauss MinmodV', content['divSchemes']['div(phiNeg,U)'])
        self.assertEqual('Gauss Minmod', content['divSchemes']['div(phiNeg,h)'])
        self.assertEqual('Gauss linearUpwind turbulenceReconGrad', content['divSchemes']['div(phi,epsilon)'])

    def testFirstOrderSteady(self):  # PCNFoam
        self.db.setValue('.//general/timeTransient', 'false')

        self.db.setValue('.//general/flowType', 'compressible')

        self.db.setValue('.//discretizationSchemes/time', 'firstOrderImplicit')
        self.db.setValue('.//discretizationSchemes/momentum', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/energy', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/turbulentKineticEnergy', 'firstOrderUpwind')

        content = FvSchemes(self.rname).build().asDict()

        self.assertEqual('localEuler', content['ddtSchemes']['default'])

        self.assertEqual('Gauss linear', content['gradSchemes']['default'])
        self.assertEqual('BJLimited Gauss linear 1.0', content['gradSchemes']['turbulenceReconGrad'])

        self.assertEqual('Gauss upwind', content['divSchemes']['div(phiNeg,U)'])
        self.assertEqual('Gauss upwind', content['divSchemes']['div(phiNeg,h)'])
        self.assertEqual('Gauss upwind', content['divSchemes']['div(phi,epsilon)'])

    def testSteadyOnlySolver(self):  # buoyantSimpleNFoam
        self.db.setValue('.//general/timeTransient', 'false')

        self.db.setValue('.//general/flowType', 'incompressible')

        self.db.setValue('.//discretizationSchemes/time', 'firstOrderImplicit')
        self.db.setValue('.//discretizationSchemes/momentum', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/energy', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/turbulentKineticEnergy', 'firstOrderUpwind')

        content = FvSchemes(self.rname).build().asDict()

        self.assertEqual('steadyState', content['ddtSchemes']['default'])

        self.assertEqual('Gauss linear', content['gradSchemes']['default'])
        self.assertEqual('BJLimited Gauss linear 1.0', content['gradSchemes']['turbulenceReconGrad'])

        self.assertEqual('bounded Gauss upwind', content['divSchemes']['div(phiNeg,U)'])
        self.assertEqual('bounded Gauss upwind', content['divSchemes']['div(phiNeg,h)'])
        self.assertEqual('bounded Gauss upwind', content['divSchemes']['div(phi,epsilon)'])

    def testTSLAero(self):  # TSLAeroFoam
        self.db.setValue('.//general/solverType', 'densityBased')
        self.db.setValue('.//general/timeTransient', 'false')
        self.db.setValue('.//general/flowType', 'compressible')

        self.db.setValue('.//discretizationSchemes/time', 'firstOrderImplicit')
        self.db.setValue('.//discretizationSchemes/momentum', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/energy', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/turbulentKineticEnergy', 'secondOrderUpwind')

        content = FvSchemes(self.rname).build().asDict()

        self.assertEqual('localEuler', content['ddtSchemes']['default'])

        self.assertEqual('Gauss linear', content['gradSchemes']['default'])
        self.assertEqual('VKMDLimited Gauss linear 0.5', content['gradSchemes']['reconGrad'])

        self.assertEqual('Gauss linearUpwind reconGrad', content['divSchemes']['div(phi,k)'])
        self.assertEqual('Gauss linearUpwind reconGrad', content['divSchemes']['div(phi,epsilon)'])
        self.assertEqual('Gauss linearUpwind reconGrad', content['divSchemes']['div(phi,omega)'])
        self.assertEqual('Gauss linearUpwind reconGrad', content['divSchemes']['div(phi,nuTilda)'])


if __name__ == '__main__':
    unittest.main()
