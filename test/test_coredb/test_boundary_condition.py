import unittest

from coredb import coredb


class TestBoundaryCondition(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testAddBoundaryCondition(self):
        rname = 'testRegion_1'
        self.db.addRegion(rname)
        bname = 'testBoundaryCondition_1'
        geometricalType = 'patch'
        index = self.db.addBoundaryCondition(rname, bname, geometricalType)
        bcs = self.db.getBoundaryConditions(rname)
        self.assertIn((index, bname, 'wall'), bcs)
        self.assertEqual(1, len(bcs))

    def testAddBoundaryConditionIndex(self):
        rname = 'testRegion_1'
        self.db.addRegion(rname)
        bname = 'testBoundaryCondition_1'
        physicalType = 'patch'
        self.db.addBoundaryCondition(rname, bname, physicalType)
        index = self.db.addBoundaryCondition(rname, 'second', physicalType)
        self.assertEqual(2, index)

    def testBoundaryConditionIndexUniqueness(self):
        """Boundary Condition ID should be unique regardless of region
        """
        rname1 = 'testRegion_1'
        rname2 = 'testRegion_2'
        self.db.addRegion(rname1)
        self.db.addRegion(rname2)
        bname1 = 'testBoundaryCondition_1'
        bname2 = 'testBoundaryCondition_2'
        physicalType = 'patch'
        i1 = self.db.addBoundaryCondition(rname1, bname1, physicalType)
        i2 = self.db.addBoundaryCondition(rname2, bname2, physicalType)
        self.assertEqual(i1+1, i2)


if __name__ == '__main__':
    unittest.main()
