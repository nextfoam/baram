import unittest

from baramFlow.coredb import coredb
from baramFlow.coredb.material_db import MaterialDB
from base.material.material import UNIVERSAL_GAS_CONSTANT


class TestMaterialDB(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()
        self.mid = self.db.getMaterials()[0][0]
        self.xpath = MaterialDB.getXPath(self.mid)

    def tearDown(self) -> None:
        coredb.destroy()

    def testGetDensityConstant(self):
        density = 21.1
        t = 25.0
        p = 123456.7
        self.db.setValue(self.xpath + '/density/specification', 'constant')
        self.db.setValue(self.xpath + '/density/constant', str(density))

        self.assertEqual(density, MaterialDB.getDensity(self.mid, t, p))

    def testGetDensityPerfectGas(self):
        t = 25.0
        p = 123456.7
        self.db.setValue(self.xpath + '/density/specification', 'perfectGas')

        r'''
        .. math:: \rho = \frac{MW \times P}{R \times T}
        '''
        mw = float(coredb.CoreDB().getValue(self.xpath + '/molecularWeight'))
        density = p * mw / (UNIVERSAL_GAS_CONSTANT * t)
        self.assertEqual(density, MaterialDB.getDensity(self.mid, t, p))

    def testGetSpecificHeatConstant(self):
        t = 25.0
        cp = 21.1
        self.db.setValue(self.xpath + '/specificHeat/specification', 'constant')
        self.db.setValue(self.xpath + '/specificHeat/constant', str(cp))

        self.assertEqual(cp, MaterialDB.getSpecificHeat(self.mid, t))

    def testGetSpecificHeatPolynomial(self):
        t = 25.0
        cs = [1.2, 1.3, 1.5, 1.5]
        self.db.setValue(self.xpath + '/specificHeat/specification', 'polynomial')
        self.db.setValue(self.xpath + '/specificHeat/polynomial', ' '.join(str(c) for c in cs))

        cp = cs[0] + cs[1]*t + cs[2]*t**2 + cs[3]*t**3
        self.assertEqual(cp, MaterialDB.getSpecificHeat(self.mid, t))

    def testGetViscosityConstant(self):
        t = 25.0
        mu = 21.1
        self.db.setValue(self.xpath + '/viscosity/specification', 'constant')
        self.db.setValue(self.xpath + '/viscosity/constant', str(mu))

        self.assertEqual(mu, MaterialDB.getViscosity(self.mid, t))

    def testGetViscosityPolynomial(self):
        t = 25.0
        cs = [1.2, 1.3, 1.5, 1.5]
        self.db.setValue(self.xpath + '/viscosity/specification', 'polynomial')
        self.db.setValue(self.xpath + '/viscosity/polynomial', ' '.join(str(c) for c in cs))

        mu = cs[0] + cs[1]*t + cs[2]*t**2 + cs[3]*t**3
        self.assertEqual(mu, MaterialDB.getViscosity(self.mid, t))

    def testGetViscositySutherland(self):
        t = 25.0
        c1 = 1.485e-6
        s = 110.4
        self.db.setValue(self.xpath + '/viscosity/specification', 'sutherland')
        self.db.setValue(self.xpath + '/viscosity/sutherland/coefficient', str(c1))
        self.db.setValue(self.xpath + '/viscosity/sutherland/temperature', str(s))

        r'''
        .. math:: \mu = \frac{C_1 T^{3/2}}{T+S}
        '''
        mu = c1 * t ** 1.5 / (t+s)
        self.assertEqual(mu, MaterialDB.getViscosity(self.mid, t))


if __name__ == '__main__':
    unittest.main()
