import unittest

from coredb import coredb


class TestBoundaryCondition(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def testBoundaryCondition(self):
        name = 'testBoundaryCondition_1'
        physicalType = 'patch'
        self.db.addBoundaryCondition(name, physicalType)
        bcs = self.db.getBoundaryConditions()
        self.assertIn(name, bcs)
        self.assertEqual(1, len(bcs))


if __name__ == '__main__':
    unittest.main()
