import unittest

from coredb import coredb
from coredb.models_db import ModelsDB
from openfoam.constant.turbulence_properties import TurbulenceProperties


class TestTurbulenceProperties(unittest.TestCase):
    def setUp(self):
        self._db = coredb.createDB()
        self._path = './/turbulenceModels'

        self._region = 'testRegion_1'
        zone = 'testZone_1'
        self._db.addRegion(self._region)
        self._db.addCellZone(self._region, zone)
        self._db.setValue('.//general/flowType', 'compressible')

    def tearDown(self) -> None:
        coredb.destroy()

    def testInviscid(self):
        self._db.setValue(self._path + '/model', 'inviscid')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('laminar', content['simulationType'])

    def testLaminar(self):
        self._db.setValue(self._path + '/model', 'laminar')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('laminar', content['simulationType'])

    def testSpalartAllmaras(self):
        self._db.setValue(self._path + '/model', 'spalartAllmaras')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('SpalartAllmaras', content['RAS']['RASModel'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber'),
                         content['RAS']['Prt'])

    def testKEpsilonStandard(self):
        self._db.setValue(self._path + '/model', 'k-epsilon')
        self._db.setValue(self._path + '/k-epsilon/model', 'standard')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('kEpsilon', content['RAS']['RASModel'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber'),
                         content['RAS']['Prt'])

    def testKEpsilonRNG(self):
        self._db.setValue(self._path + '/model', 'k-epsilon')
        self._db.setValue(self._path + '/k-epsilon/model', 'rng')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('RNGkEpsilon', content['RAS']['RASModel'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber'),
                         content['RAS']['Prt'])

    def testKEpsilonRealizable(self):
        self._db.setValue(self._path + '/model', 'k-epsilon')
        self._db.setValue(self._path + '/k-epsilon/model', 'realizable')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('realizableKE', content['RAS']['RASModel'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber'),
                         content['RAS']['Prt'])

    def testKOmegaSST(self):
        self._db.setValue(self._path + '/model', 'k-omega')
        content = TurbulenceProperties(self._region).build().asDict()
        self.assertEqual('RAS', content['simulationType'])
        self.assertEqual('kOmegaSST', content['RAS']['RASModel'])
        self.assertEqual(self._db.getValue(ModelsDB.TURBULENCE_MODELS_XPATH + '/energyPrandtlNumber'),
                         content['RAS']['Prt'])


if __name__ == '__main__':
    unittest.main()
