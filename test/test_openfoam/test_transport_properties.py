import unittest

from coredb import coredb
from openfoam.constant.transport_properties import TransportProperties


class TestTransportProperties(unittest.TestCase):
    def setUp(self):
        self.db = coredb.CoreDB()
        self.path = './/transport'  # not defined

        self.region = 'testRegion_1'
        self.db.addRegion(self.region)

    def tearDown(self) -> None:
        del coredb.CoreDB._instance

if __name__ == '__main__':
    unittest.main()
