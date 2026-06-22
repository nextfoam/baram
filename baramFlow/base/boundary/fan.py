#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from baramFlow.base.file_data_manager import TableDataForFileDB
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import boolToXml


@dataclass
class Fan:
    reverseDirection: bool          = False
    fanCurve: TableDataForFileDB    = None

    def applyToDB(self, db, bcid):
        self.applyCoupleConditionToDB(db, bcid)

        if self.fanCurve is not None:
            self.fanCurve.applyToDB(db, bcid)

    def applyCoupleConditionToDB(self, db, bcid):
        xpath = BoundaryDB.getXPath(bcid)

        db.setValue(xpath + '/fan/reverseDirection', boolToXml(self.reverseDirection))
        if self.fanCurve is not None:
            self.fanCurve.applyToDB(db, bcid)
