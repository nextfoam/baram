#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
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
    boundaries: list[str] = field(default_factory=list)

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
