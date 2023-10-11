import unittest

from baramFlow.coredb import coredb


class TestCellZones(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

    def tearDown(self) -> None:
        coredb.destroy()

    def testAddRegion(self):
        rname = 'testRegion_1'
        self.db.addRegion(rname)
        regions = self.db.getRegions()
        self.assertIn(rname, regions)
        self.assertEqual(1, len(regions))

    def testDefaultCellZone(self):
        rname = 'testRegion_1'
        self.db.addRegion(rname)
        path = f'.//region[name="{rname}"]/cellZones/cellZone[name="All"]/zoneType'
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

    def testCellZoneIdUniqueness(self):
        """Cell Zone index should be unique regardless of region
        """
        rname1 = 'testRegion_1'
        rname2 = 'testRegion_2'
        zname1 = 'testZone_1'
        zname2 = 'testZone_2'
        self.db.addRegion(rname1)
        self.db.addRegion(rname2)
        id1 = self.db.addCellZone(rname1, zname1)
        id2 = self.db.addCellZone(rname2, zname2)
        self.assertEqual(id1+1, id2)

    def testDefaultCellZoneType(self):
        rname = 'testRegion_1'
        zname = 'testZone_1'
        self.db.addRegion(rname)
        self.db.addCellZone(rname, zname)
        path = f'.//region[name="{rname}"]/cellZones/cellZone[name="{zname}"]/zoneType'
        self.assertEqual('none', self.db.getValue(path))

    def testFixedValue(self):
        rname = 'testRegion_1'
        zname = 'testZone_1'
        self.db.addRegion(rname)
        self.db.addCellZone(rname, zname)

        path = f'.//region[name="{rname}"]/cellZones/cellZone[name="{zname}"]/fixedValues/velocity/velocity/x'
        expected = '3'
        self.db.setValue(path, expected)
        value = self.db.getValue(path)
        self.assertEqual(expected, value)


if __name__ == '__main__':
    unittest.main()
