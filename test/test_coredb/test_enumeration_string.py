import unittest

from coredb import coredb


class TestEnumerationString(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.path = './/runConditions/timeSteppingMethod'

    def testValidItems(self):
        validItems = ['fixed', 'adaptive']
        for item in validItems:
            self.db.setValue(self.path, item)
            read = self.db.getValue(self.path)
            self.assertEqual(item, read)

    def testInvalidItem(self):
        written = 'wrongValue'
        with self.assertRaises(ValueError):
            self.db.setValue(self.path, written)

    def tearDown(self) -> None:
        coredb.destroy()


if __name__ == '__main__':
    unittest.main()
