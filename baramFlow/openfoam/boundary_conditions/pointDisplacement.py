#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
from numpy.typing import NDArray

from baramFlow.base.base import Vector
from baramFlow.base.dynamic_mesh.dynamic_mesh import MotionType
from baramFlow.base.dynamic_mesh.motion_function import MotionFunctionType
from baramFlow.base.dynamic_mesh.moving_boundary import MovingBoundaryEntry, PointMotionType, RotationalConstraintType, TranslationalConstraintType
from baramFlow.base.dynamic_mesh.restraint import RestraintType
from baramFlow.base.dynamic_mesh.rigid_body_solver import RigidBodyDynamicsSolverType
from baramFlow.coredb.boundary_db import BoundaryType
from baramFlow.coredb.coredb_reader import Region
from baramFlow.openfoam.boundary_conditions.boundary_condition import BoundaryCondition
from baramFlow.openfoam.constant.dynamic_mesh_dict import getMotionFunctionDict, writeManualPositionsDataFile
from baramFlow.services.dynamic_mesh.dynamic_mesh_service import DynamicMeshService
from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.openfoam.dictionary.dictionary_file import DataClass
from libbaram.pfloat import PFloat


# It returns the numbers in string form to keep high precision in resulting OpenFOAM dictionary
# PyFoam makes numbers in a list single precision numbers string.
def normalizedOrientationTensor(otensor: list[PFloat]) -> str:
    orientation: NDArray = np.array([float(i) for i in otensor], dtype=np.float64)
    orientation = orientation * np.sqrt(3) / np.linalg.norm(orientation)
    return '('  + ' '.join([str(f) for f in orientation.tolist()]) + ')'


