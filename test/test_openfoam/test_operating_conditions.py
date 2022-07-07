import unittest

from coredb import coredb
from openfoam.constant.operating_conditions import OperatingConditions


class TestOperatingConditions(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testBuild(self):
        region = 'testRegion_1'
        zone = 'testZone_1'
        pressure = '0'
        self.db.addRegion(region)
        self.db.addCellZone(region, zone)
        self.db.setValue('.//operatingConditions/pressure', pressure)

        content = OperatingConditions(region).build().asDict()
        self.assertEqual(('Op [1 -1 -2 0 0 0 0]', pressure), content['Op'])


if __name__ == '__main__':
    unittest.main()
