#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4, UUID

import qasync

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QLabel, QListWidgetItem, QMenu, QWidget,
                                QVBoxLayout, QHBoxLayout, QMessageBox)

from baramFlow.base.dynamic_mesh.dynamic_mesh import MotionType
from baramFlow.base.dynamic_mesh.motion_definition import MotionDefinition
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.cell_zone_db import CellZoneDB
from baramFlow.base.dynamic_mesh.moving_boundary import MovingBoundaryEntry
from baramFlow.base.dynamic_mesh.rigid_body_dynamics import Body
from baramFlow.base.dynamic_mesh.rigid_body_solver import RigidBodyDynamicsSolverType

from baramFlow.services.dynamic_mesh.dynamic_mesh_service import DynamicMeshService, CONSTRAINT_BOUNDARY_TYPE_MAP
from baramFlow.view.setup.dynamic_mesh.motion_type_dialog import MotionTypeDialog
from baramFlow.view.setup.dynamic_mesh.moving_cell_zone.motion_definition_dialog import MotionDefinitionDialog
from baramFlow.view.setup.dynamic_mesh.moving_boundary.point_motion_dialog import (
    PointMotionDialog, POINT_MOTION_TYPE_NAMES,
)
from baramFlow.view.setup.dynamic_mesh.rigid_body_dynamics.body_dialog import BodyDialog
from baramFlow.view.widgets.content_page import ContentPage

from widgets.async_message_box import AsyncMessageBox

from .dynamic_mesh_page_ui import Ui_DynamicMeshPage


MOTION_TYPE_NAMES = {
    MotionType.NONE: 'None',
    MotionType.MOVING_CELL_ZONE: 'Moving Cell Zone',
    MotionType.MOVING_BOUNDARY: 'Moving Boundary',
    MotionType.RIGID_BODY_DYNAMICS: 'Rigid Body Dynamics',
}


