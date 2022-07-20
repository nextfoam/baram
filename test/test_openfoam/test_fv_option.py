import unittest

from coredb import coredb
from openfoam.system.fv_options import FvOptions


class TestFvSchemes(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

        self.region = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(self.region)
        self.db.addCellZone(self.region, zone)

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testJust(self):
        FvOptions(self.region).build()


if __name__ == '__main__':
    unittest.main()
