import unittest

from coredb import coredb


class TestConfigCount(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.gravityPath = './/operatingConditions/gravity'

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testSetAttributeChange(self):
        attr = 'disabled'
        self.db.setAttribute(self.gravityPath, attr, 'true')
        expected = self.db.configCount + 1
        self.db.setAttribute(self.gravityPath, attr, 'false')
        self.assertEqual(expected, self.db.configCount)

    def testSetAttributeNoChange(self):
        attr = 'disabled'
        self.db.setAttribute(self.gravityPath, attr, 'true')
        expected = self.db.configCount
        self.db.setAttribute(self.gravityPath, attr, 'true')
        self.assertEqual(expected, self.db.configCount)

    def testSetValueInputTypeNumberChange(self):
        self.db.setValue(self.gravityPath + '/direction/x', '9.8')
        expected = self.db.configCount + 1
        self.db.setValue(self.gravityPath + '/direction/x', '9.9')
        self.assertEqual(expected, self.db.configCount)

    def testSetValueInputTypeNumberNoChange(self):
        self.db.setValue(self.gravityPath + '/direction/x', '9.8')
        expected = self.db.configCount
        self.db.setValue(self.gravityPath + '/direction/x', '9.8')
        self.assertEqual(expected, self.db.configCount)

    def testSetValueInputNumberListTypeChange(self):
        self.db.setValue('.//materials/material[name="air"]/specificHeat/polynomial', '1.1 2.2 3.3')
        expected = self.db.configCount + 1
        self.db.setValue('.//materials/material[name="air"]/specificHeat/polynomial', '1.1 4.5 3.3')
        self.assertEqual(expected, self.db.configCount)

    def testSetValueInputNumberListTypeNoChange(self):
        self.db.setValue('.//materials/material[name="air"]/specificHeat/polynomial', '1.1 2.2 3.3')
        expected = self.db.configCount
        self.db.setValue('.//materials/material[name="air"]/specificHeat/polynomial', '1.1 2.2 3.3')
        self.assertEqual(expected, self.db.configCount)


if __name__ == '__main__':
    unittest.main()
