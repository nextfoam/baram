from baramFlow.coredb.libdb import nsmap
from baramFlow.coredb.scaffold import ScaffoldType


from PySide6.QtGui import QColor
from lxml import etree


from dataclasses import dataclass
from uuid import UUID


@dataclass
class ReportingScaffold:
    type_: ScaffoldType
    boundary: int = 0
    scaffold: UUID  = UUID(int = 0)

    visibility: bool = False
    opacity: int = 100
    solidColor: bool = False
    color: QColor = QColor.fromString('#FFFFFF')
    edges: bool = False
    faces: bool = True

    @classmethod
    def fromElement(cls, e):
        type_ = ScaffoldType(e.find('type', namespaces=nsmap).text)
        boundary = int(e.find('boundary', namespaces=nsmap).text)
        scaffold = UUID(e.find('scaffoldUuid', namespaces=nsmap).text)
        visibility = (e.find('visibility', namespaces=nsmap).text == 'true')
        opacity = int(e.find('opacity', namespaces=nsmap).text)
        solidColor = (e.find('solidColor', namespaces=nsmap).text == 'true')
        color = QColor.fromString(e.find('color', namespaces=nsmap).text)
        edges = (e.find('edges', namespaces=nsmap).text == 'true')
        faces = (e.find('faces', namespaces=nsmap).text == 'true')


        return ReportingScaffold(type_=type_,
                          boundary=boundary,
                          scaffold=scaffold,
                          visibility=visibility,
                          opacity=opacity,
                          solidColor=solidColor,
                          color=color,
                          edges=edges,
                          faces=faces)

    def toElement(self):
        string = (f'<saffold>'
                  f'    <type>{self.type_.value}</type>'
                  f'    <boundary>{self.boundary}</boundary>'
                  f'    <scaffoldUuid>{str(self.scaffold)}</scaffoldUuid>'
                  f'    <visibility>{"true" if self.visibility else "false"}</visibility>'
                  f'    <opacity>{str(self.opacity)}</opacity>'
                  f'    <solidColor>{"true" if self.solidColor else "false"}</solidColor>'
                  f'    <color>{self.color.name()}</color>'
                  f'    <edges>{"true" if self.edges else "false"}</edges>'
                  f'    <faces>{"true" if self.faces else "false"}</faces>'
                  f'</scaffold>')

        return etree.fromstring(string)