class DynamicMeshPage(ContentPage):
    def __init__(self, parent):
        super().__init__(parent)

        self._ui = Ui_DynamicMeshPage()
        self._ui.setupUi(self)

        self._dynamicMesh = DynamicMeshService().getDynamicMesh()

        # Solver combo items
        self._ui.rbdSolverCombo.addItem('Newmark', RigidBodyDynamicsSolverType.NEWMARK)
        self._ui.rbdSolverCombo.addItem('Crank-Nicolson', RigidBodyDynamicsSolverType.CRANK_NICOLSON)
        self._ui.rbdSolverCombo.addItem('Symplectic', RigidBodyDynamicsSolverType.SYMPLECTIC)

        self._dialog = None

        self._connectSignalsSlots()

        self._updatePage()

    def _connectSignalsSlots(self):
        self._ui.changeTypeButton.clicked.connect(self._changeMotionType)

        # Moving Cell Zone
        self._ui.mdList.customContextMenuRequested.connect(self._showMdContextMenu)
        self._ui.mdList.itemDoubleClicked.connect(self._editMotionDefinition)
        self._ui.addMdButton.clicked.connect(self._addMotionDefinition)

        # Moving Boundary
        self._ui.mbList.itemDoubleClicked.connect(self._editBoundary)
        self._ui.editBoundaryButton.clicked.connect(self._editBoundary)
        self._ui.mbList.currentItemChanged.connect(
            lambda: self._ui.editBoundaryButton.setEnabled(self._ui.mbList.currentRow() >= 0))

        # Rigid Body Dynamics
        self._ui.rbdSolverCombo.currentIndexChanged.connect(self._rbdSolverChanged)
        self._ui.bodyList.customContextMenuRequested.connect(self._showBodyContextMenu)
        self._ui.bodyList.itemDoubleClicked.connect(self._editBody)
        self._ui.addBodyButton.clicked.connect(self._addBody)

    def showEvent(self, ev):
        if not ev.spontaneous():
            self._updatePage()

        return super().showEvent(ev)

    @qasync.asyncSlot()
    async def save(self):
        if self._dynamicMesh.motionType == MotionType.RIGID_BODY_DYNAMICS:
            try:
                solverType = self._ui.rbdSolverCombo.currentData()
                if solverType == RigidBodyDynamicsSolverType.NEWMARK:
                    vic = self._ui.rbdVelCoeff.pFloat(self.tr('Velocity Integration Coefficient'))
                    pic = self._ui.rbdPosCoeff.pFloat(self.tr('Position Integration Coefficient'))

                elif solverType == RigidBodyDynamicsSolverType.CRANK_NICOLSON:
                    oac = self._ui.rbdAccOffCoeff.pFloat(self.tr('Acceleration Off-centering Coefficient'))
                    ovc = self._ui.rbdVelOffCoeff.pFloat(self.tr('Velocity Off-centering Coefficient'))

                relaxation = self._ui.rbdRelaxation.pFloat(self.tr('Acceleration Relaxation Factor'))
                damping = self._ui.rbdDamping.pFloat(self.tr('Acceleration Damping Factor'))

            except ValueError as e:
                await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
                return False

            rbd = self._dynamicMesh.rigidBodyDynamics
            solver = rbd.solver

            solver.solverType = solverType

            if solverType == RigidBodyDynamicsSolverType.NEWMARK:
                solver.velocityIntegrationCoefficient = vic
                solver.positionIntegrationCoefficient = pic

            elif solver.solverType == RigidBodyDynamicsSolverType.CRANK_NICOLSON:
                solver.offCenteringAccelerationCoefficient = oac
                solver.offCenteringVelocityCoefficient = ovc

            rbd.accelerationRelaxationFactor = relaxation
            rbd.accelerationDampingFactor = damping


        return True

    def _updatePage(self):
        mt = self._dynamicMesh.motionType
        self._ui.motionTypeLabel.setText(MOTION_TYPE_NAMES[mt])
        if mt == MotionType.NONE:
            self._ui.stack.setCurrentWidget(self._ui.nonePage)
        elif mt == MotionType.MOVING_CELL_ZONE:
            self._ui.stack.setCurrentWidget(self._ui.movingCellZonePage)
            self._updateMotionDefinitions()
        elif mt == MotionType.MOVING_BOUNDARY:
            self._ui.stack.setCurrentWidget(self._ui.movingBoundaryPage)
            self._updateMovingBoundaries()
        elif mt == MotionType.RIGID_BODY_DYNAMICS:
            self._ui.stack.setCurrentWidget(self._ui.rigidBodyDynamicsPage)
            self._updateRigidBodyDynamics()

    def _changeMotionType(self):
        self._dialog = MotionTypeDialog(self, self._dynamicMesh.motionType)
        self._dialog.accepted.connect(self._motionTypeChanged)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _motionTypeChanged(self):
        newType = self._dialog.selectedType
        if newType == self._dynamicMesh.motionType:
            return

        confirm = await AsyncMessageBox().question(
            self, self.tr('Warning'),
            self.tr('Changing Motion Type will clear current configuration.\nContinue?'))
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._dynamicMesh.motionType=newType

        self._updatePage()

    # ── Moving Cell Zone ──

    def _updateMotionDefinitions(self):
        self._ui.mdList.clear()
        for md in self._dynamicMesh.motionDefinitions:
            self._addMdItem(md)

    def _addMotionDefinition(self):
        order = len(self._dynamicMesh.motionDefinitions) + 1
        existingNames = {md.name for md in self._dynamicMesh.motionDefinitions}
        n = order
        while f'Motion-{n}' in existingNames:
            n += 1
        md = MotionDefinition(name=f'Motion-{n}', order=order)
        self._dialog = MotionDefinitionDialog(self, md, existingNames)
        self._dialog.accepted.connect(lambda: self._motionDefinitionAdded(md))
        self._dialog.open()

    def _motionDefinitionAdded(self, md):
        self._dynamicMesh.motionDefinitions.append(md)
        self._addMdItem(md)

    def _addMdItem(self, md: MotionDefinition):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)
        nameLabel = QLabel(f'<b>{md.name}</b>')
        czText = ', '.join(CellZoneDB.getCellZoneText(z) for z in md.cellZones) if md.cellZones else self.tr('Entire Domain')
        czLabel = QLabel(czText)
        czLabel.setStyleSheet('color:grey')
        layout.addWidget(nameLabel)
        layout.addWidget(czLabel)
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 48))
        item.setData(Qt.ItemDataRole.UserRole, md.uuid)
        self._ui.mdList.addItem(item)
        self._ui.mdList.setItemWidget(item, widget)

    def _showMdContextMenu(self, pos):
        row = self._ui.mdList.currentRow()
        if row < 0:
            return
        menu = QMenu(self.window())
        if row > 0:
            menu.addAction(self.tr('Move Up')).triggered.connect(lambda: self._moveMd(row, row - 1))
        if row < self._ui.mdList.count() - 1:
            menu.addAction(self.tr('Move Down')).triggered.connect(lambda: self._moveMd(row, row + 1))
        menu.addAction(self.tr('Edit')).triggered.connect(self._editMotionDefinition)
        menu.addAction(self.tr('Remove')).triggered.connect(self._removeMd)
        menu.exec(self._ui.mdList.mapToGlobal(pos))

    def _moveMd(self, fromRow, toRow):
        mds = self._dynamicMesh.motionDefinitions
        mds[fromRow], mds[toRow] = mds[toRow], mds[fromRow]
        self._updateMotionDefinitions()
        self._ui.mdList.setCurrentRow(toRow)

    def _editMotionDefinition(self):
        row = self._ui.mdList.currentRow()
        if row < 0:
            return
        md = self._dynamicMesh.motionDefinitions[row]
        existingNames = {m.name for m in self._dynamicMesh.motionDefinitions if m is not md}
        self._dialog = MotionDefinitionDialog(self, md, existingNames)
        self._dialog.accepted.connect(self._updateMotionDefinitions)
        self._dialog.open()

    def _removeMd(self):
        row = self._ui.mdList.currentRow()
        if row >= 0:
            del self._dynamicMesh.motionDefinitions[row]
            self._ui.mdList.takeItem(row)

    # ── Moving Boundary ──

    def _updateMovingBoundaries(self):
        self._ui.mbList.clear()
        for entry in self._dynamicMesh.movingBoundaries:
            self._addMbItem(entry)

    def _addMbItem(self, entry: MovingBoundaryEntry):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)

        name = BoundaryDB.getBoundaryName(entry.boundary)
        nameLabel = QLabel(name)

        bctype = BoundaryDB.getBoundaryType(entry.boundary)
        constrained = bctype in CONSTRAINT_BOUNDARY_TYPE_MAP

        if constrained:
            summary = POINT_MOTION_TYPE_NAMES.get(CONSTRAINT_BOUNDARY_TYPE_MAP[bctype], '')
        else:
            summary = POINT_MOTION_TYPE_NAMES.get(entry.pointMotionType, '')
            if entry.useFixedNormal:
                summary = f'Fixed Normal {entry.normal} Slip'
        summaryLabel = QLabel(f'<b>{summary}</b>')

        layout.addWidget(nameLabel, 1)
        layout.addWidget(summaryLabel)

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 40))
        item.setData(Qt.ItemDataRole.UserRole, entry.uuid)
        if constrained:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsSelectable)
            widget.setEnabled(False)
        self._ui.mbList.addItem(item)
        self._ui.mbList.setItemWidget(item, widget)

    def _editBoundary(self):
        item = self._ui.mbList.currentItem()
        if item is None:
            return
        uuid = item.data(Qt.ItemDataRole.UserRole)
        entry = next(mb for mb in self._dynamicMesh.movingBoundaries if mb.uuid == uuid)
        self._dialog = PointMotionDialog(self, entry)
        self._dialog.accepted.connect(self._updateMovingBoundaries)
        self._dialog.open()

    # ── Rigid Body Dynamics ──

    def _updateRigidBodyDynamics(self):
        rbd = self._dynamicMesh.rigidBodyDynamics

        # Solver
        idx = self._ui.rbdSolverCombo.findData(rbd.solver.solverType)
        if idx >= 0:
            self._ui.rbdSolverCombo.setCurrentIndex(idx)
        self._ui.rbdVelCoeff.setPFloat(rbd.solver.velocityIntegrationCoefficient)
        self._ui.rbdPosCoeff.setPFloat(rbd.solver.positionIntegrationCoefficient)
        self._ui.rbdAccOffCoeff.setPFloat(rbd.solver.offCenteringAccelerationCoefficient)
        self._ui.rbdVelOffCoeff.setPFloat(rbd.solver.offCenteringVelocityCoefficient)

        self._ui.rbdRelaxation.setPFloat(rbd.accelerationRelaxationFactor)
        self._ui.rbdDamping.setPFloat(rbd.accelerationDampingFactor)

        # Bodies
        self._ui.bodyList.clear()
        for body in rbd.bodies:
            self._addBodyItem(body)

    def _rbdSolverChanged(self, index):
        solverType = self._ui.rbdSolverCombo.itemData(index)
        if solverType == RigidBodyDynamicsSolverType.NEWMARK:
            self._ui.rbdSolverStack.setCurrentIndex(0)
        elif solverType == RigidBodyDynamicsSolverType.CRANK_NICOLSON:
            self._ui.rbdSolverStack.setCurrentIndex(1)
        elif solverType == RigidBodyDynamicsSolverType.SYMPLECTIC:
            self._ui.rbdSolverStack.setCurrentIndex(2)
        else:
            self._ui.rbdSolverStack.setCurrentIndex(2)

    def _addBodyItem(self, body: Body):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        nameLabel = QLabel(f'<b>{body.name}</b>')
        massLabel = QLabel(f'{body.mass} kg')
        massLabel.setStyleSheet('color:grey')
        layout.addWidget(nameLabel, 1)
        layout.addWidget(massLabel)
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 40))
        item.setData(Qt.ItemDataRole.UserRole, body.uuid)
        self._ui.bodyList.addItem(item)
        self._ui.bodyList.setItemWidget(item, widget)
        self._ui.bodyList.updateGeometry()

    def _showBodyContextMenu(self, pos):
        row = self._ui.bodyList.currentRow()
        if row < 0:
            return
        menu = QMenu(self.window())
        menu.addAction(self.tr('Edit')).triggered.connect(self._editBody)
        menu.addAction(self.tr('Remove')).triggered.connect(self._removeBody)
        menu.exec(self._ui.bodyList.mapToGlobal(pos))

    def _addBody(self):
        existingBodies = [(b.uuid, b.name) for b in self._dynamicMesh.rigidBodyDynamics.bodies]
        existingNames = {b.name for b in self._dynamicMesh.rigidBodyDynamics.bodies}
        n = len(existingBodies) + 1
        while f'Body-{n}' in existingNames:
            n += 1
        body = Body(uuid=uuid4(), name=f'Body-{n}', parent=UUID(int=0))
        self._dialog = BodyDialog(self, body, existingBodies)
        self._dialog.accepted.connect(lambda: self._bodyAdded(body))
        self._dialog.open()

    def _bodyAdded(self, body):
        self._dynamicMesh.rigidBodyDynamics.bodies.append(body)
        self._addBodyItem(body)

    def _editBody(self):
        row = self._ui.bodyList.currentRow()
        if row < 0:
            return
        body = self._dynamicMesh.rigidBodyDynamics.bodies[row]
        existingBodies = [(b.uuid, b.name) for b in self._dynamicMesh.rigidBodyDynamics.bodies]
        self._dialog = BodyDialog(self, body, existingBodies)
        self._dialog.accepted.connect(self._updateRigidBodyDynamics)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _removeBody(self):
        row = self._ui.bodyList.currentRow()
        if row < 0:
            return

        body = self._dynamicMesh.rigidBodyDynamics.bodies[row]

        # Check if body is used as parent
        for b in self._dynamicMesh.rigidBodyDynamics.bodies:
            if b.parent == body.uuid:
                await AsyncMessageBox().warning(
                    self, self.tr('Warning'),
                    self.tr('Cannot remove body that is used as a parent.'))
                return

        confirm = await AsyncMessageBox().question(
            self, self.tr('Remove Body'),
            self.tr('Remove "{0}"?').format(body.name))
        if confirm == QMessageBox.StandardButton.Yes:
            del self._dynamicMesh.rigidBodyDynamics.bodies[row]
            self._ui.bodyList.takeItem(row)
            self._ui.bodyList.updateGeometry()

