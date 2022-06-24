import unittest

from coredb import coredb
from openfoam.fv_schemes import FvSchemes


class TestFvSchemes(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

        self.region = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(self.region)
        self.db.addCellZone(self.region, zone)

        self.db.setValue('.//models/energyModels', 'on')
        self.db.setValue('.//models/multiphaseModels/model', 'off')
        self.db.setValue('.//models/speciesModels', 'off')

        self.db.setValue('.//turbulenceModels/model', 'k-epsilon')
        self.db.setValue('.//turbulenceModels/k-epsilon/model', 'realizable')

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testSecondOrderTransient(self):
        solver = 'PCNFoam'

        self.db.setValue('.//general/timeTransient', 'true')

        self.db.setValue('.//discretizationSchemes/time', 'secondOrderImplicit')
        self.db.setValue('.//discretizationSchemes/momentum', 'secondOrderUpwind')
        self.db.setValue('.//discretizationSchemes/energy', 'secondOrderUpwind')
        self.db.setValue('.//discretizationSchemes/turbulentKineticEnergy', 'secondOrderUpwind')

        content = FvSchemes(self.region, solver).asDict()

        self.assertEqual('backward', content['ddtSchemes']['default'])

        self.assertEqual('Gauss linear', content['gradSchemes']['default'])
        self.assertEqual('cellLimited Gauss linear 1.0', content['gradSchemes']['turbulenceReconGrad'])

        self.assertEqual('Gauss MinmodV', content['divSchemes']['div(phiNeg,U)'])
        self.assertEqual('Gauss Minmod', content['divSchemes']['div(phiNeg,h)'])
        self.assertEqual('Gauss linearUpwind turbulenceReconGrad', content['divSchemes']['div(phi,epsilon)'])

    def testFirstOrderSteady(self):
        solver = 'PCNFoam'

        self.db.setValue('.//general/timeTransient', 'false')

        self.db.setValue('.//discretizationSchemes/time', 'firstOrderImplicit')
        self.db.setValue('.//discretizationSchemes/momentum', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/energy', 'firstOrderUpwind')
        self.db.setValue('.//discretizationSchemes/turbulentKineticEnergy', 'firstOrderUpwind')

        content = FvSchemes(self.region, solver).asDict()

        self.assertEqual('NEXT::localEuler', content['ddtSchemes']['default'])

        self.assertEqual('Gauss linear', content['gradSchemes']['default'])
        self.assertEqual('cellLimited Gauss linear 1.0', content['gradSchemes']['turbulenceReconGrad'])

        self.assertEqual('Gauss upwind', content['divSchemes']['div(phiNeg,U)'])
        self.assertEqual('Gauss upwind', content['divSchemes']['div(phiNeg,h)'])
        self.assertEqual('bounded Gauss upwind', content['divSchemes']['div(phi,epsilon)'])


if __name__ == '__main__':
    unittest.main()
