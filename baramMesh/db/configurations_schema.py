#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum, auto, IntEnum

from libbaram.validation import FloatType, IntKeyList, EnumType, IntType, TextType, BoolType, VectorComposite


CURRENT_CONFIGURATIONS_VERSION = 5
CONFIGURATIONS_VERSION_KEY = 'version'


class Step(IntEnum):
    NONE = -1

    GEOMETRY = 0
    REGION = auto()
    BASE_GRID = auto()
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


class FeatureSnapType(Enum):
    EXPLICIT = 'explicit'
    IMPLICIT = 'implicit'


class GapRefinementMode(Enum):
    NONE = 'none'
    INSIDE = 'inside'
    OUTSIDE = 'outside'
    MIXED = 'mixed'


class BufferLayerPointSmoothingMethod(Enum):
    LAPLACIAN = 'laplacian'
    GETME = 'geometricElementTransform'


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
    'layerGroup': IntType().setOptional().setDefault(None),
    'slaveLayerGroup': IntType().setOptional().setDefault(None),
    'addBufferLayers': BoolType(False)
}

region = {
    'name': TextType(),
    'type': EnumType(RegionType),
    'point': VectorComposite().schema()
}

surfaceRefinement = {
    'groupName': TextType(),
    'surfaceRefinement': {
        'minimumLevel': IntType().setRange(0, 10).setDefault(1),
        'maximumLevel': IntType().setRange(1, 10).setDefault(1)
    },
    'featureEdgeRefinementLevel': IntType().setRange(1, 10).setDefault(1),
    'curvatureRefinement': {
        'disabled': BoolType(True),
        'numberOfCells': IntType().setLowLimit(1).setDefault(10),
        'maxLevel': IntType().setRange(1, 10).setDefault(7),
        'excludeSharpSurface': BoolType(False),
        'minRadius': FloatType().setLowLimit(0, True)
    }
}

volumeRefinement = {
    'groupName': TextType(),
    'volumeRefinementLevel': IntType().setRange(0, 10).setDefault(1),
    'gapRefinement': {
        'minCellLayers': IntType().setLowLimit(3, False).setDefault(4),
        'detectionStartLevel': IntType().setRange(0, 10).setDefault(1),
        'maxRefinementLevel': IntType().setRange(1, 10).setDefault(1),
        'direction': EnumType(GapRefinementMode),
        'gapSelf': BoolType(True)
    },
    'levelIncrement': {
        'disabled': BoolType(True),
        'splitCountX': IntType().setRange(0, 10).setDefault(1),
        'splitCountY': IntType().setRange(0, 10),
        'splitCountZ': IntType().setRange(0, 10),
        'minLevel': IntType().setRange(0, 10),
        'maxLevel': IntType().setRange(0, 10).setDefault(10),
    }
}

layer = {
    'groupName': TextType(),
    'nSurfaceLayers': IntType().setLowLimit(1),
    'thicknessModel': EnumType(ThicknessModel).setDefault(ThicknessModel.FINAL_AND_EXPANSION),
    'relativeSizes': BoolType(True),
    'firstLayerThickness': FloatType().setDefault(0.3),
    'finalLayerThickness': FloatType().setDefault(0.5),
    'thickness': FloatType().setDefault(0.5),
    'expansionRatio': FloatType().setDefault(1.2),
    'minThickness': FloatType().setDefault(0.3)
}


schema = {
    CONFIGURATIONS_VERSION_KEY: IntType().setDefault(CURRENT_CONFIGURATIONS_VERSION),
    'step': EnumType(Step).setDefault(Step.GEOMETRY),
    'geometry': IntKeyList(geometry),
    'region': IntKeyList(region),
    'baseGrid': {
        'numCellsX': IntType().setLowLimit(1).setDefault(10),
        'numCellsY': IntType().setLowLimit(1).setDefault(10),
        'numCellsZ': IntType().setLowLimit(1).setDefault(10),
        'boundingHex6': IntType().setOptional().setDefault(None)
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
        'nSmoothPatch': IntType().setDefault(0),
        'nSmoothInternal': IntType().setDefault(0),
        'nSolveIter': IntType().setDefault(30),
        'nRelaxIter': IntType().setDefault(5),
        'nFeatureSnapIter': IntType().setDefault(15),
        'featureSnapType': EnumType(FeatureSnapType),
        'multiRegionFeatureSnap': BoolType(False),
        'tolerance': FloatType().setDefault(3),
        'concaveAngle': FloatType().setDefault(45),
        'minAreaRatio': FloatType().setDefault(0.3),
        'bufferLayer': {
            'disabled': BoolType(True),
            'pointSmoothingMethod': EnumType(BufferLayerPointSmoothingMethod),
            'numberOfPointSmoothingIteration': IntType().setDefault(10).setLowLimit(10).setHighLimit(100),
            'GETMeTransformationParameter': FloatType().setDefault(0.667).setLowLimit(0, False).setHighLimit(1),
        }
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
        'featureAngle': FloatType().setDefault(60),
        'maxFaceThicknessRatio': FloatType().setDefault(0.5),
        'nSmoothSurfaceNormals': IntType().setDefault(1),
        'nSmoothThickness': FloatType().setDefault(10),
        'minMedialAxisAngle': FloatType().setDefault(90),
        'maxThicknessToMedialRatio': FloatType().setDefault(0.3),
        'nSmoothNormals': IntType().setDefault(3),
        'nRelaxIter': IntType().setDefault(10),
        'nBufferCellsNoExtrude': IntType().setDefault(0),
        'nLayerIter': IntType().setDefault(50),
        'nRelaxedIter': IntType().setDefault(20)
    },
    'meshQuality': {
        'maxNonOrtho': FloatType().setDefault(65),
        'maxBoundarySkewness': FloatType().setDefault(20),
        'maxInternalSkewness': FloatType().setDefault(4),
        'maxConcave': FloatType().setDefault(80),
        'minVol': FloatType().setDefault('1e-13'),
        'minTetQuality': FloatType().setDefault('1e-9'),
        'minVolCollapseRatio': FloatType().setDefault(-1),
        'minArea': FloatType().setDefault(-1),
        'minTwist': FloatType().setDefault(0.02),
        'minDeterminant': FloatType().setDefault(0.001),
        'minFaceWeight': FloatType().setDefault(0.05),
        'minFaceFlatness': FloatType().setDefault(-1),
        'minVolRatio': FloatType().setDefault(0.01),
        'minTriangleTwist': FloatType().setDefault(-1),
        'nSmoothScale': IntType().setDefault(4),
        'errorReduction': FloatType().setDefault(0.75),
        'mergeTolerance': FloatType().setDefault(1e-6),
        'relaxed': {
            'maxNonOrtho': FloatType().setDefault(75)
        }
    }
}
