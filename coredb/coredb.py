#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Lock
from PySide6.QtCore import QFile, QIODevice

from lxml import etree
import xmlschema
import h5py

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

ns = {'': 'http://www.example.org/baram'}
xs = {'': 'http://www.w3.org/2001/XMLSchema'}

_mutex = Lock()


class CoreDB(object):
    XSD_PATH = u':/baram.cfg.xsd'
    XML_PATH = u':/baram.cfg.xml'
    # XSD_PATH = "../resources/baram.cfg.xsd"
    # XML_PATH = '../resources/baram.cfg.xml'

    _instance = None

    def __new__(cls):
        with _mutex:
            if cls._instance is None:
                cls._instance = super(CoreDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._modified = False
        self._filePath = None

        xsdFile = QFile(self.XSD_PATH)
        xsdFile.open(QIODevice.ReadOnly)
        xsdBytes = bytes(xsdFile.readAll())
        xsdFile.close()

        self._schema = xmlschema.XMLSchema(xsdBytes)

        xmlFile = QFile(self.XML_PATH)
        xmlFile.open(QIODevice.ReadOnly)
        xmlBytes = bytes(xmlFile.readAll())
        xmlFile.close()

        xsdTree = etree.fromstring(xsdBytes)
        schema = etree.XMLSchema(etree=xsdTree)
        self._xmlParser = etree.XMLParser(schema=schema)
        self._root = etree.fromstring(xmlBytes, self._xmlParser)

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
        matches = self._schema.findall(xpath, namespaces=ns)

        if len(matches) != 1:
            raise LookupError

        match = matches[0]

        if not match.type.has_simple_content():
            raise LookupError

        elements = self._root.findall(xpath, namespaces=ns)
        if len(elements) != 1:
            raise LookupError

        element = elements[0]

        if match.type.local_name == 'inputNumberType' or match.type.base_type.local_name == 'inputNumberType':
            notation = match.attributes['notation'].default
            if element.attrib.get('notation') is not None:
                notation = element.attrib['notation']

            if notation == 'decimal':
                return element.text
            elif notation == 'scientific':
                return f'{element.attrib["mantissa"]}E{element.attrib["exponent"]}'
            else:
                raise AssertionError('Unknown Number Notation Type')
        else:
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
        matches = self._schema.findall(xpath, namespaces=ns)

        if len(matches) != 1:
            raise LookupError

        match = matches[0]

        if not match.type.has_simple_content():
            raise LookupError

        elements = self._root.findall(xpath, namespaces=ns)
        if len(elements) != 1:
            raise LookupError

        element = elements[0]

        if match.type.local_name == 'inputNumberType' or match.type.base_type.local_name == 'inputNumberType':
            decimal = float(value)

            minValue = match.type.content.min_value
            maxValue = match.type.content.max_value

            if minValue is not None and decimal < minValue:
                raise ValueError

            if maxValue is not None and decimal > maxValue:
                raise ValueError

            if "e" in value.lower():  # scientific notation
                mantissa, exponent = value.lower().split('e')
                element.attrib['notation'] = 'scientific'
                element.attrib['mantissa'] = mantissa
                element.attrib['exponent'] = exponent
            else:
                element.attrib['notation'] = 'decimal'

            element.text = str(decimal)
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

    def saveAs(self, path: str):
        f = h5py.File(path, 'w')
        try:
            dt = h5py.string_dtype(encoding='utf-8')
            ds = f.create_dataset('configuration', (1,), dtype=dt)
            ds[0] = etree.tostring(self._root, xml_declaration=True,  encoding='UTF-8')

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

            ds[0] = etree.tostring(self._root, xml_declaration=True,  encoding='UTF-8')

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

        self._root = root
        self._filePath = path
        self._modified = False

