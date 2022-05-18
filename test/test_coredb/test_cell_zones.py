import unittest

from coredb import coredb


class TestCellZones(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def testAddRegion(self):
        rname = 'testRegion_1'
        self.db.addRegion(rname)
        regions = self.db.getRegions()
        self.assertIn(rname, regions)
        self.assertEqual(1, len(regions))

    def testDefaultCellZone(self):
        rname = 'testRegion_1'
        self.db.addRegion(rname)
        path = f'.//cellZones/region[name="{rname}"]/cellZone[name="All"]/zoneType'
        self.assertEqual('none', self.db.getValue(path))

    def testAddCellZone(self):
        rname = 'testRegion_1'
        zname = 'testZone_1'
        self.db.addRegion(rname)
        czid = self.db.addCellZone(rname, zname)
        zones = self.db.getCellZones(rname)
        self.assertIn((czid, zname), zones)

    def testAddCellZoneId(self):
        rname = 'testRegion_1'
        zname = 'testZone_1'
        self.db.addRegion(rname)
        czid = self.db.addCellZone(rname, zname)
        self.assertEqual(2, czid)  # next to 'All' zone

    def testDefaultCellZoneType(self):
        rname = 'testRegion_1'
        zname = 'testZone_1'
        self.db.addRegion(rname)
        self.db.addCellZone(rname, zname)
        path = f'.//cellZones/region[name="{rname}"]/cellZone[name="{zname}"]/zoneType'
        self.assertEqual('none', self.db.getValue(path))

    def tearDown(self) -> None:
        del coredb.CoreDB._instance


if __name__ == '__main__':
    unittest.main()
