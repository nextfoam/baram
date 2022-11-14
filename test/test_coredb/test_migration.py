#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path

from lxml import etree

from coredb import migrate
from coredb import coredb


class TestMigration(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.dataFolder = Path(__file__).parent / 'coredb_xml'

    def tearDown(self) -> None:
        coredb.destroy()

    def testV1(self):
        tree = etree.parse(self.dataFolder/'v1.xml')
        migrate.migrate(tree.getroot())

        self.db._xmlSchema.assertValid(tree)

    def testV1a(self):
        tree = etree.parse(self.dataFolder/'v1a.xml')
        migrate.migrate(tree.getroot())

        self.db._xmlSchema.assertValid(tree)


if __name__ == '__main__':
    unittest.main()
