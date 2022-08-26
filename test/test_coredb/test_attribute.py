import unittest

from coredb import coredb


class TestAttribute(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.path = './/operatingConditions/gravity'

    def tearDown(self) -> None:
        coredb.destroy()

    def testGetAttribute(self):
        attr = 'disabled'
        value = self.db.getAttribute(self.path, attr)

        # 'true' is default value
        self.assertEqual('true', value)

    def testSetAttribute(self):
        attr = 'disabled'

        expected = 'false'
        self.db.setAttribute(self.path, attr, expected)
        value = self.db.getAttribute(self.path, attr)
        self.assertEqual(expected, value)

        expected = 'true'
        self.db.setAttribute(self.path, attr, expected)
        value = self.db.getAttribute(self.path, attr)
        self.assertEqual(expected, value)


if __name__ == '__main__':
    unittest.main()
