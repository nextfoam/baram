from typing import ClassVar

from PySide6.QtCore import QObject, Signal
from baramFlow.coredb.libdb import nsmap

from PySide6.QtGui import QColor
from lxml import etree


from dataclasses import dataclass
from uuid import UUID


@dataclass
class ReportingScaffold(QObject):
    instanceUpdated: ClassVar[Signal] = Signal(UUID)

    scaffoldUuid: UUID  = UUID(int = 0)

    visibility: bool = False
    opacity: int = 100
    solidColor: bool = False
    color: QColor = QColor.fromString('#FFFFFF')
    edges: bool = False
    faces: bool = True
    showVectors: bool = False

    def __post_init__(self):
        super().__init__()

    @classmethod
    def fromElement(cls, e):
        scaffoldUuid = UUID(e.find('scaffoldUuid', namespaces=nsmap).text)
        visibility = (e.find('visibility', namespaces=nsmap).text == 'true')
        opacity = int(e.find('opacity', namespaces=nsmap).text)
        solidColor = (e.find('solidColor', namespaces=nsmap).text == 'true')
        color = QColor.fromString(e.find('color', namespaces=nsmap).text)
        edges = (e.find('edges', namespaces=nsmap).text == 'true')
        faces = (e.find('faces', namespaces=nsmap).text == 'true')
        showVectors = (e.find('showVectors', namespaces=nsmap).text == 'true')


        return ReportingScaffold(scaffoldUuid=scaffoldUuid,
                          visibility=visibility,
                          opacity=opacity,
                          solidColor=solidColor,
                          color=color,
                          edges=edges,
                          faces=faces,
                          showVectors=showVectors)

    def toElement(self):
        string = (f'<scaffold>'
                  f'    <scaffoldUuid>{str(self.scaffoldUuid)}</scaffoldUuid>'
                  f'    <visibility>{"true" if self.visibility else "false"}</visibility>'
                  f'    <opacity>{str(self.opacity)}</opacity>'
                  f'    <solidColor>{"true" if self.solidColor else "false"}</solidColor>'
                  f'    <color>{self.color.name()}</color>'
                  f'    <edges>{"true" if self.edges else "false"}</edges>'
                  f'    <faces>{"true" if self.faces else "false"}</faces>'
                  f'    <showVectors>{"true" if self.showVectors else "false"}</showVectors>'
                  f'</scaffold>')

        return etree.fromstring(string)

    def markUpdated(self):
        self.instanceUpdated.emit(self.scaffoldUuid)