class PointDisplacement(BoundaryCondition):
    DIMENSIONS = '[0 1 0 0 0 0 0]'

    def __init__(self, region: Region, time, processorNo):
        super().__init__(region, time, processorNo, 'pointDisplacement', DataClass.CLASS_POINT_VECTOR_FIELD)

        self._initialValue = Vector.zero()

        self._dynamicMesh = DynamicMeshService().getDynamicMesh()

        if self._dynamicMesh.motionType == MotionType.RIGID_BODY_DYNAMICS:
            self._rigidBodyDynamicsBoundary = set()
            for body in self._dynamicMesh.rigidBodyDynamics.bodies:
                for bcid in body.boundaries:
                    self._rigidBodyDynamicsBoundary.add(bcid)

    def build0(self):
        if self._dynamicMesh.motionType in [MotionType.NONE, MotionType.MOVING_CELL_ZONE]:
            self._data = None
        else:
            self._data = {
                'dimensions': self.DIMENSIONS,
                'internalField': ('uniform', self._initialValue.toFloatList()),
                'boundaryField': self._constructBoundaryField()
            }

        return self

    def _constructBoundaryField(self):
        field = {}

        for bcidInt, name, type_ in self._region.boundaries:
            bcid = str(bcidInt)

            field[name] = {
                BoundaryType.VELOCITY_INLET.value:      (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.FLOW_RATE_INLET.value:     (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.FLOW_RATE_OUTLET.value:    (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.PRESSURE_INLET.value:      (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.PRESSURE_OUTLET.value:     (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.INTAKE_FAN.value:          (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.EXHAUST_FAN.value:         (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.ABL_INLET.value:           (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.OPEN_CHANNEL_INLET.value:  (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.OPEN_CHANNEL_OUTLET.value: (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.OUTFLOW.value:             (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.FREE_STREAM.value:         (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.FAR_FIELD_RIEMANN.value:   (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.SUBSONIC_INLET.value:      (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.SUBSONIC_OUTFLOW.value:    (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.SUPERSONIC_INFLOW.value:   (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.SUPERSONIC_OUTFLOW.value:  (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.WALL.value:                (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.THERMO_COUPLED_WALL.value: (lambda: self._constructPointDisplacement(bcid)),
                BoundaryType.SYMMETRY.value:            (lambda: self._constructSymmetry()),
                BoundaryType.INTERFACE.value:           (lambda: self._constructCyclic()),
                BoundaryType.POROUS_JUMP.value:         (lambda: self._constructCyclic()),
                BoundaryType.FAN.value:                 (lambda: self._constructCyclic()),
                BoundaryType.EMPTY.value:               (lambda: self._constructEmpty()),
                BoundaryType.CYCLIC.value:              (lambda: self._constructCyclic()),
                BoundaryType.CYCLIC_ACMI.value:         (lambda: self._constructCyclic()),
                BoundaryType.WEDGE.value:               (lambda: self._constructWedge()),
            }.get(type_, lambda: None)()

        return field

    def _constructPointDisplacement(self, bcid: str):

        if self._dynamicMesh.motionType == MotionType.MOVING_BOUNDARY:
            boundaryEntry = next((be for be in self._dynamicMesh.movingBoundaries if be.boundary == bcid), None)

            if boundaryEntry is None:
                return self._constructFixedValue(Vector.zero().toFloatList())

            if boundaryEntry.pointMotionType == PointMotionType.FIXED:
                return self._constructFixedValue(Vector.zero().toFloatList())

            elif boundaryEntry.pointMotionType == PointMotionType.SLIP:
                if not boundaryEntry.useFixedNormal:
                    return {'type': 'slip'}
                else:
                    return {
                                'type': 'fixedNormalSlip',
                                'n': boundaryEntry.normal.toFloatList()
                            }

            elif boundaryEntry.pointMotionType == PointMotionType.PRESCRIBED_MOTION:
                return self._constructPrescribedMotion(boundaryEntry)

            elif boundaryEntry.pointMotionType == PointMotionType.RIGID_BODY_MOTION:
                return self._constructRigidBodyMotion(boundaryEntry)

        elif self._dynamicMesh.motionType == MotionType.RIGID_BODY_DYNAMICS:
            if bcid in self._rigidBodyDynamicsBoundary:
                return {
                    'type': 'calculated'
                }
            else:
                return self._constructFixedValue(Vector.zero().toFloatList())

    def _constructPrescribedMotion(self, be: MovingBoundaryEntry):
        multiMotionCoeffs = {}
        for mFunction in be.motionFunctions:
            data = getMotionFunctionDict(mFunction)
            multiMotionCoeffs[uuidToNnstr(mFunction.uuid)] = data
            if mFunction.functionType == MotionFunctionType.MANUAL_POSITION:
                writeManualPositionsDataFile(mFunction)

        return {
            'type': 'solidBodyMotionDisplacement',
            'solidBodyMotionFunction': 'multiMotion',
            'multiMotionCoeffs': multiMotionCoeffs
        }

    def _constructRigidBodyMotion(self, be: MovingBoundaryEntry):
        rbm = be.rigidBodyMotion

        if rbm.solver.solverType == RigidBodyDynamicsSolverType.NEWMARK:
            solver = {
                'type': 'Newmark',
                'gamma': float(rbm.solver.velocityIntegrationCoefficient),
                'beta': float(rbm.solver.positionIntegrationCoefficient)
            }
        elif rbm.solver.solverType == RigidBodyDynamicsSolverType.CRANK_NICOLSON:
            solver = {
                'type': 'CrankNicolson',
                'aoc': float(rbm.solver.offCenteringAccelerationCoefficient),
                'beta': float(rbm.solver.offCenteringVelocityCoefficient)
            }
        elif rbm.solver.solverType == RigidBodyDynamicsSolverType.SYMPLECTIC:
            solver = {
                'type': 'symplectic',
            }
        else:
            raise AssertionError

        constraints = {}

        if rbm.translationalConstraintType == TranslationalConstraintType.PLANE:
            constraints['translation'] = {
                'sixDoFRigidBodyMotionConstraint': 'plane',
                'normal': rbm.normal.toFloatList(),
                'centreOfRotation': rbm.centerOfRotation.toFloatList()
            }
        elif rbm.translationalConstraintType == TranslationalConstraintType.LINE:
            constraints['translation'] = {
                'sixDoFRigidBodyMotionConstraint': 'line',
                'direction': rbm.direction.toFloatList(),
                'centreOfRotation': rbm.centerOfRotation.toFloatList()
            }
        elif rbm.translationalConstraintType == TranslationalConstraintType.FIXED:
            constraints['translation'] = {
                'sixDoFRigidBodyMotionConstraint': 'point',
                'centreOfRotation': rbm.centerOfRotation.toFloatList()
            }

        if rbm.rotationalConstraintType == RotationalConstraintType.AXIS:
            constraints['rotation'] = {
                'sixDoFRigidBodyMotionConstraint': 'axis',
                'axis': rbm.axis.toFloatList(),
            }

            if rbm.limitAngle:
                orientation = rbm.orientation if rbm.useBoundaryOrientation else rbm.constraintOrientation
                constraints['rotation'].update({
                    'thetaUnits': 'degrees',
                    'maxClockwiseTheta': float(rbm.clockwise),
                    'maxCounterclockwiseTheta': float(rbm.counterclockwise),
                    'referenceOrientation': normalizedOrientationTensor(orientation),
                })

        elif rbm.rotationalConstraintType == RotationalConstraintType.FIXED:
            constraints['rotation'] = {
                'sixDoFRigidBodyMotionConstraint': 'orientation',
            }

        restraints = {}
        for r in rbm.restraints:
            if r.restraintType == RestraintType.SIMPLE_DAMPER:
                restraints[uuidToNnstr(r.uuid)] = {
                    'sixDoFRigidBodyMotionRestraint': 'linearDamper',
                    'coeff': float(r.dampingConstant)
                }
            elif r.restraintType == RestraintType.TRANSLATIONAL_SPRING:
                restraints[uuidToNnstr(r.uuid)] = {
                    'sixDoFRigidBodyMotionRestraint': 'linearSpring',
                    'refAttachmentPt': r.attachmentPoint.toFloatList(),
                    'anchor': r.anchorPoint.toFloatList(),
                    'restLength': float(r.restLength),
                    'stiffness': float(r.springConstant),
                    'damping': float(r.dampingConstant)
                }
            elif r.restraintType == RestraintType.ROTATIONAL_SPRING:
                orientation = rbm.orientation if rbm.useBoundaryOrientation else r.orientation
                restraints[uuidToNnstr(r.uuid)] = {
                    'sixDoFRigidBodyMotionRestraint': 'linearAxialAngularSpring',
                    'axis': r.axis.toFloatList(),
                    'stiffness': float(r.springConstant),
                    'damping': float(r.dampingConstant),
                    'referenceOrientation': normalizedOrientationTensor(orientation),
                }

        return {
            'type': 'sixDoFRigidBodyDisplacement',
            'mass': float(rbm.mass),
            'centreOfMass': rbm.centerOfMass.toFloatList(),
            'momentOfInertia': [float(i) for i in rbm.momentOfInertia],
            'orientation': [float(i) for i in rbm.orientation],
            'centreOfRotation': rbm.centerOfRotation.toFloatList(),
            'accelerationRelaxation': float(rbm.accelerationRelaxationFactor),
            'accelerationDamping': float(rbm.accelerationDampingFactor),
            'solver': solver,
            'constraints': constraints,
            'restraints': restraints,
            'value': ('uniform', Vector.zero().toFloatList())
        }