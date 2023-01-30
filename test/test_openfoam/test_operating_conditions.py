import unittest

from coredb import coredb
from openfoam.constant.operating_conditions import OperatingConditions


class TestOperatingConditions(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

    def tearDown(self) -> None:
        coredb.destroy()

    def testBuild(self):
        rname = 'testRegion_1'
        zone = 'testZone_1'
        pressure = '0'
        self.db.addRegion(rname)
        self.db.addCellZone(rname, zone)
        self.db.setValue('.//operatingConditions/pressure', pressure)

        content = OperatingConditions(rname).build().asDict()
        self.assertEqual(('Op [1 -1 -2 0 0 0 0]', pressure), content['Op'])


if __name__ == '__main__':
    unittest.main()
