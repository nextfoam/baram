import unittest

from baram.coredb import coredb


class TestMonitors(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

    def testAddForceMonitor(self):
        name = self.db.addForceMonitor()
        monitors = self.db.getForceMonitors()
        self.assertIn(name, monitors)

    def testRemoveForceMonitor(self):
        name = self.db.addForceMonitor()
        self.db.removeForceMonitor(name)
        monitors = self.db.getForceMonitors()
        self.assertNotIn(name, monitors)

    def testAddPointMonitor(self):
        name = self.db.addPointMonitor()
        monitors = self.db.getPointMonitors()
        self.assertIn(name, monitors)

    def testRemovePointMonitor(self):
        name = self.db.addPointMonitor()
        self.db.removePointMonitor(name)
        monitors = self.db.getPointMonitors()
        self.assertNotIn(name, monitors)

    def testAddSurfaceMonitor(self):
        name = self.db.addSurfaceMonitor()
        monitors = self.db.getSurfaceMonitors()
        self.assertIn(name, monitors)

    def testRemoveSurfaceMonitor(self):
        name = self.db.addSurfaceMonitor()
        self.db.removeSurfaceMonitor(name)
        monitors = self.db.getSurfaceMonitors()
        self.assertNotIn(name, monitors)

    def testAddVolumeMonitor(self):
        name = self.db.addVolumeMonitor()
        monitors = self.db.getVolumeMonitors()
        self.assertIn(name, monitors)

    def testRemoveVolumeMonitor(self):
        name = self.db.addVolumeMonitor()
        self.db.removeVolumeMonitor(name)
        monitors = self.db.getVolumeMonitors()
        self.assertNotIn(name, monitors)

    def tearDown(self) -> None:
        coredb.destroy()


if __name__ == '__main__':
    unittest.main()
