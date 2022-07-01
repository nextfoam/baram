import unittest

from coredb import coredb
from openfoam.turbulence_properties import TurbulenceProperties


class TestTurbulenceProperties(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/turbulenceModels'

        self.region = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(self.region)
        self.db.addCellZone(self.region, zone)
        self.db.setValue('.//general/flowType', 'compressible')

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testInviscid(self):
        self.db.setValue(self.path + '/model', 'inviscid')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('laminar', content['simulationType'])

    def testLaminar(self):
        self.db.setValue(self.path + '/model', 'laminar')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('laminar', content['simulationType'])

    def testSpalartAllmaras(self):
        self.db.setValue(self.path + '/model', 'spalartAllmaras')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('SpalartAllmaras', content['RAS']['RASModel'])

    def testKEpsilonStandard(self):
        self.db.setValue(self.path + '/model', 'k-epsilon')
        self.db.setValue(self.path + '/k-epsilon/model', 'standard')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('kEpsilon', content['RAS']['RASModel'])

    def testKEpsilonRNG(self):
        self.db.setValue(self.path + '/model', 'k-epsilon')
        self.db.setValue(self.path + '/k-epsilon/model', 'rng')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('RNGkEpsilon', content['RAS']['RASModel'])

    def testKEpsilonRealizable(self):
        self.db.setValue(self.path + '/model', 'k-epsilon')
        self.db.setValue(self.path + '/k-epsilon/model', 'realizable')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('realizableKE', content['RAS']['RASModel'])

    def testKOmegaSST(self):
        self.db.setValue(self.path + '/model', 'k-omega')
        content = TurbulenceProperties(self.region).asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('kOmegaSST', content['RAS']['RASModel'])


if __name__ == '__main__':
    unittest.main()
