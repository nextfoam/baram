#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy
from uuid import UUID, uuid4

from PySide6.QtCore import QSize
import qasync

from PySide6.QtWidgets import QDialog, QMenu, QListWidgetItem

from baramFlow.base.dynamic_mesh.restraint import Restraint, RestraintType
from baramFlow.base.dynamic_mesh.rigid_body_dynamics import Body, Joint, JointType
from baramFlow.base.event_bus import EventBus
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.view.setup.dynamic_mesh.restraints.restraint_dialogs import RESTRAINT_DIALOGS, RotationalSpringDialog
from baramFlow.view.setup.dynamic_mesh.restraints.restraint_widget import RESTRAINT_TYPE_NAMES, RestraintWidget
from baramFlow.view.setup.dynamic_mesh.rigid_body_dynamics.joint_widget import JointWidget, JOINT_TYPE_NAMES
from baramFlow.view.setup.dynamic_mesh.rigid_body_dynamics.joint_dialogs import JOINT_DIALOGS
from baramFlow.view.widgets.multi_selector_dialog import MultiSelectorDialog
from libbaram.pfloat import PFloat
from widgets.async_message_box import AsyncMessageBox

from .body_dialog_ui import Ui_BodyDialog


class BodyDialog(QDialog):
    NONE_UUID = UUID(int=0)

    def __init__(self, parent, body: Body, existingBodies: list[tuple[UUID, str]]):
        """
        existingBodies: list of (uuid, name) tuples for all bodies except this one,
                        used for parent selection.
        """
        super().__init__(parent)

        self._ui = Ui_BodyDialog()
        self._ui.setupUi(self)

        self._body = body
        self._joints = [deepcopy(j) for j in body.joints]
        self._restraints = [deepcopy(r) for r in body.restraints]
        self._boundaries = list(body.boundaries)
        self._existingNames = {bName for bUuid, bName in existingBodies if bUuid != body.uuid}
        self._dialog = None

        # Name and Parent
        self._ui.name.setText(body.name)
        self._ui.parentCombo.addItem(self.tr('None'), self.NONE_UUID)
        for bUuid, bName in existingBodies:
            if bUuid != body.uuid:
                self._ui.parentCombo.addItem(bName, bUuid)
        idx = self._ui.parentCombo.findData(body.parent)
        if idx >= 0:
            self._ui.parentCombo.setCurrentIndex(idx)

        # Mass Properties
        self._ui.mass.setPFloat(body.mass)
        self._ui.com.setVector(body.centerOfMass)
        self._ui.localOrigin.setVector(body.localOrigin)

        # Orientation Tensor
        oriEdits = [
            [self._ui.ori00, self._ui.ori01, self._ui.ori02],
            [self._ui.ori10, self._ui.ori11, self._ui.ori12],
            [self._ui.ori20, self._ui.ori21, self._ui.ori22],
        ]
        for i in range(3):
            for j in range(3):
                oriEdits[i][j].setPFloat(body.orientation[i * 3 + j])

        # Moment of Inertia Tensor

        self._ui.moi00.setPFloat(body.momentOfInertia[0])
        self._ui.moi01.setPFloat(body.momentOfInertia[1])
        self._ui.moi02.setPFloat(body.momentOfInertia[2])
        self._ui.moi11.setPFloat(body.momentOfInertia[3])
        self._ui.moi12.setPFloat(body.momentOfInertia[4])
        self._ui.moi22.setPFloat(body.momentOfInertia[5])

        # Mesh Deformation
        self._ui.deformationOffset.setPFloat(body.deformationOffset)
        self._ui.deformationDistance.setPFloat(body.deformationDistance)

        # Add Joint menu
        jointMenu = QMenu(self._ui.addJointButton)
        for jt in JointType:
            action = jointMenu.addAction(JOINT_TYPE_NAMES[jt])
            action.triggered.connect(lambda checked=False, jtype=jt: self._addJoint(jtype))
        self._ui.addJointButton.setMenu(jointMenu)

        # Add Restraint menu
        restraintMenu = QMenu(self._ui.addRestraintButton)
        for rt in RestraintType:
            action = restraintMenu.addAction(RESTRAINT_TYPE_NAMES[rt])
            action.triggered.connect(lambda checked=False, rtype=rt: self._addRbdRestraint(rtype))
        self._ui.addRestraintButton.setMenu(restraintMenu)

        self._setBoundaries(self._boundaries)
        self._connectSignalsSlots()
        self._loadJoints()
        self._loadRbdRestraints()

    def _connectSignalsSlots(self):
        self._ui.selectBoundariesButton.clicked.connect(self._selectBoundariesClicked)
        self._ui.jointList.customContextMenuRequested.connect(self._showJointContextMenu)
        self._ui.jointList.itemDoubleClicked.connect(self._editJoint)
        self._ui.rbdRestraintList.customContextMenuRequested.connect(self._showRbdRestraintMenu)
        self._ui.rbdRestraintList.itemDoubleClicked.connect(self._editRbdRestraint)
        self._ui.buttonBox.accepted.connect(self._accept)
        self._ui.buttonBox.rejected.connect(self.reject)

    @qasync.asyncSlot()
    async def _selectBoundariesClicked(self):
        boundaries = BoundaryDB.getBoundarySelectorItems()
        self._dialog = MultiSelectorDialog(self, self.tr("Select Boundaries"), boundaries, self._boundaries)
        self._dialog.accepted.connect(self._boundariesChanged)
        self._dialog.open()

    @qasync.asyncSlot()
    async def _boundariesChanged(self):
        self._setBoundaries(self._dialog.selectedItems())

    def _setBoundaries(self, boundaries):
        self._boundaries = boundaries
        self._ui.boundariesList.clear()
        for bcid in boundaries:
            self._ui.boundariesList.addItem(BoundaryDB.getBoundaryText(bcid))

    def _loadJoints(self):
        self._ui.jointList.clear()
        for j in self._joints:
            self._addJointItem(j)

    def _addJoint(self, jointType: JointType):
        joint = Joint(jointType=jointType)
        dialogClass = JOINT_DIALOGS.get(jointType)
        if dialogClass:
            self._dialog = dialogClass(self, joint)
            self._dialog.accepted.connect(lambda: self._jointAdded(joint))
            self._dialog.open()
        else:
            # Spherical has no dialog, just add directly
            self._jointAdded(joint)

    def _jointAdded(self, joint):
        self._joints.append(joint)
        self._addJointItem(joint)

    def _addJointItem(self, joint: Joint):
        widget = JointWidget(joint)
        item = QListWidgetItem()
        item.setSizeHint(widget.size())
        self._ui.jointList.addItem(item)
        self._ui.jointList.setItemWidget(item, widget)

    def _showJointContextMenu(self, pos):
        row = self._ui.jointList.currentRow()
        if row < 0:
            return
        menu = QMenu(self)
        if row > 0:
            menu.addAction(self.tr('Move Up')).triggered.connect(lambda: self._moveJoint(row, row - 1))
        if row < self._ui.jointList.count() - 1:
            menu.addAction(self.tr('Move Down')).triggered.connect(lambda: self._moveJoint(row, row + 1))
        joint = self._joints[row]
        if joint.jointType != JointType.SPHERICAL:
            menu.addAction(self.tr('Edit')).triggered.connect(self._editJoint)
        menu.addAction(self.tr('Remove')).triggered.connect(self._removeJoint)
        menu.exec(self._ui.jointList.mapToGlobal(pos))

    def _moveJoint(self, fromRow, toRow):
        self._joints[fromRow], self._joints[toRow] = self._joints[toRow], self._joints[fromRow]
        self._loadJoints()
        self._ui.jointList.setCurrentRow(toRow)

    def _editJoint(self):
        row = self._ui.jointList.currentRow()
        if row < 0:
            return
        joint = self._joints[row]
        dialogClass = JOINT_DIALOGS.get(joint.jointType)
        if dialogClass:
            self._dialog = dialogClass(self, joint)
            self._dialog.accepted.connect(lambda: self._jointEdited(row))
            self._dialog.open()

    def _jointEdited(self, row):
        widget = self._ui.jointList.itemWidget(self._ui.jointList.item(row))
        if isinstance(widget, JointWidget):
            widget.load()

    def _removeJoint(self):
        row = self._ui.jointList.currentRow()
        if row >= 0:
            del self._joints[row]
            self._ui.jointList.takeItem(row)

    def _loadRbdRestraints(self):
        self._ui.rbdRestraintList.clear()
        for r in self._restraints:
            self._addRbdRestraintItem(r)

    def _addRbdRestraint(self, restraintType: RestraintType):
        order = self._ui.rbdRestraintList.count() + 1
        restraint = Restraint(uuid=uuid4(), order=order, restraintType=restraintType)
        dialogClass = RESTRAINT_DIALOGS.get(restraintType)
        if dialogClass:
            if dialogClass is RotationalSpringDialog:
                self._dialog = dialogClass(self, restraint, showOrientation=False)
            else:
                self._dialog = dialogClass(self, restraint)
            self._dialog.accepted.connect(lambda: self._rbdRestraintAdded(restraint))
            self._dialog.open()
        else:
            self._rbdRestraintAdded(restraint)

    def _rbdRestraintAdded(self, restraint):
        self._restraints.append(restraint)
        self._addRbdRestraintItem(restraint)

    def _addRbdRestraintItem(self, restraint: Restraint):
        widget = RestraintWidget(restraint)
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 48))
        self._ui.rbdRestraintList.addItem(item)
        self._ui.rbdRestraintList.setItemWidget(item, widget)
        #self._ui.rbdRestraintList.updateGeometry()

    def _showRbdRestraintMenu(self, pos):
        row = self._ui.rbdRestraintList.currentRow()
        if row < 0:
            return
        menu = QMenu(self)
        if row > 0:
            menu.addAction(self.tr('Move Up')).triggered.connect(
                lambda: self._moveRbdRestraint(row, row - 1))
        if row < self._ui.rbdRestraintList.count() - 1:
            menu.addAction(self.tr('Move Down')).triggered.connect(
                lambda: self._moveRbdRestraint(row, row + 1))
        menu.addAction(self.tr('Edit')).triggered.connect(self._editRbdRestraint)
        menu.addAction(self.tr('Remove')).triggered.connect(self._removeRbdRestraint)
        menu.exec(self._ui.rbdRestraintList.mapToGlobal(pos))

    def _moveRbdRestraint(self, fromRow, toRow):
        self._restraints[fromRow], self._restraints[toRow] = self._restraints[toRow], self._restraints[fromRow]
        self._loadRbdRestraints()
        self._ui.rbdRestraintList.setCurrentRow(toRow)

    def _editRbdRestraint(self):
        row = self._ui.rbdRestraintList.currentRow()
        if row < 0:
            return
        restraint = self._restraints[row]
        dialogClass = RESTRAINT_DIALOGS.get(restraint.restraintType)
        if dialogClass:
            if dialogClass is RotationalSpringDialog:
                self._dialog = dialogClass(self, restraint, showOrientation=False)
            else:
                self._dialog = dialogClass(self, restraint)
            self._dialog.accepted.connect(lambda: self._rbdRestraintEdited(row))
            self._dialog.open()

    def _rbdRestraintEdited(self, row):
        widget = self._ui.rbdRestraintList.itemWidget(self._ui.rbdRestraintList.item(row))
        if isinstance(widget, RestraintWidget):
            widget.load()

    def _removeRbdRestraint(self):
        row = self._ui.rbdRestraintList.currentRow()
        if row >= 0:
            del self._restraints[row]
            self._ui.rbdRestraintList.takeItem(row)
            #self._ui.rbdRestraintList.updateGeometry()

    @qasync.asyncSlot()
    async def _accept(self):
        name = self._ui.name.text()
        if name in self._existingNames:
            await AsyncMessageBox().warning(self, self.tr('Warning'),
                                            self.tr('The name "{0}" is already in use.').format(name))
            return

        if not self._boundaries:
            await AsyncMessageBox().warning(self, self.tr('Warning'),
                                            self.tr('At least one boundary must be selected.'))
            return

        try:
            mass = PFloat(self._ui.mass.text(), self.tr('Mass'), low=0, lowInclusive=False)
            centerOfMass = self._ui.com.vector('Center of Mass')
            localOrigin = self._ui.localOrigin.vector('Local Origin')

            oriEdits = [
                [self._ui.ori00, self._ui.ori01, self._ui.ori02],
                [self._ui.ori10, self._ui.ori11, self._ui.ori12],
                [self._ui.ori20, self._ui.ori21, self._ui.ori22],
            ]
            orientation: list[PFloat] = []
            for i in range(3):
                for j in range(3):
                    orientation.append(oriEdits[i][j].pFloat(self.tr('Orientation')))

            momentOfInertia = [
                self._ui.moi00.pFloat(self.tr('Moment of Inertia')),
                self._ui.moi01.pFloat(self.tr('Moment of Inertia')),
                self._ui.moi02.pFloat(self.tr('Moment of Inertia')),
                self._ui.moi11.pFloat(self.tr('Moment of Inertia')),
                self._ui.moi12.pFloat(self.tr('Moment of Inertia')),
                self._ui.moi22.pFloat(self.tr('Moment of Inertia'))
            ]

            deformationOffset = self._ui.deformationOffset.pFloat(self.tr('Deformation Offset'), low=0)
            deformationDistance = self._ui.deformationDistance.pFloat(self.tr('Deformation Distance'), low=0)
        except ValueError as e:
            await AsyncMessageBox().warning(self, self.tr('Warning'), str(e))
            return

        self._body.name = name
        self._body.parent = self._ui.parentCombo.currentData()
        self._body.mass = mass
        self._body.centerOfMass = centerOfMass
        self._body.localOrigin = localOrigin
        self._body.orientation = orientation
        self._body.momentOfInertia = momentOfInertia
        self._body.boundaries = self._boundaries
        self._body.joints = self._joints
        self._body.restraints = self._restraints
        self._body.deformationOffset = deformationOffset
        self._body.deformationDistance = deformationDistance

        EventBus().onConfigChanged.emit()

        self.accept()
