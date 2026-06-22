#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from enum import Enum

from baramFlow.coredb.libdb import E, nsmap
from libbaram.pfloat import PFloat


class RigidBodyDynamicsSolverType(Enum):
    NEWMARK         = 'newmark'
    CRANK_NICOLSON  = 'crankNicolson'
    SYMPLECTIC      = 'symplectic'


@dataclass
class RigidBodySolver:
    solverType: RigidBodyDynamicsSolverType = RigidBodyDynamicsSolverType.NEWMARK
    velocityIntegrationCoefficient: PFloat = dataClassField(default_factory=lambda: PFloat('0.5'))
    positionIntegrationCoefficient: PFloat = dataClassField(default_factory=lambda: PFloat('0.25'))
    offCenteringAccelerationCoefficient: PFloat = dataClassField(default_factory=lambda: PFloat('0.5'))
    offCenteringVelocityCoefficient: PFloat = dataClassField(default_factory=lambda: PFloat('0.5'))

    @classmethod
    def fromElement(cls, e):
        solverType = RigidBodyDynamicsSolverType(e.find('solverType', namespaces=nsmap).text)
        velocityIntegrationCoefficient = PFloat.fromElement(e.find('velocityIntegrationCoefficient', namespaces=nsmap))
        positionIntegrationCoefficient = PFloat.fromElement(e.find('positionIntegrationCoefficient', namespaces=nsmap))
        offCenteringAccelerationCoefficient = PFloat.fromElement(e.find('offCenteringAccelerationCoefficient', namespaces=nsmap))
        offCenteringVelocityCoefficient = PFloat.fromElement(e.find('offCenteringVelocityCoefficient', namespaces=nsmap))

        return RigidBodySolver(
            solverType=solverType,
            velocityIntegrationCoefficient=velocityIntegrationCoefficient,
            positionIntegrationCoefficient=positionIntegrationCoefficient,
            offCenteringAccelerationCoefficient=offCenteringAccelerationCoefficient,
            offCenteringVelocityCoefficient=offCenteringVelocityCoefficient)

    def toElement(self):
        return E('rigidBodySolverType',
                 E('solverType', self.solverType.value),
                 self.velocityIntegrationCoefficient.toElement('velocityIntegrationCoefficient'),
                 self.positionIntegrationCoefficient.toElement('positionIntegrationCoefficient'),
                 self.offCenteringAccelerationCoefficient.toElement('offCenteringAccelerationCoefficient'),
                 self.offCenteringVelocityCoefficient.toElement('offCenteringVelocityCoefficient'))
