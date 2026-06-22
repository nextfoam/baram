#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from uuid import uuid4, UUID

from pandas import DataFrame

from libbaram.natural_name_uuid import uuidToNnstr

from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.coredb import _CoreDB
from baramFlow.coredb.project import Project


class FileDataManager:
    _dataFrames: dict[str, DataFrame] = {}

    @classmethod
    def putDataFrame(cls, data: DataFrame):
        id_ = uuid4()
        name = uuidToNnstr(id_)
        Project.instance().fileDB().putDataFrame(name, data)
        cls._dataFrames[name] = data

        return id_


@dataclass
class TableDataForFileDB:
    data: list[list[float]] = None
    name: UUID              = None

    def applyToDB(self, db: _CoreDB, bcid: str):
        if self.data is not None:
            self.name = FileDataManager.putDataFrame(DataFrame(self.data))
            db.setValue(BoundaryDB.getXPath(bcid) + '/fanCurveName', str(self.name))
