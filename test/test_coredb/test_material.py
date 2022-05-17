import unittest

from coredb import coredb


class TestMaterial(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def testMaterialDB(self):
        materials = self.db.getMaterialsFromDB()
        self.assertIn(('air', None, 'gas'), materials)
        self.assertIn(('nitrogen', 'N2', 'gas'), materials)
        self.assertIn(('oxygen', 'O2', 'gas'), materials)
        self.assertIn(('aluminum', 'Al', 'solid'), materials)

    def testGetMaterialsDefaultValue(self):
        materials = self.db.getMaterials()
        self.assertIn((1, 'air', None, 'gas'), materials)
        self.assertEqual(1, len(materials))

    def testAddValidMaterial(self):
        nitrogenId = self.db.addMaterial('nitrogen')
        oxygenId   = self.db.addMaterial('oxygen')
        aluminumId = self.db.addMaterial('aluminum')
        materials = self.db.getMaterials()
        self.assertEqual(4, len(materials))
        self.assertIn((nitrogenId, 'nitrogen', 'N2', 'gas'), materials)
        self.assertIn((oxygenId, 'oxygen', 'O2', 'gas'), materials)
        self.assertIn((aluminumId, 'aluminum', 'Al', 'solid'), materials)

    def testAddInvalidMaterial(self):
        with self.assertRaises(LookupError) as context:
            self.db.addMaterial('airNone')

    def testAddDuplicateMaterial(self):
        self.db.addMaterial('nitrogen')
        with self.assertRaises(FileExistsError) as context:
            self.db.addMaterial('nitrogen')

    def testRemoveMaterial(self):
        self.db.addMaterial('nitrogen')
        self.db.addMaterial('oxygen')
        self.db.removeMaterial('nitrogen')
        materials = self.db.getMaterials()
        self.assertEqual(2, len(materials))
        self.db.removeMaterial('oxygen')
        materials = self.db.getMaterials()
        self.assertEqual(1, len(materials))


if __name__ == '__main__':
    unittest.main()
