#!/usr/bin/env python
# -*- coding: utf-8 -*-


from enum import Enum

from .schema import FloatType, IntKeyList, EnumType, IntType, TextType, ElementSchema, BoolType, TextKeyList
from .schema import VectorComposite


class GeometryType(Enum):
    SURFACE = 'surface'
    VOLUME = 'volume'


class ShapeType(Enum):
    TRI_SURFACE_MESH = 'triSurfaceMesh'
    HEX = 'hex'
    CYLINDER = 'cylinder'
    SPHERE = 'sphere'
    HEX6 = 'hex6'


class ThicknessModel(Enum):
    FIRST_AND_OVERALL = 'firstAndOverall'
    FIRST_AND_EXPANSION = 'firstAndExpansion'
    FINAL_AND_OVERALL = 'finalAndOverall'
    FINAL_AND_EXPANSION = 'finalAndExpansion'
    OVERALL_AND_EXPANSION = 'overallAndExpansion'
    FIRST_AND_RELATIVE_FINAL = 'firstAndRelativeFinal'


geometry = {
    'gType': EnumType(GeometryType),
    'volume': IntType(),
    'name': TextType(),
    'shape': EnumType(ShapeType),
    'path': TextType().setOptional(),
    'point1': VectorComposite().schema(),
    'point2': VectorComposite().setDefault(1, 1, 1).schema(),
    'radius': FloatType().setDefault(1)
}

refinement = {
    'level': IntType().setDefault(1)
}

layer = {
    'nSurfaceLayers': IntType().setDefault(0),
    'useLocalSetting': BoolType(False),
    'thicknessModel': EnumType(ThicknessModel),
    'relativeSizes': BoolType(True),
    'firstLayerThickness': FloatType().setDefault(0.001),
    'finalLayerThickness': FloatType().setDefault(1.0),
    'thickness': FloatType().setDefault(2.0),
    'expansionRation': FloatType().setDefault(1.2),
    'minThickness': FloatType().setDefault(1.2)
}


class GeometrySchema(ElementSchema):
    def __init__(self):
        super().__init__(geometry)

    def validateElement(self, db, fullCheck=False):
        return db.data()


class RefinementSchema(ElementSchema):
    def __init__(self):
        super().__init__(refinement)


class LayerSchema(ElementSchema):
    def __init__(self):
        super().__init__(layer)


schema = {
    'geometry': IntKeyList(GeometrySchema()),
    'baseGrid': {
        'numCellsX': FloatType().setDefault(10),
        'numCellsY': FloatType().setDefault(10),
        'numCellsZ': FloatType().setDefault(10)
    },
    'castellation': {
        'vtkNonManifoldEdges': BoolType(False),
        'vtkBoundaryEdges': BoolType(True),
        'nCellsBetweenLevels': IntType().setDefault(3),
        'resolveFeatureAngle': FloatType().setDefault(30),
        'maxGlobalCells': IntType().setDefault('1e8'),
        'maxLocalCells': IntType().setDefault('1e7'),
        'maxRefinementCells': IntType().setDefault(0),
        'maxLoadUnbalance': FloatType().setDefault('0.5'),
        'allowFreeStandingZoneFaces': BoolType(True),
        'refinementSurfaces': TextKeyList(RefinementSchema()),
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
        'thicknessModel': EnumType(ThicknessModel),
        'relativeSizes': BoolType(True),
        'firstLayerThickness': FloatType().setDefault(0.001),
        'finalLayerThickness': FloatType().setDefault('1.0'),
        'thickness': FloatType().setDefault('2.0'),
        'expansionRation': FloatType().setDefault(1.2),
        'minThickness': FloatType().setDefault(1.2),
        'layers': TextKeyList(LayerSchema()),
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
        'relaxed': {
            'maxNonOrtho': FloatType().setDefault(65)
        }
    }
}
