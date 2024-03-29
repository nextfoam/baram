#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget


class EmptyPage(QWidget):
    def __init__(self, ui):
        super().__init__()
        self._ui = ui

        # db = coredb.CoreDB()
        # db.addRegion("region1")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "velocityInlet", "patch")) + '/physicalType', "velocityInlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "flowRateInlet", "patch")) + '/physicalType', "flowRateInlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "pressureInlet", "patch")) + '/physicalType', "pressureInlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "pressureOutlet", "patch")) + '/physicalType', "pressureOutlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "ablInlet", "patch")) + '/physicalType', "ablInlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "openChannelInlet", "patch")) + '/physicalType', "openChannelInlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "openChannelOutlet", "patch")) + '/physicalType', "openChannelOutlet")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "outflow", "patch")) + '/physicalType', "outflow")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "freeStream", "patch")) + '/physicalType', "freeStream")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "farFieldRiemann", "patch")) + '/physicalType', "farFieldRiemann")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "subsonicInflow", "patch")) + '/physicalType', "subsonicInflow")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "subsonicOutflow", "patch")) + '/physicalType', "subsonicOutflow")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "supersonicInflow", "patch")) + '/physicalType', "supersonicInflow")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "supersonicOutflow", "patch")) + '/physicalType', "supersonicOutflow")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "wall", "patch")) + '/physicalType', "wall")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "thermoCoupledWall", "patch")) + '/physicalType', "thermoCoupledWall")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "symmetry", "patch")) + '/physicalType', "symmetry")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "interface", "patch")) + '/physicalType', "interface")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "porousJump", "patch")) + '/physicalType', "porousJump")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "fan", "patch")) + '/physicalType', "fan")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "empty", "patch")) + '/physicalType', "empty")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "cyclic", "patch")) + '/physicalType', "cyclic")
        # db.setValue(BoundaryDB.getXPath(db.addBoundaryCondition("region1", "wedge", "patch")) + '/physicalType', "wedge")
