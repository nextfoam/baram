#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from uuid import UUID

from baramFlow.base.dynamic_mesh.dynamic_mesh import MotionType
from baramFlow.base.dynamic_mesh.motion_function import MotionFunction, MotionFunctionType
from baramFlow.base.dynamic_mesh.moving_boundary import PointMotionType
from baramFlow.base.dynamic_mesh.restraint import RestraintType
from baramFlow.base.dynamic_mesh.rigid_body_dynamics import Joint, JointType
from baramFlow.base.dynamic_mesh.rigid_body_solver import RigidBodyDynamicsSolverType
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.services.dynamic_mesh.dynamic_mesh_service import DynamicMeshService
from libbaram.natural_name_uuid import uuidToNnstr
from libbaram.openfoam.dictionary.dictionary_file import DictionaryFile

from baramFlow.openfoam.file_system import FileSystem


def getMotionFunctionDict(f: MotionFunction):
    if f.functionType == MotionFunctionType.ROTATION:
        return {
            'solidBodyMotionFunction': 'rotatingMotion',
            'rotatingMotionCoeffs': {
                'origin': f.origin.toFloatList(),
                'axis': f.axis.toFloatList(),
                'omega': float(f.rpm) * 2 * math.pi / 60.0
            }
        }
    elif f.functionType == MotionFunctionType.ROTATING_OSCILLATION:
        return {
            'solidBodyMotionFunction': 'oscillatingRotatingMotion',
            'oscillatingRotatingMotionCoeffs': {
                'origin': f.origin.toFloatList(),
                'amplitude': f.angularAmplitude.toFloatList(),
                'omega': float(f.rpm) * 2 * math.pi / 60.0
            }
        }
    elif f.functionType == MotionFunctionType.LINEAR_TRANSLATION:
        return {
            'solidBodyMotionFunction': 'linearMotion',
            'linearMotionCoeffs': {
                'velocity': f.velocity.toFloatList()
            }
        }
    elif f.functionType == MotionFunctionType.LINEAR_OSCILLATION:
        return {
            'solidBodyMotionFunction': 'oscillatingLinearMotion',
            'oscillatingLinearMotionCoeffs': {
                'amplitude': f.linearAmplitude.toFloatList(),
                'omega': float(f.frequency) * 2 * math.pi
            }
        }
    elif f.functionType == MotionFunctionType.MANUAL_POSITION:
        return {
            'solidBodyMotionFunction': 'tabulated6DoFMotion',
            'tabulated6DoFMotionCoeffs': {
                'CofG': f.origin.toFloatList(),
                'timeDataFileName': f'"<constant>/{uuidToNnstr(f.uuid)}"'
            }
        }


def writeManualPositionsDataFile(f: MotionFunction):
    # Write the table consumed by tabulated6DoFMotion. Format:
    #     N
    #     (
    #         (t ((surge sway heave) (roll pitch yaw)))
    #         ...
    #     )
    p = f.positions
    assert len(p.t) == len(p.surge) == len(p.sway) == len(p.heave) \
            == len(p.roll) == len(p.pitch) == len(p.yaw)

    path = FileSystem.constantPath() / uuidToNnstr(f.uuid)
    with open(path, 'w') as file:
        file.write(f'{len(p.t)} (\n')
        for i in range(len(p.t)):
            file.write(f'({p.t[i]} (({p.surge[i]} {p.sway[i]} {p.heave[i]}) ({p.roll[i]} {p.pitch[i]} {p.yaw[i]})))\n')
        file.write(')\n')


