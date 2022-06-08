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


if __name__ == '__main__':
    unittest.main()
