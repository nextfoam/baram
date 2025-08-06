#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import copy
import logging
from typing import Optional

from lxml import etree
import xmlschema
import h5py
from xmlschema.names import XSD_DOUBLE, XSD_MIN_INCLUSIVE, XSD_MAX_INCLUSIVE, XSD_MIN_EXCLUSIVE, XSD_MAX_EXCLUSIVE

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from resources import resource
from baramFlow.coredb import migrate
from .libdb import nsmap, ns, DBError, ValueException

__instance: Optional[_CoreDB] = None

logger = logging.getLogger(__name__)


class Cancel(Exception):
    pass


def CoreDB():
    global __instance
    assert(__instance is not None)

    return __instance


def createDB():
    global __instance
    assert(__instance is None)

    __instance = _CoreDB()
    __instance.loadDefault()

    return __instance


def loadDB(file):
    global __instance
    assert(__instance is None)

    __instance = _CoreDB()
    __instance.load(file)

    return __instance


def loaded():
    global __instance
    return __instance is not None


def destroy():
    global __instance
    __instance = None


class _CoreDB(object):
    CONFIGURATION_ROOT = 'configurations'
    XSD_PATH = f'{CONFIGURATION_ROOT}/baram.cfg.xsd'
    XML_PATH = f'{CONFIGURATION_ROOT}/baram.cfg.xml'

    CELL_ZONE_PATH = f'{CONFIGURATION_ROOT}/cell_zone.xml'
    BOUNDARY_CONDITION_PATH = f'{CONFIGURATION_ROOT}/boundary_condition.xml'

    FORCE_MONITOR_PATH   = f'{CONFIGURATION_ROOT}/force_monitor.xml'
    POINT_MONITOR_PATH   = f'{CONFIGURATION_ROOT}/point_monitor.xml'
    SURFACE_MONITOR_PATH = f'{CONFIGURATION_ROOT}/surface_monitor.xml'
    VOLUME_MONITOR_PATH  = f'{CONFIGURATION_ROOT}/volume_monitor.xml'

    FORCE_MONITOR_DEFAULT_NAME = 'force-mon-'
    POINT_MONITOR_DEFAULT_NAME = 'point-mon-'
    SURFACE_MONITOR_DEFAULT_NAME = 'surface-mon-'
    VOLUME_MONITOR_DEFAULT_NAME = 'volume-mon-'

    MONITOR_MAX_INDEX = 100
    MATERIAL_MAX_INDEX = 1000
    CELL_ZONE_MAX_INDEX = 1000
    BOUNDARY_CONDITION_MAX_INDEX = 10000
    USER_DEFINED_SCALAR_MAX_INDEX = 10000

    def __init__(self):
        self._initialized = True

        self._configCount = 0
        self._configCountAtSave = self._configCount
        self._inContext = False
        self._backupTree = None
        self._lastError = None
        self._lastNote = None

        self._schema = xmlschema.XMLSchema(resource.file(self.XSD_PATH))

        xsdTree = etree.parse(resource.file(self.XSD_PATH))
        self._xmlSchema = etree.XMLSchema(etree=xsdTree)
        self._xmlParser = etree.XMLParser(schema=self._xmlSchema)

        self._xmlTree = None

    def __enter__(self):
        logger.debug('enter')
        self._backupTree = copy.deepcopy(self._xmlTree)
        self._lastError = None
        self._inContext = True
        return self

    def __exit__(self, eType, eValue, eTraceback):
        if self._lastError is not None or eType is not None:
            self._xmlTree = self._backupTree

        self._lastError = None
        self._backupTree = None
        self._inContext = False

        if eType == Cancel:
            logger.debug('exit with Cancel')
            return True
        else: # To make it clear
            logger.debug('exit without error')
            return None

    def getAttribute(self, xpath: str, name: str) -> str:
        """Returns attribute value on specified configuration path.

        Returns attribute value specified by 'xpath', and 'name'

        Args:
            xpath: XML xpath for the configuration item
            name: attribute name

        Returns:
            attribute value

        Raises:
            LookupError: Less or more than one item are matched, or attribute not found
        """
        elements = self._xmlTree.findall(xpath, namespaces=nsmap)
        if len(elements) != 1:
            raise LookupError

        value = elements[0].get(name)
        if value is None:
            raise LookupError

        logger.debug(f'getAttribute( {xpath}:{name} -> {value} )')

        return value

    def setAttribute(self, xpath: str, name: str, value: str):
        """Returns attribute value on specified configuration path.

        Returns attribute value specified by 'xpath', and 'name'

        Args:
            xpath: XML xpath for the configuration item
            name: attribute name
            value: attribute value

        Returns:

        Raises:
            LookupError: Less or more than one item are matched, or attribute not found
        """
        elements = self._xmlTree.findall(xpath, namespaces=nsmap)
        if len(elements) != 1:
            raise LookupError

        if name not in elements[0].keys():
            raise LookupError

        oldValue = elements[0].get(name)
        elements[0].set(name, value)
        if value != oldValue:
            self._configCount += 1

        logger.debug(f'setAttribute( {xpath}:{name} -> {value} )')

    def getValue(self, xpath: str) -> str:
        """Returns specified configuration setting.

        Returns configuration value specified by 'xpath'

        Args:
            xpath: XML xpath for the configuration item

        Returns:
            user parameter or configuration value

        Raises:
            LookupError: Less or more than one item are matched
        """
        element = self.getElement(xpath)
        if parameter := element.get('batchParameter'):
            return '$' + parameter

        path = self._xmlTree.getelementpath(element)
        schema = self._schema.find('/{http://www.baramcfd.org/baram}configuration/' + path, namespaces=nsmap)

        if schema is None:
            raise LookupError

        if not schema.type.has_simple_content():
            raise LookupError

        logger.debug(f'getValue( {xpath} -> {element.text} )')

        if element.text is None:
            return ''
        else:
            return element.text

    def validate(self, xpath: str, value: str):
        """Validates configuration value in specified path

        Validates configuration value in specified path
        Returns tuple: (xml element to be set, value, batch parameter name)

        Args:
            xpath: XML xpath for the configuration item
            value: configuration value

        Raises:
            LookupError: Less or more than one item are matched
            ValueError: Invalid configuration value by program
            DBValueException: Invalid configuration value by user
        """
        element = self.getElement(xpath)

        path = self._xmlTree.getelementpath(element)
        schema = self._schema.find('/{http://www.baramcfd.org/baram}configuration/' + path, namespaces=nsmap)

        if schema is None:
            raise LookupError

        if not schema.type.has_simple_content():
            raise LookupError

        batchParameter = None
        value = value.strip()

        if schema.type.is_complex() and 'batchParameter' in schema.type.attributes:
            if value and value[0] == '$':
                batchParameter = value[1:]
                batchParameterXPath = f'/runCalculation/batch/parameters/parameter[name="{batchParameter}"]'
                batchParameterValue = self._xmlTree.findall(f'{batchParameterXPath}/value', namespaces=nsmap)

                if len(batchParameterValue) == 1:
                    value = batchParameterValue[0].text
                else:
                    batchParameter = None

        if schema.type.local_name == 'inputNumberListType':
            numbers = value.split()
            # To check if the strings in value are valid numbers
            # 'ValueError' exception is raised if invalid number found
            try:
                [float(n) for n in numbers]
            except ValueError:
                self._lastError = DBError.FLOAT_ONLY
                raise ValueException(DBError.FLOAT_ONLY, self._lastNote)

            return element, ' '.join(numbers), None

        elif schema.type.is_derived(schema.type.maps.types[XSD_DOUBLE]):  # The case when the type has restrictions or attributes
            try:
                decimal = float(value)
            except ValueError:
                self._lastError = DBError.FLOAT_ONLY
                raise ValueException(DBError.FLOAT_ONLY, self._lastNote)

            if (minValue := getattr(schema.type.base_type.get_facet(XSD_MIN_INCLUSIVE), 'value', None)) is not None:
                if decimal < minValue:
                    self._lastError = DBError.OUT_OF_RANGE
                    raise ValueException(DBError.OUT_OF_RANGE, self._lastNote)

            if (maxValue := getattr(schema.type.base_type.get_facet(XSD_MAX_INCLUSIVE), 'value', None)) is not None:
                if decimal > maxValue:
                    self._lastError = DBError.OUT_OF_RANGE
                    raise ValueException(DBError.OUT_OF_RANGE, self._lastNote)

            if (minValue := getattr(schema.type.base_type.get_facet(XSD_MIN_EXCLUSIVE), 'value', None)) is not None:
                if decimal <= minValue:
                    self._lastError = DBError.OUT_OF_RANGE
                    raise ValueException(DBError.OUT_OF_RANGE, self._lastNote)

            if (maxValue := getattr(schema.type.base_type.get_facet(XSD_MAX_EXCLUSIVE), 'value', None)) is not None:
                if decimal >= maxValue:
                    self._lastError = DBError.OUT_OF_RANGE
                    raise ValueException(DBError.OUT_OF_RANGE, self._lastNote)

            return element, value.lower(), batchParameter

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
                try:
                    decimal = int(value)
                except ValueError:
                    self._lastError = DBError.INTEGER_ONLY
                    raise ValueException(DBError.INTEGER_ONLY, self._lastNote)
            else:
                try:
                    decimal = float(value)
                except ValueError:
                    self._lastError = DBError.FLOAT_ONLY
                    raise ValueException(DBError.FLOAT_ONLY, self._lastNote)

            if minValue is not None and decimal < minValue:
                self._lastError = DBError.OUT_OF_RANGE
                raise ValueException(DBError.OUT_OF_RANGE, self._lastNote)

            if maxValue is not None and decimal > maxValue:
                self._lastError = DBError.OUT_OF_RANGE
                raise ValueException(DBError.OUT_OF_RANGE, self._lastNote)

            return element, value.lower(), None

        # String
        # For now, string value is set only by VIEW code not by user.
        # Therefore, raising exception(not returning value) is reasonable.
        else:
            if schema.type.is_restriction():
                if schema.type.enumeration is not None and value not in schema.type.enumeration:
                    raise ValueError

                if schema.type.patterns is not None:
                    for p in schema.type.patterns.patterns:
                        if p.match(value) is None:
                            raise ValueError

            return element, value, None

    def setValue(self, xpath: str, value: str, note=None):
        """Sets configuration value in specified path

        Sets configuration value in specified path

        Args:
            xpath: XML xpath for the configuration item
            value: configuration value

        Raises:
            LookupError: Less or more than one item are matched
            ValueError: Invalid configuration value
            ValueException: Invalid configuration value by user
        """
        self._lastNote = note
        element, value, parameter = self.validate(xpath, value)

        if element.text != value:
            if element.text or value:     # the case of (element.text=='' and oldValue is None) happens because of XML processing
                self._configCount += 1

            element.text = value

        logger.debug(f'setValue( {xpath} -> {element.text} )')

        self._xmlSchema.assertValid(self._xmlTree)

        if element.get('batchParameter') != parameter:
            if parameter:
                element.set('batchParameter', parameter)
            else:
                del element.attrib['batchParameter']
            self._configCount += 1

    def setBulk(self, xpath: str, value: dict):
        """Set the value at the specified path

        Current configuration under the xpath will be cleared.
        Usually process is like following.
            1. A value of type dictionary is read by getBulk()
            2. Some values in the dictionary are modified
            3. the dictionary value is written back by setBulk
        It handles only dictionary, list and simple types

        Args:
            xpath: XML xpath for the configuration item
            value: configuration value of dictionary type

        Raises:
            LookupError: Less or more than one item are matched
            ValueError: Invalid configuration value
            RuntimeError: Called not in "with" context
        """
        def _setBulkInternal(element: etree.Element, data: dict):
            for k, v in data.items():
                # process attributes
                if k.startswith('@'):
                    element.set(k[1:], v)
                # process text
                elif k.startswith('$'):
                    element.text = str(v)
                # process dictionary
                elif isinstance(v, dict):
                    _setBulkInternal(etree.SubElement(element, f'{{{ns}}}{k}'), v)
                elif isinstance(v, list):
                    # Only primitive types or dictionary can be a member of the value
                    if len(v) == 0:
                        etree.SubElement(element, f'{{{ns}}}{k}')
                    elif isinstance(v[0], dict):
                        for item in v:
                            if not isinstance(item, dict):
                                raise ValueError
                            _setBulkInternal(etree.SubElement(element, f'{{{ns}}}{k}'), item)
                    else:
                        for item in v:
                            etree.SubElement(element, f'{{{ns}}}{k}').text = str(item)
                else:
                    etree.SubElement(element, f'{{{ns}}}{k}').text = str(v)

        if not self._inContext:
            raise RuntimeError

        if not isinstance(value, dict):
            raise ValueError

        elements = self._xmlTree.findall(xpath, namespaces=nsmap)
        if len(elements) != 1:
            raise LookupError

        elements[0].clear()
        _setBulkInternal(elements[0], value)
        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

    def getBulk(self, xpath: str) -> dict:
        """Get the value at the specified path

        Current configuration under the xpath will be returned in dictionary type

        Args:
            xpath: XML xpath for the configuration item

        Raises:
            LookupError: Less or more than one item are matched
        """
        def _getBulkInternal(element: etree.Element) -> dict:
            data = {}

            # process attributes
            for k, v in element.items():
                data['@' + k] = v

            # process dictionary
            for child in element:
                tag = etree.QName(child.tag).localname
                result = _getBulkInternal(child)
                if tag in data:
                    if isinstance(data[tag], list):
                        data[tag].append(result)
                    else:
                        data[tag] = [
                            data[tag],
                            result
                        ]
                else:
                    data[tag] = result

            # process text
            if element.text is not None:
                if data:  # dictionary is not empty
                    data['$'] = element.text
                else:
                    data = element.text

            return data

        elements = self._xmlTree.findall(xpath, namespaces=nsmap)
        if len(elements) != 1:
            raise LookupError

        return _getBulkInternal(elements[0])

    def availableID(self, xpath, attribute):
        idList = [e.get(attribute) for e in self.getElements(xpath)]
        index = 1
        while str(index) in idList:
            index += 1

        return str(index)

    def toUniqueText(self, xpath, name, desiredText):
        seq = 0
        text = desiredText
        while self.exists(f'{xpath}[{name}="{text}"]'):
            seq += 1
            text = f'{desiredText}{seq}'

        return text

    def getRegions(self) -> list[str]:
        elements = self._xmlTree.findall(f'/regions/region', namespaces=nsmap)
        regions = [e.find('name', namespaces=nsmap).text for e in elements]
        if len(regions) == 1 and regions[0] is None:
            self.setValue('/regions/region/name', '')
            return ['']

        return regions

    def clearRegions(self):
        parent = self._xmlTree.find('/regions', namespaces=nsmap)
        parent.clear()

    def addCellZone(self, rname: str, zname: str) -> int:
        zone = self._xmlTree.find(f'/regions/region[name="{rname}"]/cellZones/cellZone[name="{zname}"]', namespaces=nsmap)

        if zone is not None:
            raise FileExistsError

        idList = self._xmlTree.xpath(f'/x:configuration/x:regions/x:region/x:cellZones/x:cellZone/@czid', namespaces={'x': ns})

        for index in range(1, self.CELL_ZONE_MAX_INDEX):
            if str(index) not in idList:
                break
        else:
            raise OverflowError

        # 'region' cannot be None because zoneTree lookup above succeeded
        cellZones = self._xmlTree.find(f'/regions/region[name="{rname}"]/cellZones', namespaces=nsmap)

        zoneTree = etree.parse(resource.file(self.CELL_ZONE_PATH), self._xmlParser)
        zone = zoneTree.getroot()
        zone.find('name', namespaces=nsmap).text = zname
        zone.attrib['czid'] = str(index)

        cellZones.append(zone)

        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

        return index

    def getCellZones(self, rname: str) -> list[(int, str)]:
        elements = self._xmlTree.findall(f'/regions/region[name="{rname}"]/cellZones/cellZone', namespaces=nsmap)
        return [(int(e.attrib['czid']), e.find('name', namespaces=nsmap).text) for e in elements]

    def getCellZonesByType(self, rname: str, zoneType: str) -> list[int]:
        elements = self._xmlTree.findall(f'/regions/region[name="{rname}"]/cellZones/cellZone[zoneType="{zoneType}"]',
                                         namespaces=nsmap)
        return [e.attrib['czid'] for e in elements]

    def addBoundaryCondition(self, rname: str, bname: str, geometricalType: str, physicalType: str) -> int:
        bc = self._xmlTree.find(f'/regions/region[name="{rname}"]/boundaryConditions/boundaryCondition[name="{bname}"]',
                                namespaces=nsmap)

        if bc is not None:
            raise FileExistsError

        idList = self._xmlTree.xpath(f'/x:configuration/x:regions/x:region/x:boundaryConditions/x:boundaryCondition/@bcid', namespaces={'x': ns})

        for index in range(1, self.BOUNDARY_CONDITION_MAX_INDEX):
            if str(index) not in idList:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'/regions/region[name="{rname}"]/boundaryConditions', namespaces=nsmap)

        bcTree = etree.parse(resource.file(self.BOUNDARY_CONDITION_PATH), self._xmlParser)
        bc = bcTree.getroot()
        bc.find('name', namespaces=nsmap).text = bname
        bc.attrib['bcid'] = str(index)

        if geometricalType is not None:
            bc.find('geometricalType', namespaces=nsmap).text = geometricalType

        bc.find('physicalType', namespaces=nsmap).text = physicalType

        parent.append(bc)

        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

        return index

    def getBoundaryConditions(self, rname: str) -> list[tuple[int, str, str]]:
        """Returns list of boundary conditions in the region

        Returns list of boundary conditions in the region

        Args:
            rname: region name

        Returns:
            List of boundary conditions in tuple, '(bcid, name, physicalType)'
        """
        elements = self._xmlTree.findall(
            f'/regions/region[name="{rname}"]/boundaryConditions/boundaryCondition', namespaces=nsmap)
        return [(int(e.attrib['bcid']),
                 e.find('name', namespaces=nsmap).text,
                 e.find('physicalType', namespaces=nsmap).text) for e in elements]

    def copyBoundaryConditions(self, sourceID, targetID):
        old = self.getElement(f'regions/region/boundaryConditions/boundaryCondition[@bcid="{targetID}"]')
        new = copy.deepcopy(self.getElement(f'regions/region/boundaryConditions/boundaryCondition[@bcid="{sourceID}"]'))
        new.set('bcid', str(targetID))
        new.find('name', namespaces=nsmap).text = old.find('name', namespaces=nsmap).text
        new.find('geometricalType', namespaces=nsmap).text = old.find('geometricalType', namespaces=nsmap).text
        old.getparent().replace(old, new)

    def hasMesh(self):
        return True if self._xmlTree.findall(f'/regions/region', namespaces=nsmap) else False

    def addForceMonitor(self) -> str:
        names = self.getForceMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.FORCE_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'/monitors/forces', namespaces=nsmap)

        forceTree = etree.parse(resource.file(self.FORCE_MONITOR_PATH), self._xmlParser)
        forceTree.find('name', namespaces=nsmap).text = monitorName

        parent.append(forceTree.getroot())

        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removeForceMonitor(self, name: str):
        monitor = self._xmlTree.find(f'/monitors/forces/forceMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'/monitors/forces', namespaces=nsmap)
        parent.remove(monitor)

        self._configCount += 1

    def getForceMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'/x:configuration/x:monitors/x:forces/x:forceMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def clearForceMonitors(self):
        parent = self._xmlTree.find('/monitors/forces', namespaces=nsmap)
        parent.clear()

    def addPointMonitor(self) -> str:
        names = self.getPointMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.POINT_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'/monitors/points', namespaces=nsmap)

        pointTree = etree.parse(resource.file(self.POINT_MONITOR_PATH), self._xmlParser)
        pointTree.find('name', namespaces=nsmap).text = monitorName

        parent.append(pointTree.getroot())

        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removePointMonitor(self, name: str):
        monitor = self._xmlTree.find(f'/monitors/points/pointMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'/monitors/points', namespaces=nsmap)
        parent.remove(monitor)

        self._configCount += 1

    def getPointMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'/x:configuration/x:monitors/x:points/x:pointMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def clearPointMonitors(self):
        parent = self._xmlTree.find('/monitors/points', namespaces=nsmap)
        parent.clear()

    def addSurfaceMonitor(self) -> str:
        names = self.getSurfaceMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.SURFACE_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'/monitors/surfaces', namespaces=nsmap)

        surfaceTree = etree.parse(resource.file(self.SURFACE_MONITOR_PATH), self._xmlParser)
        surfaceTree.find('name', namespaces=nsmap).text = monitorName

        parent.append(surfaceTree.getroot())

        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removeSurfaceMonitor(self, name: str):
        monitor = self._xmlTree.find(f'/monitors/surfaces/surfaceMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'/monitors/surfaces', namespaces=nsmap)
        parent.remove(monitor)

        self._configCount += 1

    def getSurfaceMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'/x:configuration/x:monitors/x:surfaces/x:surfaceMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def clearSurfacesMonitors(self):
        parent = self._xmlTree.find('/monitors/surfaces', namespaces=nsmap)
        parent.clear()

    def addVolumeMonitor(self) -> str:
        names = self.getVolumeMonitors()

        for index in range(1, self.MONITOR_MAX_INDEX):
            monitorName = self.VOLUME_MONITOR_DEFAULT_NAME+str(index)
            if monitorName not in names:
                break
        else:
            raise OverflowError

        parent = self._xmlTree.find(f'/monitors/volumes', namespaces=nsmap)

        volumeTree = etree.parse(resource.file(self.VOLUME_MONITOR_PATH), self._xmlParser)
        volumeTree.find('name', namespaces=nsmap).text = monitorName

        parent.append(volumeTree.getroot())

        self._configCount += 1

        self._xmlSchema.assertValid(self._xmlTree)

        return monitorName

    def removeVolumeMonitor(self, name: str):
        monitor = self._xmlTree.find(f'/monitors/volumes/volumeMonitor[name="{name}"]', namespaces=nsmap)
        if monitor is None:
            raise LookupError

        parent = self._xmlTree.find(f'/monitors/volumes', namespaces=nsmap)
        parent.remove(monitor)

        self._configCount += 1

    def getVolumeMonitors(self) -> list[str]:
        names = self._xmlTree.xpath(f'/x:configuration/x:monitors/x:volumes/x:volumeMonitor/x:name/text()', namespaces={'x': ns})
        return [str(r) for r in names]

    def clearVolumeMonitors(self):
        parent = self._xmlTree.find('/monitors/volumes', namespaces=nsmap)
        parent.clear()

    def clearMonitors(self):
        self.clearForceMonitors()
        self.clearPointMonitors()
        self.clearSurfacesMonitors()
        self.clearVolumeMonitors()

    def getBatchParameters(self):
        parameters = {}
        for e in self._xmlTree.findall('/runCalculation/batch/parameters/parameter', namespaces=nsmap):
            name = e.find('name', namespaces=nsmap).text
            parameters[name] = {'value': e.find('value', namespaces=nsmap).text, 'usages': 0}

        for e in self._xmlTree.findall('.//*[@batchParameter]', namespaces=nsmap):
            parameters[e.get('batchParameter')]['usages'] += 1

        return parameters

    def getBatchDefaults(self):
        return {e.find('name', namespaces=nsmap).text: e.find('value', namespaces=nsmap).text
                for e in self._xmlTree.findall('/runCalculation/batch/parameters/parameter', namespaces=nsmap)}

    def getSurfaceTensions(self, rname):
        xpath = f'/regions/region[name="{rname}"]/phaseInteractions/surfaceTensions/surfaceTension'
        elements = self._xmlTree.findall(xpath, namespaces=nsmap)

        surfaceTensions = []
        for e in elements:
            mid1, mid2 = (m.text for m in e.findall('mid', namespaces=nsmap))
            value = self.getValue(f'{xpath}[mid="{mid1}"][mid="{mid2}"]/value')
            surfaceTensions.append((mid1, mid2, value))

        return surfaceTensions

    def getUserDefinedScalars(self):
        elements = self._xmlTree.findall(f'/models/userDefinedScalars/scalar', namespaces=nsmap)
        return [(int(e.attrib['scalarID']), e.find('fieldName', namespaces=nsmap).text)
                for e in elements if e.attrib['scalarID'] != '0']

    def getUserDefinedScalarsInRegion(self, rname):
        elements = self._xmlTree.findall(f'/models/userDefinedScalars/scalar[region="{rname}"]', namespaces=nsmap)
        return [(int(e.attrib['scalarID']), e.find('fieldName', namespaces=nsmap).text)
                for e in elements if e.attrib['scalarID'] != '0']

    def addElementFromString(self, xpath, text):
        parent = self._xmlTree.find(xpath, namespaces=nsmap)
        if parent is None:
            raise LookupError

        parent.append(etree.fromstring(text))

        self._xmlSchema.assertValid(self._xmlTree)

        self._configCount += 1

    def addElement(self, xpath, element):
        parent = self._xmlTree.find(xpath, namespaces=nsmap)
        if parent is None:
            raise LookupError

        parent.append(element)

        self._xmlSchema.assertValid(self._xmlTree)

        self._configCount += 1

    def removeElement(self, xpath):
        element = self._xmlTree.find(xpath, namespaces=nsmap)
        if element is None:
            return

        parent = self._xmlTree.find(xpath+'/..', namespaces=nsmap)
        parent.remove(element)

        self._configCount += 1

    def clearElement(self, xpath):
        element = self._xmlTree.find(xpath, namespaces=nsmap)
        if element is None:
            raise LookupError

        element.clear()

    def getList(self, xpath) -> list[str]:
        return [e.text for e in self._xmlTree.findall(xpath, namespaces=nsmap)]

    def exists(self, xpath: str):
        """Returns if specified configuration path exists.

        Args:
            xpath: XML xpath for the configuration item.

        Returns:
            True if xpath element exists, False otherwise.
        """
        return self._xmlTree.find(xpath, namespaces=nsmap) is not None

    def getVector(self, xpath: str):
        return [float(self.getValue(xpath + '/x')),
                float(self.getValue(xpath + '/y')),
                float(self.getValue(xpath + '/z'))]

    def getBool(self, xpath: str):
        return self.getValue(xpath) == 'true'

    @property
    def isModified(self) -> bool:
        return self._configCountAtSave != self._configCount

    @property
    def configCount(self) -> int:
        return self._configCount

    def saveAs(self, path: str):
        f = h5py.File(path, 'w')
        try:
            dt = h5py.string_dtype(encoding='utf-8')
            ds = f.create_dataset('configuration', (1,), dtype=dt)
            ds[0] = etree.tostring(self._xmlTree, xml_declaration=True, encoding='UTF-8')

        finally:
            f.close()

        # self._filePath = path
        self._configCountAtSave = self._configCount

    def save(self, path: str):
        with h5py.File(path, 'a') as f:
            if 'configuration' in f.keys():
                del f['configuration']

            f['configuration'] = etree.tostring(self._xmlTree.getroot(), xml_declaration=True, encoding='UTF-8')

        self._configCountAtSave = self._configCount

    def load(self, path: str):
        with h5py.File(path, 'r') as f:
            ds = f['configuration']
            if h5py.check_string_dtype(ds.dtype) is None:
                raise ValueError

            root = etree.fromstring(ds[()])
            migrate.migrate(root)

            tree = etree.ElementTree(root)
            self._xmlSchema.assertValid(tree)
            self._xmlTree = tree

        self._configCountAtSave = self._configCount

    def loadDefault(self):
        self._xmlTree = etree.parse(resource.file(self.XML_PATH), self._xmlParser)
        # Add 'air' as default material
        # self.addMaterial('air', 'air')

        self._configCountAtSave = self._configCount

    def getElement(self, xpath):
        element = self._xmlTree.find(xpath, namespaces=nsmap)
        if element is None:
            raise LookupError

        return element

    def getElements(self, xpath):
        return self._xmlTree.findall(xpath, namespaces=nsmap)

    def increaseConfigCount(self):
        self._xmlSchema.assertValid(self._xmlTree)
        self._configCount += 1