class DynamicMeshDict(DictionaryFile):
    def __init__(self, rname: str):
        super().__init__(FileSystem.caseRoot(), self.constantLocation(rname), 'dynamicMeshDict')

        self._rname = rname

        self._dynamicMesh = DynamicMeshService().getDynamicMesh()

    def build(self):
        if self._data is not None:
            return self

        if self._dynamicMesh.motionType == MotionType.MOVING_CELL_ZONE:
            self._buildMovingCellZone()
        elif self._dynamicMesh.motionType == MotionType.MOVING_BOUNDARY:
            self._buildMovingBoundary()
        elif self._dynamicMesh.motionType == MotionType.RIGID_BODY_DYNAMICS:
            self._buildRigidBodyDynamics()

        # db = CoreDBReader()

        # zones = db.getCellZonesByType(self._rname, ZoneType.SLIDING_MESH.value)
        # if zones:
        #     self._data = {
        #         'dynamicFvMesh': 'dynamicMotionSolverListFvMesh',
        #         'motionSolverLibs': ['"libfvMotionSolvers.so"'],
        #         'motionSolver': 'fvMotionSolvers',
        #         'solvers': {}
        #     }

        #     for czid in zones:
        #         xpath = CellZoneDB.getXPath(czid)
        #         name = db.getValue(xpath + '/name')

        #         self._data['solvers'][f'sliding_{name}'] = {
        #             'solver': 'solidBody',
        #             'solidBodyMotionFunction': 'rotatingMotion',
        #             'cellZone': name,
        #             'rotatingMotionCoeffs': {
        #                 'origin': db.getVector(xpath + '/slidingMesh/rotationAxisOrigin'),
        #                 'axis': db.getVector(xpath + '/slidingMesh/rotationAxisDirection'),
        #                 'omega': float(db.getValue(xpath + '/slidingMesh/rotatingSpeed')) * 2 * 3.141592 / 60
        #             }
        #         }

        return self

    def _buildMovingCellZone(self):
        solvers = {}

        for motionDefinition in self._dynamicMesh.motionDefinitions:
            multiMotionCoeffs = {}

            for mFunction in motionDefinition.motionFunctions:
                multiMotionCoeffs[uuidToNnstr(mFunction.uuid)] = getMotionFunctionDict(mFunction)
                if mFunction.functionType == MotionFunctionType.MANUAL_POSITION:
                    writeManualPositionsDataFile(mFunction)

            mdData = {
                'motionSolver': 'solidBody',
                'solidBodyCoeffs': {
                    'solidBodyMotionFunction': 'multiMotion',
                    'multiMotionCoeffs': multiMotionCoeffs
                }
            }

            if motionDefinition.cellZones:
                cellZoneNames = [CellZoneDB.getCellZoneName(czid) for czid in motionDefinition.cellZones]
                mdData['solidBodyCoeffs']['cellZone'] = '"(' + '|'.join(cellZoneNames) + ')"'

            solvers[uuidToNnstr(motionDefinition.uuid)] = mdData

        self._data = {
            'dynamicFvMesh': 'dynamicMotionSolverListFvMesh',
            'motionSolverLibs': ['fvMotionSolvers'],
            'solvers': solvers
        }

    def _buildMovingBoundary(self):
        movingBoundaries = [BoundaryDB.getBoundaryName(mb.boundary) for mb in self._dynamicMesh.movingBoundaries
                            if mb.pointMotionType in (PointMotionType.PRESCRIBED_MOTION, PointMotionType.RIGID_BODY_MOTION)]

        self._data = {
            'dynamicFvMesh': 'dynamicMotionSolverFvMesh',
            'motionSolverLibs': ['fvMotionSolvers'],
            'motionSolver': 'displacementLaplacian',
            'displacementLaplacianCoeffs': {
                'diffusivity': ('inverseDistance', movingBoundaries)
            }
        }


    def _buildRigidBodyDynamics(self):
        rbd = self._dynamicMesh.rigidBodyDynamics

        if rbd.solver.solverType == RigidBodyDynamicsSolverType.NEWMARK:
            solver = {
                'type': 'Newmark',
                'gamma': float(rbd.solver.velocityIntegrationCoefficient),
                'beta': float(rbd.solver.positionIntegrationCoefficient)
            }
        elif rbd.solver.solverType == RigidBodyDynamicsSolverType.CRANK_NICOLSON:
            solver = {
                'type': 'CrankNicolson',
                'aoc': float(rbd.solver.offCenteringAccelerationCoefficient),
                'beta': float(rbd.solver.offCenteringVelocityCoefficient)
            }
        elif rbd.solver.solverType == RigidBodyDynamicsSolverType.SYMPLECTIC:
            solver = {
                'type': 'symplectic',
            }
        else:
            raise AssertionError

        bodies = {}
        for body in rbd.bodies:
            bDict = {
                'type': 'rigidBody',
                'parent': 'root' if body.parent == UUID(int=0) else uuidToNnstr(body.parent),
                'mass': float(body.mass),
                'centreOfMass': body.centerOfMass.toFloatList(),
                'inertia': [float(i) for i in body.momentOfInertia],
                'transform': ([float(i) for i in body.orientation], body.localOrigin.toFloatList()),
                'patches': [BoundaryDB.getBoundaryName(bcid) for bcid in body.boundaries],
                'innerDistance': float(body.deformationOffset),
                'outerDistance': float(body.deformationDistance)
            }

            jDict = self._compactJointDict([self._jointDict(j) for j in body.joints])
            if len(jDict) == 1:
                bDict['joint'] = jDict[0]
            elif len(jDict) > 1:
                bDict['joint'] = {
                    'type': 'composite',
                    'joints': jDict
                }

            bodies[uuidToNnstr(body.uuid)] = bDict

            restraints = {}
            for r in body.restraints:
                if r.restraintType == RestraintType.SIMPLE_DAMPER:
                    restraints[uuidToNnstr(r.uuid)] = {
                        'type': 'linearDamper',
                        'body': uuidToNnstr(body.uuid),
                        'coeff': float(r.dampingConstant)
                    }
                elif r.restraintType == RestraintType.TRANSLATIONAL_SPRING:
                    restraints[uuidToNnstr(r.uuid)] = {
                        'type': 'linearSpring',
                        'body': uuidToNnstr(body.uuid),
                        'refAttachmentPt': r.attachmentPoint.toFloatList(),
                        'anchor': r.anchorPoint.toFloatList(),
                        'restLength': float(r.restLength),
                        'stiffness': float(r.springConstant),
                        'damping': float(r.dampingConstant)
                    }
                elif r.restraintType == RestraintType.ROTATIONAL_SPRING:
                    restraints[uuidToNnstr(r.uuid)] = {
                        'type': 'linearAxialAngularSpring',
                        'body': uuidToNnstr(body.uuid),
                        'axis': r.axis.toFloatList(),
                        'stiffness': float(r.springConstant),
                        'damping': float(r.dampingConstant)
                    }

        self._data = {
            'dynamicFvMesh': 'dynamicMotionSolverFvMesh',
            'motionSolverLibs': ['rigidBodyMeshMotion'],
            'motionSolver': 'rigidBodyMotion',
            'rigidBodyMotionCoeffs': {
                'solver': solver,
                'accelerationRelaxation': float(rbd.accelerationRelaxationFactor),
                'accelerationDamping': float(rbd.accelerationDampingFactor),
                'bodies': bodies,
            },
            'restraints': restraints
        }

    def _jointDict(self, joint: Joint) -> dict:
        if joint.jointType == JointType.SPHERICAL:
            return {'type': 'Rs' }

        elif joint.jointType == JointType.PRISMATIC:
            if joint.direction.isXAligned():
                return {'type': 'Px' }
            elif joint.direction.isYAligned():
                return {'type': 'Py' }
            elif joint.direction.isZAligned():
                return {'type': 'Pz' }
            else:
                return {'type': 'Pa',
                        'axis': joint.direction.toFloatList() }

        elif joint.jointType == JointType.REVOLUTE:
            if joint.axis.isXAligned():
                return {'type': 'Rx' }
            elif joint.axis.isYAligned():
                return {'type': 'Ry' }
            elif joint.axis.isZAligned():
                return {'type': 'Rz' }
            else:
                return {'type': 'Ra',
                        'axis': joint.axis.toFloatList() }

        else:
            raise AssertionError

    def _compactJointDict(self, joints):
        result = []
        i = 0
        while i < len(joints):
            if i + 2 < len(joints):
                types = [joints[i + k]['type'] for k in range(3)]
                if set(types) == {'Px', 'Py', 'Pz'}:
                    result.append({'type': 'Pxyz'})
                    i += 3
                    continue
                elif all(t in ('Rx', 'Ry', 'Rz') for t in types) and len(set(types)) == 3:
                    axes = ''.join(t[1] for t in types)
                    result.append({'type': f'R{axes}'})
                    i += 3
                    continue
            result.append(joints[i])
            i += 1
        return result



