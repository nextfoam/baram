#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock

from lxml import etree
import xmlschema
import h5py
import pandas as pd

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from resources import resource

ns = 'http://www.example.org/baram'
nsmap = {'': ns}

_mutex = Lock()


class CoreDB(object):
    CONFIGURATION_ROOT = 'configurations'
    XSD_PATH = f'{CONFIGURATION_ROOT}/baram.cfg.xsd'
    XML_PATH = f'{CONFIGURATION_ROOT}/baram.cfg.xml'

    CELL_ZONE_PATH = f'{CONFIGURATION_ROOT}/cell_zone.xml'
    BOUNDARY_CONDITION_PATH = f'{CONFIGURATION_ROOT}/boundary_condition.xml'

    FORCE_MONITOR_PATH   = f'{CONFIGURATION_ROOT}/force_monitor.xml'
    POINT_MONITOR_PATH   = f'{CONFIGURATION_ROOT}/point_monitor.xml'
    SURFACE_MONITOR_PATH = f'{CONFIGURATION_ROOT}/surface_monitor.xml'
    VOLUME_MONITOR_PATH  = f'{CONFIGURATION_ROOT}/volume_monitor.xml'

    MATERIALS_PATH = 'materials.csv'

    FORCE_MONITOR_DEFAULT_NAME = 'force-mon-'
    POINT_MONITOR_DEFAULT_NAME = 'point-mon-'
    SURFACE_MONITOR_DEFAULT_NAME = 'surface-mon-'
    VOLUME_MONITOR_DEFAULT_NAME = 'volume-mon-'

    MONITOR_MAX_INDEX = 100

    _instance = None

    def __new__(cls):
        with _mutex:
            if cls._instance is None:
                cls._instance = super(CoreDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._modified = False
        self._filePath = None

        self._schema = xmlschema.XMLSchema(resource.file(self.XSD_PATH))

        xsdTree = etree.parse(resource.file(self.XSD_PATH))
        self._xmlSchema = etree.XMLSchema(etree=xsdTree)
        self._xmlParser = etree.XMLParser(schema=self._xmlSchema)
        self._xmlTree = etree.parse(resource.file(self.XML_PATH), self._xmlParser)

        df = pd.read_csv(resource.file(self.MATERIALS_PATH), header=0, index_col=0).transpose()
        self._materialDB = df.where(pd.notnull(df), None).to_dict()

        # Add 'air' as default material
        self.addMaterial('air')

    def getValue(self, xpath: str) -> str:
        """Returns specified configuration value.

        Returns configuration value specified by 'xpath'

        Args:
            xpath: XML xpath for the configuration item

        Returns:
            configuration value

        Raises:
            LookupError: Less or more than one item are matched
        """
        elements = self._xmlTree.findall(xpath, namespaces=nsmap)
        if len(elements) != 1:
            raise LookupError

        element = elements[0]

        path = self._xmlTree.getelementpath(element)
        schema = self._schema.find(".//" + path, namespaces=nsmap)

        if schema is None:
            raise LookupError

        if not schema.type.has_simple_content():
            raise LookupError

        return element.text

    def setValue(self, xpath: str, value: str):
        """Sets configuration value in specified path

        Sets configuration value in specified path

        Args:
            xpath: XML xpath for the configuration item
            value: configuration value

        Raises:
            LookupError: Less or more than one item are matched
            ValueError: Invalid configuration value
        """
        elements = self._xmlTree.findall(xpath, namespaces=nsmap)
        if len(elements) != 1:
            raise LookupError

        element = elements[0]

        path = self._xmlTree.getelementpath(element)
        schema = self._schema.find(".//" + path, namespaces=nsmap)

        if schema is None:
            raise LookupError

        if not schema.type.has_simple_content():
            raise LookupError

        if schema.type.local_name == 'inputNumberType'\
                or schema.type.base_type.local_name == 'inputNumberType':  # The case when the type has restrictions
            decimal = float(value)

            minValue = schema.type.min_value
            maxValue = schema.type.max_value

            if minValue is not None and decimal < minValue:
                raise ValueError

            if maxValue is not None and decimal > maxValue:
                raise ValueError

            element.text = value.lower()

            self._modified = True

        elif schema.type.local_name == 'inputNumberListType':
            numbers = value.split()
            # To check if the strings in value are valid numbers
            # 'ValueError" exception is raised if invalid number found
            [float(n) for n in numbers]

            element.text = value

            self._modified = True

        elif schema.type.is_decimal():
            if schema.type.is_simple():
                name = schema.type.local_name.lower()
                minValue = schema.type.min_value
                maxValue = schema.type.max_value
            else:
                name = schema.type.content.primitive_type.local_name.lower()
                minValue = schema.type.content.min_value
                maxValue = schema.type.content.max_value

            if 'integer' in name:
                decimal = int(value)
            else:
                decimal = float(value)

            if minValue is not None and decimal < minValue:
                raise ValueError

            if maxValue is not None and decimal > maxValue:
                raise ValueError

            if element.text == str(decimal):
                return

            element.text = str(decimal)
            self._modified = True

        else:  # String
            if schema.type.is_restriction() and value not in schema.type.enumeration:
                raise ValueError

            element.text = value
            self._modified = True

        self._xmlSchema.assertValid(self._xmlTree)

    def getMaterialsFromDB(self) -> list[(str, str, str)]:
        """Returns available materials from material database

        Returns available materials with name, chemicalFormula and phase from material database

        Returns:
            List of materials in tuple, '(name, chemicalFormula, phase)'
        """
        return [(k, v['chemicalFormula'], v['phase']) for k, v in self._materialDB.items()]

    def getMaterials(self) -> list[(str, str, str)]:
        """Returns configured materials

        Returns configured materials with name, chemicalFormula and phase from material database

        Returns:
            List of materials in tuple, '(name, chemicalFormula, phase)'
        """
        elements = self._xmlTree.findall(f'.//materials/material', namespaces=nsmap)

        return [(e.findtext('name', namespaces=nsmap), e.findtext('chemicalFormula', namespaces=nsmap), e.findtext('phase', namespaces=nsmap)) for e in elements]

    def addMaterial(self, name: str):
        """Add material to configuration from material database

        Add material to configuration from material database

        Raises:
            FileExistsError: Specified material is already in the configuration
            LookupError: material not found in material database
        """
        try:
            mdb = self._materialDB[name]
        except KeyError:
            raise LookupError

        material = self._xmlTree.find(f'.//materials/material[name="{name}"]', namespaces=nsmap)
        if material is not None:
            raise FileExistsError

        materialsElement = self._xmlTree.find('.//materials', namespaces=nsmap)

        def _materialPropertySubElement(parent: etree.Element, tag: str, pname: str):
            if mdb[pname] is None:
                return
            etree.SubElement(parent, f'{{{ns}}}{tag}').text = str(mdb[pname])

        material = etree.SubElement(materialsElement, f'{{{ns}}}material')

        etree.SubElement(material, f'{{{ns}}}name').text = name

        _materialPropertySubElement(material, 'chemicalFormula', 'chemicalFormula')
        _materialPropertySubElement(material, 'phase', 'phase')
        _materialPropertySubElement(material, 'molecularWeight', 'molecularWeight')
        _materialPropertySubElement(material, 'absorptionCoefficient', 'absorptionCoefficient')
        _materialPropertySubElement(material, 'surfaceTension', 'surfaceTension')
        _materialPropertySubElement(material, 'saturationPressure', 'saturationPressure')
        _materialPropertySubElement(material, 'emissivity', 'emissivity')

        density = etree.SubElement(material, f'{{{ns}}}density')
        etree.SubElement(density, f'{{{ns}}}specification').text = 'constant'
        _materialPropertySubElement(density, 'constant', 'density')

        specificHeat = etree.SubElement(material, f'{{{ns}}}specificHeat')
        etree.SubElement(specificHeat, f'{{{ns}}}specification').text = 'constant'
        _materialPropertySubElement(specificHeat, 'constant', 'specificHeat')
        etree.SubElement(specificHeat, f'{{{ns}}}polynomial').text = ''

        if mdb['viscosity'] is not None:
            viscosity = etree.SubElement(material, f'{{{ns}}}viscosity')
            etree.SubElement(viscosity, f'{{{ns}}}specification').text = 'constant'
            _materialPropertySubElement(viscosity, 'constant', 'viscosity')
            etree.SubElement(viscosity, f'{{{ns}}}polynomial').text = ''
            sutherland = etree.SubElement(viscosity, f'{{{ns}}}sutherland')
            _materialPropertySubElement(sutherland, 'coefficient', 'sutherlandCoefficient')
            _materialPropertySubElement(sutherland, 'temperature', 'sutherlandTemperature')

        thermalConductivity = etree.SubElement(material, f'{{{ns}}}thermalConductivity')
        etree.SubElement(thermalConductivity, f'{{{ns}}}specification').text = 'constant'
        _materialPropertySubElement(thermalConductivity, 'constant', 'thermalConductivity')
        etree.SubElement(thermalConductivity, f'{{{ns}}}polynomial').text = ''

        self._xmlSchema.assertValid(self._xmlTree)

    def removeMaterial(self, name: str):
        parent = self._xmlTree.find(f'.//materials', namespaces=nsmap)
        material = parent.find(f'material[name="{name}"]', namespaces=nsmap)
        if material is None:
            raise LookupError

        parent.remove(material)

    def addRegion(self, rname: str):
        region = self._xmlTree.find(f'.//cellZones/region[name="{rname}"]', namespaces=nsmap)

        if region is not None:
            raise FileExistsError

        cellZones = self._xmlTree.find('.//cellZones', namespaces=nsmap)

        region = etree.SubElement(cellZones, f'{{{ns}}}region')

        etree.SubElement(region, f'{{{ns}}}name').text = rname
        etree.SubElement(region, f'{{{ns}}}material').text = 'air'

        czone = etree.parse(resource.file(self.CELL_ZONE_PATH), self._xmlParser)
        region.append(czone.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

    def getRegions(self) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:cellZones/x:region/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def addCellZone(self, rname: str, zname: str):
        zone = self._xmlTree.find(f'.//cellZones/region[name="{rname}"]/cellZone[name="{zname}"]', namespaces=nsmap)

        if zone is not None:
            raise FileExistsError

        region = self._xmlTree.find(f'.//cellZones/region[name="{rname}"]', namespaces=nsmap)

        zone = etree.parse(resource.file(self.CELL_ZONE_PATH), self._xmlParser)
        zone.find('name', namespaces=nsmap).text = zname

        region.append(zone.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

    def getCellZones(self, rname: str) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:cellZones/x:region[x:name="{rname}"]/x:cellZone/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def addBoundaryCondition(self, bname: str, geometricalType: str):
        bc = self._xmlTree.find(f'.//boundaryConditions/boundaryCondition[name="{bname}"]', namespaces=nsmap)

        if bc is not None:
            raise FileExistsError

        parent = self._xmlTree.find(f'.//boundaryConditions', namespaces=nsmap)

        bc = etree.parse(resource.file(self.BOUNDARY_CONDITION_PATH), self._xmlParser)
        bc.find('name', namespaces=nsmap).text = bname

        # ToDo: set default physicalType according to the geometricalType

        parent.append(bc.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

    def getBoundaryConditions(self) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:boundaryConditions/x:boundaryCondition/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def addForceMonitor(self) -> str:
        names = self.getForceMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.FORCE_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'.//monitors/forces', namespaces=nsmap)

        fm = etree.parse(resource.file(self.FORCE_MONITOR_PATH), self._xmlParser)
        fm.find('name', namespaces=nsmap).text = monitorName

        parent.append(fm.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removeForceMonitor(self, name: str):
        monitor = self._xmlTree.find(f'.//monitors/forces/forceMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'.//monitors/forces', namespaces=nsmap)
        parent.remove(monitor)

    def getForceMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:monitors/x:forces/x:forceMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def addPointMonitor(self) -> str:
        names = self.getPointMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.POINT_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'.//monitors/points', namespaces=nsmap)

        monitor = etree.parse(resource.file(self.POINT_MONITOR_PATH), self._xmlParser)
        monitor.find('name', namespaces=nsmap).text = monitorName

        parent.append(monitor.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removePointMonitor(self, name: str):
        monitor = self._xmlTree.find(f'.//monitors/points/pointMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'.//monitors/points', namespaces=nsmap)
        parent.remove(monitor)

    def getPointMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:monitors/x:points/x:pointMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def addSurfaceMonitor(self) -> str:
        names = self.getSurfaceMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.SURFACE_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'.//monitors/surfaces', namespaces=nsmap)

        surface = etree.parse(resource.file(self.SURFACE_MONITOR_PATH), self._xmlParser)
        surface.find('name', namespaces=nsmap).text = monitorName

        parent.append(surface.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removeSurfaceMonitor(self, name: str):
        monitor = self._xmlTree.find(f'.//monitors/surfaces/surfaceMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'.//monitors/surfaces', namespaces=nsmap)
        parent.remove(monitor)

    def getSurfaceMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:monitors/x:surfaces/x:surfaceMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def addVolumeMonitor(self) -> str:
        names = self.getVolumeMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.VOLUME_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'.//monitors/volumes', namespaces=nsmap)

        volume = etree.parse(resource.file(self.VOLUME_MONITOR_PATH), self._xmlParser)
        volume.find('name', namespaces=nsmap).text = monitorName

        parent.append(volume.getroot())

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removeVolumeMonitor(self, name: str):
        monitor = self._xmlTree.find(f'.//monitors/volumes/volumeMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'.//monitors/volumes', namespaces=nsmap)
        parent.remove(monitor)

    def getVolumeMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'.//x:monitors/x:volumes/x:volumeMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def saveAs(self, path: str):
        f = h5py.File(path, 'w')
        try:
            dt = h5py.string_dtype(encoding='utf-8')
            ds = f.create_dataset('configuration', (1,), dtype=dt)
            ds[0] = etree.tostring(self._xmlTree, xml_declaration=True, encoding='UTF-8')

            # ToDo: write the rest of data like uploaded polynomials

        finally:
            f.close()

        self._filePath = path
        self._modified = False

    def save(self):
        f = h5py.File(self._filePath, 'r+')
        try:
            ds = f['configuration']
            if h5py.check_string_dtype(ds.dtype) is None:
                raise ValueError

            ds[0] = etree.tostring(self._xmlTree, xml_declaration=True, encoding='UTF-8')

            # ToDo: write the rest of data like uploaded polynomials
        finally:
            f.close()

        self._modified = False

    def load(self, path: str):
        f = h5py.File(path, 'r')
        try:
            ds = f['configuration']
            if h5py.check_string_dtype(ds.dtype) is None:
                raise ValueError

            root = etree.fromstring(ds[0], self._xmlParser)
        finally:
            f.close()

        self._xmlTree = root
        self._filePath = path
        self._modified = False
