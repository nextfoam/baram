#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, auto, IntEnum

from .simple_schema import FloatType, IntKeyList, EnumType, IntType, TextType, BoolType, PositiveIntType
from .simple_schema import VectorComposite


class Step(IntEnum):
    NONE = -1

    GEOMETRY = 0
    BASE_GRID = auto()
    REGION = auto()
    CASTELLATION = auto()
    SNAP = auto()
    BOUNDARY_LAYER = auto()
    EXPORT = auto()

    LAST_STEP = EXPORT


class GeometryType(Enum):
    SURFACE = 'surface'
    VOLUME = 'volume'


class Shape(Enum):
    TRI_SURFACE_MESH = 'triSurfaceMesh'
    HEX = 'hex'
    CYLINDER = 'cylinder'
    SPHERE = 'sphere'
    HEX6 = 'hex6'
    X_MIN = 'xMin'
    X_MAX = 'xMax'
    Y_MIN = 'yMin'
    Y_MAX = 'yMax'
    Z_MIN = 'zMin'
    Z_MAX = 'zMax'

    PLATES = [X_MIN, X_MAX, Y_MIN, Y_MAX, Z_MIN, Z_MAX]


class CFDType(Enum):
    NONE = 'none'
    CELL_ZONE = 'cellZone'
    BOUNDARY = 'boundary'
    INTERFACE = 'interface'


class RegionType(Enum):
    FLUID = 'fluid'
    SOLID = 'solid'


class ThicknessModel(Enum):
    FIRST_AND_OVERALL = 'firstAndOverall'
    FIRST_AND_EXPANSION = 'firstAndExpansion'
    FINAL_AND_OVERALL = 'finalAndOverall'
    FINAL_AND_EXPANSION = 'finalAndExpansion'
    OVERALL_AND_EXPANSION = 'overallAndExpansion'
    FIRST_AND_RELATIVE_FINAL = 'firstAndRelativeFinal'


geometry = {
    'gType': EnumType(GeometryType),
    'volume': IntType().setOptional(),
    'name': TextType(),
    'shape': EnumType(Shape),
    'cfdType': EnumType(CFDType),
    'nonConformal': BoolType(False),
    'interRegion': BoolType(False),
    'path': TextType().setOptional(),
    'point1': VectorComposite().schema(),
    'point2': VectorComposite().setDefault(1, 1, 1).schema(),
    'radius': FloatType().setDefault(1),
    'castellationGroup': IntType().setOptional().setDefault(None),
    'layerGroup': IntType().setOptional().setDefault(None)
}

region = {
    'name': TextType(),
    'type': EnumType(RegionType),
    'point': VectorComposite().schema()
}

surfaceRefinement = {
    'groupName': TextType(),
    'surfaceRefinementLevel': IntType().setDefault(1),
    'featureEdgeRefinementLevel': IntType().setDefault(0),
}

volumeRefinement = {
    'groupName': TextType(),
    'volumeRefinementLevel': PositiveIntType().setDefault(1)
}

layer = {
    'groupName': TextType(),
    'nSurfaceLayers': PositiveIntType().setDefault(1),
    'thicknessModel': EnumType(ThicknessModel).setDefault(ThicknessModel.FINAL_AND_EXPANSION),
    'relativeSizes': BoolType(True),
    'firstLayerThickness': FloatType().setDefault(0.3),
    'finalLayerThickness': FloatType().setDefault(0.5),
    'thickness': FloatType().setDefault(0.5),
    'expansionRatio': FloatType().setDefault(1.2),
    'minThickness': FloatType().setDefault(0.3)
}


schema = {
    'step': EnumType(Step).setDefault(Step.GEOMETRY),
    'geometry': IntKeyList(geometry),
    'region': IntKeyList(region),
    'baseGrid': {
        'numCellsX': PositiveIntType().setDefault(10),
        'numCellsY': PositiveIntType().setDefault(10),
        'numCellsZ': PositiveIntType().setDefault(10)
    },
    'castellation': {
        'vtkNonManifoldEdges': BoolType(False),
        'vtkBoundaryEdges': BoolType(True),
        'nCellsBetweenLevels': IntType().setDefault(3),
        'resolveFeatureAngle': FloatType().setDefault(30),
        'maxGlobalCells': IntType().setDefault('1e8'),
        'maxLocalCells': IntType().setDefault('1e7'),
        'minRefinementCells': IntType().setDefault(0),
        'maxLoadUnbalance': FloatType().setDefault('0.5'),
        'allowFreeStandingZoneFaces': BoolType(True),
        'refinementSurfaces': IntKeyList(surfaceRefinement),
        'refinementVolumes': IntKeyList(volumeRefinement),
    },
    'snap': {
        'nSmoothPatch': IntType().setDefault(3),
        'nSmoothInternal': IntType().setDefault(3),
        'nSolveIter': IntType().setDefault(30),
        'nRelaxIter': IntType().setDefault(5),
        'nFeatureSnapIter': IntType().setDefault(15),
        'multiRegionFeatureSnap': BoolType(False),
        'tolerance': FloatType().setDefault(3),
        'concaveAngle': FloatType().setDefault(45),
        'minAreaRation': FloatType().setDefault(0.3)
    },
    'addLayers': {
        # 'thicknessModel': EnumType(ThicknessModel).setDefault(ThicknessModel.FINAL_AND_OVERALL),
        # 'relativeSizes': BoolType(True),
        # 'firstLayerThickness': FloatType().setDefault(0.3),
        # 'finalLayerThickness': FloatType().setDefault('0.5'),
        # 'thickness': FloatType().setDefault('0.5'),
        # 'expansionRatio': FloatType().setDefault(1.2),
        # 'minThickness': FloatType().setDefault(0.3),
        'layers': IntKeyList(layer),
        'nGrow': IntType().setDefault(0),
        'maxFaceThicknessRatio': FloatType().setDefault(0.5),
        'nSmoothSurfaceNormals': IntType().setDefault(1),
        'nSmoothThickness': FloatType().setDefault(10),
        'minMedialAxisAngle': FloatType().setDefault(90),
        'maxThicknessToMedialRatio': FloatType().setDefault(0.3),
        'nSmoothNormals': IntType().setDefault(3),
        'slipFeatureAngle': FloatType().setDefault(30),
        'nRelaxIter': IntType().setDefault(10),
        'nBufferCellsNoExtrude': IntType().setDefault(0),
        'nLayerIter': IntType().setDefault(50),
        'nRelaxedIter': IntType().setDefault(20)
    },
    'meshQuality': {
        'maxNonOrtho': FloatType().setDefault(65),
        'maxBoundarySkewness': FloatType().setDefault(65),
        'maxInternalSkewness': FloatType().setDefault(4),
        'maxConcave': FloatType().setDefault(80),
        'minVol': FloatType().setDefault('1e-13'),
        'minTetQuality': FloatType().setDefault('1e-15'),
        'minVolCollapseRatio': FloatType().setDefault(0.5),
        'minArea': FloatType().setDefault(-1),
        'minTwist': FloatType().setDefault(0.02),
        'minDeterminant': FloatType().setDefault('1e-13'),
        'minFaceWeight': FloatType().setDefault(0.05),
        'minFaceFlatness': FloatType().setDefault(-1),
        'minVolRatio': FloatType().setDefault(0.01),
        'minTriangleTwist': FloatType().setDefault(-1),
        'nSmoothScale': IntType().setDefault(4),
        'errorReduction': FloatType().setDefault(0.75),
        'mergeTolerance': FloatType().setDefault(1e-6),
        'relaxed': {
            'maxNonOrtho': FloatType().setDefault(65)
        }
    }
}
