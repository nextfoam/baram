import unittest

from baramFlow.coredb import coredb
import baramFlow.openfoam.solver


class TestSolver(unittest.TestCase):
    def setUp(self):
        self.db = coredb.createDB()

        self.rname = 'testRegion_1'
        zone = 'testZone_1'
        self.db.addRegion(self.rname)
        self.db.addCellZone(self.rname, zone)

    def tearDown(self) -> None:
        coredb.destroy()

    def testFindingPCNFoamForTransient(self):
        self.db.setValue('.//general/timeTransient', 'true')
        self.db.setValue('.//general/flowType', 'compressible')
        self.db.setValue('.//general/solverType', 'pressureBased')
        self.db.setAttribute('.//operatingConditions/gravity', 'disabled', 'true')
        self.db.setValue('.//models/energyModels', 'on')
        self.db.setValue('.//models/multiphaseModels/model', 'off')
        self.db.setValue('.//models/speciesModels', 'off')

        solvers = baramFlow.openfoam.solver.findSolvers()

        self.assertEqual(1, len(solvers))
        self.assertIn('PCNFoam', solvers)

    def testFindingPCNFoamForSteady(self):
        self.db.setValue('.//general/timeTransient', 'false')
        self.db.setValue('.//general/flowType', 'compressible')
        self.db.setValue('.//general/solverType', 'pressureBased')
        self.db.setAttribute('.//operatingConditions/gravity', 'disabled', 'true')
        self.db.setValue('.//models/energyModels', 'on')
        self.db.setValue('.//models/multiphaseModels/model', 'off')
        self.db.setValue('.//models/speciesModels', 'off')

        solvers = baramFlow.openfoam.solver.findSolvers()

        self.assertEqual(1, len(solvers))
        self.assertIn('PCNFoam', solvers)

    def testFindingPCNFoamForIncompressible(self):
        self.db.setValue('.//general/timeTransient', 'false')
        self.db.setValue('.//general/flowType', 'incompressible')
        self.db.setValue('.//general/solverType', 'pressureBased')
        self.db.setAttribute('.//operatingConditions/gravity', 'disabled', 'true')
        self.db.setValue('.//models/energyModels', 'on')
        self.db.setValue('.//models/multiphaseModels/model', 'off')
        self.db.setValue('.//models/speciesModels', 'off')

        solvers = baramFlow.openfoam.solver.findSolvers()

        self.assertNotIn('PCNFoam', solvers)


if __name__ == '__main__':
    unittest.main()
