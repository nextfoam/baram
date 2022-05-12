import unittest

from coredb import coredb


class TestMaterial(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

    def testGetMaterialsEmpty(self):
        materials = self.db.getMaterials()
        self.assertEqual(len(materials), 0)

    def testAddValidMaterial(self):
        self.db.addMaterial('air')
        self.db.addMaterial('oxygen')
        self.db.addMaterial('aluminum')
        materials = self.db.getMaterials()
        self.assertEqual(len(materials), 3)
        self.assertIn(('air', None, 'gas'), materials)
        self.assertIn(('oxygen', 'O2', 'gas'), materials)
        self.assertIn(('aluminum', 'Al', 'solid'), materials)

    def testAddInvalidMaterial(self):
        with self.assertRaises(LookupError) as context:
            self.db.addMaterial('airNone')

    def testAddDuplicateMaterial(self):
        self.db.addMaterial('air')
        with self.assertRaises(FileExistsError) as context:
            self.db.addMaterial('air')

    def testRemoveMaterial(self):
        self.db.addMaterial('air')
        self.db.addMaterial('oxygen')
        self.db.removeMaterial('air')
        materials = self.db.getMaterials()
        self.assertEqual(len(materials), 1)
        self.db.removeMaterial('oxygen')
        materials = self.db.getMaterials()
        self.assertEqual(len(materials), 0)


if __name__ == '__main__':
    unittest.main()
