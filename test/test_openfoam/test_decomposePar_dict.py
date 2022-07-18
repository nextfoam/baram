#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from coredb import coredb

from openfoam.system.decomposePar_dict import DecomposeParDict

class TestDecomposeParDict(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()

        self.region1 = 'testRegion_1'
        self.db.addRegion(self.region1)

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

    def testNumberOfSubdomains(self):
        self._db.setValue('.//runCalculation/parallel/numberOfCores', '4')
        content = DecomposeParDict(self.region1).build().asDict()
        self.assertEqual('4', content['numberOfSubdomains'])

    def testNumberOfSubdomains(self):
        content = DecomposeParDict(self.region1).build().asDict()
        self.assertEqual('scotch', content['method'])


if __name__ == '__main__':
    unittest.main()
