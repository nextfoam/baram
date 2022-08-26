import unittest
import pprint

from coredb import coredb


class TestMaterial(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.pp = pprint.PrettyPrinter(indent=4)

    def tearDown(self) -> None:
        coredb.destroy()

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

    def testMaterialIdReuse(self):
        self.db.addMaterial('nitrogen')
        self.db.addMaterial('oxygen')

        materials = self.db.getMaterials()
        mid = 0
        for m in materials:
            if m[1] == 'nitrogen':
                mid = m[0]
                break

        self.db.removeMaterial('nitrogen')
        self.db.addMaterial('hydrogen')

        materials = self.db.getMaterials()
        for m in materials:
            if m[1] == 'hydrogen':
                self.assertEqual(mid, m[0])
                break
        else:
            self.assertTrue(False)

    def testMaterialGetBulk(self):
        expected = {
            'material': [
                {
                    '@mid': '1',
                    'absorptionCoefficient': '0.0',
                    'density': {
                        'constant': '1.225',
                        'specification': 'constant'
                    },
                    'molecularWeight': '28.966',
                    'name': 'air',
                    'phase': 'gas',
                    'specificHeat': {
                        'constant': '1006.0',
                        'polynomial': '',
                        'specification': 'constant'
                    },
                    'thermalConductivity': {
                        'constant': '0.0245',
                        'polynomial': '',
                        'specification': 'constant'
                    },
                    'viscosity': {
                        'constant': '1.79e-05',
                        'polynomial': '',
                        'specification': 'constant',
                        'sutherland': {
                            'coefficient': '1.46e-06',
                            'temperature': '110.4'
                        }
                    }
                },
                {
                    '@mid': '2',
                    'absorptionCoefficient': '0.0',
                    'chemicalFormula': 'H2',
                    'density': {
                        'constant': '0.085',
                        'specification': 'constant'
                    },
                    'molecularWeight': '2.01588',
                    'name': 'hydrogen',
                    'phase': 'gas',
                    'specificHeat': {
                        'constant': '14268.0',
                        'polynomial': '',
                        'specification': 'constant'
                    },
                    'thermalConductivity': {
                        'constant': '0.181',
                        'polynomial': '',
                        'specification': 'constant'
                    },
                    'viscosity': {
                        'constant': '8.69e-06',
                        'polynomial': '',
                        'specification': 'constant',
                        'sutherland': {
                            'coefficient': '6.9e-06',
                            'temperature': '97.0'
                        }
                    }
                }
            ]
        }

        self.db.addMaterial('hydrogen')
        data = self.db.getBulk('.//materials')
        # self.pp.pprint(data)
        self.assertDictEqual(expected, data)

    def testMaterialSetBulk(self):
        testName = 'myair'
        data = self.db.getBulk('.//materials/material[name="air"]')
        mid = data['@mid']
        data['name'] = testName
        with self.db:
            self.db.setBulk(f'.//materials/material[@mid="{mid}"]', data)
        name = self.db.getValue(f'.//materials/material[@mid="{mid}"]/name')

        # data = self.db.getBulk(f'.//materials/material[@mid="{mid}"]')
        # self.pp.pprint(data)

        self.assertEqual(testName, name)


if __name__ == '__main__':
    unittest.main()
