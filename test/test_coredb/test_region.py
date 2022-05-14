import unittest

from coredb import coredb


class TestMaterial(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def testAddRegion(self):
        name = 'testRegion_1'
        self.db.addRegion(name)
        regions = self.db.getRegions()
        self.assertIn(name, regions)
        self.assertEqual(1, len(regions))

    def testDefaultCellZone(self):
        name = 'testRegion_1'
        self.db.addRegion(name)
        path = f'.//cellZones/region[name="{name}"]/cellZone[name="All"]/zoneType'
        self.assertEqual('none', self.db.getValue(path))


if __name__ == '__main__':
    unittest.main()
