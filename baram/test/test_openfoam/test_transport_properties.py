#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from baram.coredb import coredb

from baram.openfoam.constant.transport_properties import TransportProperties


class TestTransportProperties(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

        self.region1 = 'testRegion_1'
        self.db.addRegion(self.region1)

    def tearDown(self) -> None:
        coredb.destroy()

    def testTransportModel(self):
        content = TransportProperties(self.region1).build().asDict()
        self.assertEqual('Newtonian', content['transportModel'])

    def testNu(self):
        content = TransportProperties(self.region1).build().asDict()
        self.assertEqual('[ 0 2 -1 0 0 0 0 ] 1.4612244897959185e-05', content['nu'])

if __name__ == '__main__':
    unittest.main()
