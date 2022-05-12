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
    XSD_PATH = 'baram.cfg.xsd'
    XML_PATH = 'baram.cfg.xml'

    MATERIALS_PATH = 'materials.csv'

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
        match = self._schema.find(".//" + path, namespaces=nsmap)

        if match is None:
            raise LookupError

        if not match.type.has_simple_content():
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
        match = self._schema.find(".//" + path, namespaces=nsmap)

        if match is None:
            raise LookupError

        if not match.type.has_simple_content():
            raise LookupError

        if match.type.local_name == 'inputNumberType'\
                or match.type.base_type.local_name == 'inputNumberType':  # The case when the type has restrictions
            decimal = float(value)

            minValue = match.type.min_value
            maxValue = match.type.max_value

            if minValue is not None and decimal < minValue:
                raise ValueError

            if maxValue is not None and decimal > maxValue:
                raise ValueError

            element.text = value.lower()

            self._modified = True

        elif match.type.local_name == 'inputNumberListType':
            numbers = value.split()
            # To check if the strings in value are valid numbers
            # 'ValueError" exception is raised if invalid number found
            [float(n) for n in numbers]

            element.text = value

            self._modified = True

        elif match.type.is_decimal():
            if match.type.is_simple():
                name = match.type.local_name.lower()
                minValue = match.type.min_value
                maxValue = match.type.max_value
            else:
                name = match.type.content.primitive_type.local_name.lower()
                minValue = match.type.content.min_value
                maxValue = match.type.content.max_value

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
            if match.type.is_restriction() and value not in match.type.enumeration:
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

