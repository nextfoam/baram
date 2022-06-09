#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget

from coredb import coredb


class EmptyPage(QWidget):
    def __init__(self, ui):
        super().__init__()
        self._ui = ui

        db = coredb.CoreDB()
        db.addRegion("region1")
        db.addRegion("region2")
        db.addCellZone("region1", "zone1-1")
        db.addCellZone("region1", "zone1-2")
        db.addCellZone("region2", "zone2-1")
        db.addCellZone("region2", "zone2-2")
        db.addBoundaryCondition("region1", "boundary1-1", "cyclic")
        db.addBoundaryCondition("region1", "boundary1-2", "patch")
        db.addBoundaryCondition("region2", "boundary2-1", "empty")
        db.addBoundaryCondition("region2", "boundary2-2", "processor")
