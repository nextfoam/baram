import unittest
from unittest.mock import MagicMock, patch

from pathlib import Path

from openfoam.solver_info_manager import readCompleteLineOnly, readOutFile, Worker


class TestSolverInfoManager(unittest.TestCase):
    def setUp(self):
        ...

    def tearDown(self) -> None:
        ...

    def testReadCompleteLineOnly(self):
        f = MagicMock()
        f.incompleteLine = ''  # This is necessary because python unittest Mock() always returns True for hasattr()
        f.readline.side_effect = [
            'Line 1 incomplete ',
            'Line 1 middle ',
            'Line 1 ending\n',
            'Line2 incomplete ',
            'Line 2 remaining\n'
        ]
        self.assertEqual('', readCompleteLineOnly(f))
        self.assertEqual('', readCompleteLineOnly(f))
        self.assertEqual('Line 1 incomplete Line 1 middle Line 1 ending\n', readCompleteLineOnly(f))
        self.assertEqual('', readCompleteLineOnly(f))
        self.assertEqual('Line2 incomplete Line 2 remaining\n', readCompleteLineOnly(f))

    @patch('openfoam.solver_info_manager.readCompleteLineOnly')
    def testReadOutFile(self, mockReadCompleteLineOnly):
        f = MagicMock()
        del f.residualHeader  # make hasattr(f, 'residualHeader) return False
        fileContents = [
            '# Solver information\n',
            '# Time          	U_solver        	Ux_initial      	Ux_final        	Ux_iters        	Uy_initial      	Uy_final        	Uy_iters        	Uz_initial      	Uz_final        	Uz_iters        	U_converged     \n',
            '0.0120482       	DILUPBiCGStab	1.00000000e+00	8.58724200e-08	1	1.00000000e+00	5.78842110e-14	1	1.00000000e+00	6.57355850e-14	1	false\n',
            '0.0265769       	DILUPBiCGStab	3.66757700e-01	2.17151110e-13	1	9.06273050e-01	3.18900850e-13	1	3.76387760e-01	3.48509970e-13	1	false\n',
            '0.0439595       	DILUPBiCGStab	2.31957720e-02	2.67950170e-08	1	5.38653860e-01	3.35496420e-13	1	3.79282860e-02	5.53125350e-08	1	false\n',
            ''
        ]
        mockReadCompleteLineOnly.side_effect = fileContents
        lines, names = readOutFile(f)
        self.assertEqual(''.join(fileContents[2:]), lines)
        self.assertEqual(fileContents[1].split()[1:], names)

    @patch('glob.glob')
    @patch.object(Path, 'stat')
    def testGetInfoFilesMultiRegion(self, mockPathStat, mockGlobGlob):
        casePath = Path('/test/case/folder')
        files = [
            str(casePath / 'postProcessing' / 'bottomWater' / 'solverInfo_1' / '3.4' / 'solverInfo.dat'),
            str(casePath / 'postProcessing' / 'bottomWater' / 'solverInfo_1' / '4.1' / 'solverInfo.dat'),
            str(casePath / 'postProcessing' / 'bottomWater' / 'solverInfo_1' / '4.1' / 'solverInfo_4.1.dat'),
            str(casePath / 'postProcessing' / 'noRegion' / 'solverInfo_3' / '4.1' / 'solverInfo_4.1.dat'),
            str(casePath / 'postProcessing' / 'topAir' / 'solverInfo_2' / '3.4' / 'solverInfo.dat'),
        ]
        FILE_SIZE = 10
        mockGlobGlob.return_value = files
        stat = MagicMock()
        stat.st_size = FILE_SIZE
        mockPathStat.return_value = stat
        w = Worker(casePath, ['bottomWater', 'topAir'])

        infoFiles = w._getInfoFilesMultiRegion()

        self.assertIn(Path(files[1]), infoFiles)
        solverInfo = infoFiles[Path(files[1])]
        self.assertEqual(FILE_SIZE, solverInfo.size)
        self.assertIsNone(solverInfo.dup)
        self.assertEqual('bottomWater', solverInfo.rname)

        self.assertIn(Path(files[2]), infoFiles)
        solverInfo = infoFiles[Path(files[2])]
        self.assertIsNotNone(solverInfo.dup)

        self.assertNotIn(Path(files[3]), infoFiles)

        self.assertIn(Path(files[4]), infoFiles)
        solverInfo = infoFiles[Path(files[4])]
        self.assertEqual('topAir', solverInfo.rname)

    @patch('glob.glob')
    @patch.object(Path, 'stat')
    def testGetInfoFilesSingleRegion(self, mockPathStat, mockGlobGlob):
        casePath = Path('/test/case/folder')
        files = [
            str(casePath / 'postProcessing' / 'solverInfo_1' / '3.4' / 'solverInfo.dat'),
            str(casePath / 'postProcessing' / 'solverInfo_1' / '4.1' / 'solverInfo.dat'),
            str(casePath / 'postProcessing' / 'solverInfo_1' / '4.1' / 'solverInfo_4.1.dat'),
            str(casePath / 'postProcessing' / 'solverInfo_2' / '3.4' / 'solverInfo.dat'),
        ]
        FILE_SIZE = 10
        mockGlobGlob.return_value = files
        stat = MagicMock()
        stat.st_size = FILE_SIZE
        mockPathStat.return_value = stat
        w = Worker(casePath, [''])

        infoFiles = w._getInfoFilesSingleRegion()

        self.assertIn(Path(files[1]), infoFiles)
        solverInfo = infoFiles[Path(files[1])]
        self.assertEqual(FILE_SIZE, solverInfo.size)
        self.assertIsNone(solverInfo.dup)
        self.assertEqual('', solverInfo.rname)

        self.assertIn(Path(files[2]), infoFiles)
        solverInfo = infoFiles[Path(files[2])]
        self.assertIsNotNone(solverInfo.dup)


if __name__ == '__main__':
    unittest.main()
