import unittest

from baramFlow.coredb import coredb
from baramFlow.coredb.models_db import ModelsDB
from baramFlow.openfoam.constant.g import G


class TestG(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.path = ModelsDB.TURBULENCE_MODELS_XPATH

        self.rname = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(self.rname)
        self.db.addCellZone(self.rname, zone)

    def tearDown(self) -> None:
        coredb.destroy()

    def testG(self):
        self.db.setValue(self.path + '/model', 'inviscid')
        content = G().build().asDict()
        self.assertEqual('[0 1 -2 0 0 0 0]', content['dimensions'])
        self.assertEqual(self.db.getVector('.//operatingConditions/gravity/direction'), content['value'])


if __name__ == '__main__':
    unittest.main()
