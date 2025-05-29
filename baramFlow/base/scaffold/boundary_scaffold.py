#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from dataclasses import field as dataClassField
from uuid import UUID

from lxml import etree
from vtkmodules.vtkCommonDataModel import vtkMultiBlockDataSet, vtkPolyData

from baramFlow.coredb import coredb
from baramFlow.coredb.boundary_db import BoundaryDB
from baramFlow.coredb.libdb import nsmap
from baramFlow.base.scaffold.scaffold import Scaffold
from libbaram.openfoam.polymesh import collectBoundaryMesh


@dataclass
class BoundaryScaffold(Scaffold):
    boundaries: list[str] = dataClassField(default_factory=list)
    _boundaryNames: list[str] = dataClassField(init=False, repr=False)

    def __setattr__(self, name: str, value):
        if (name == "boundaries"):
            # Boundary names are preserved.
            # The names are used to rematch the boundaries to the new bcid after mesh importing.
            super().__setattr__('_boundaryNames',  [BoundaryDB.getBoundaryText(bcid) for bcid in value])
        super().__setattr__(name, value)

    @classmethod
    def parseScaffolds(cls) -> dict[UUID, Scaffold]:
        scaffolds: dict[UUID, Scaffold] = {}

        for e in coredb.CoreDB().getElements(Scaffold.SCAFFOLDS_PATH + '/boundaries/boundary'):
            s = BoundaryScaffold.fromElement(e)
            scaffolds[s.uuid] = s

        return scaffolds

    @classmethod
    def fromElement(cls, e):
        uuid = UUID(e.find('uuid', namespaces=nsmap).text)
        name = e.find('name', namespaces=nsmap).text
        boundaries = e.find('boundaries', namespaces=nsmap).text.split()

        return BoundaryScaffold(uuid=uuid,
                          name=name,
                          boundaries=boundaries)

    def toElement(self):
        string = ('<boundary xmlns="http://www.baramcfd.org/baram">'
                 f'    <uuid>{str(self.uuid)}</uuid>'
                 f'    <name>{self.name}</name>'
                 f'    <boundaries>{" ".join(self.boundaries)}</boundaries>'
                  '</boundary>')

        return etree.fromstring(string)

    def xpath(self):
        return f'/boundary[uuid="{str(self.uuid)}"]'

    def addElement(self):
        coredb.CoreDB().addElement(Scaffold.SCAFFOLDS_PATH + '/boundaries', self.toElement())

    def removeElement(self):
        coredb.CoreDB().removeElement(Scaffold.SCAFFOLDS_PATH + '/boundaries' + self.xpath())

    async def getDataSet(self, mBlock: vtkMultiBlockDataSet) -> vtkPolyData:
        boundaries: list[tuple[str, str]] = []

        for bcid in self.boundaries:
            rname = BoundaryDB.getBoundaryRegion(bcid)
            bcname = BoundaryDB.getBoundaryName(bcid)

            boundaries.append((rname, bcname))

        return await collectBoundaryMesh(mBlock, boundaries)

    def rematchBoundaries(self):
        bcids: dict[str, str] = {}
        db = coredb.CoreDB()
        for rname in db.getRegions():
            boundaries = db.getBoundaryConditions(rname)
            for id_, _, _ in boundaries:
                bcid = str(id_)
                bcids[BoundaryDB.getBoundaryText(bcid)] = bcid

        boundaries = []
        for name in self._boundaryNames:
            if name in bcids:
                boundaries.append(bcids[name])

        if len(boundaries) > 0:
            self.boundaries = boundaries
        else:  # put all boundaries if no matching boundaries are found
            self.boundaries = list(bcids.values())
