#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QFile, QIODevice

from lxml import etree
import xmlschema

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

ns = {'': 'http://www.example.org/baram'}
xs = {'': 'http://www.w3.org/2001/XMLSchema'}


class CoreDB:
    # XSD_PATH = u':/baram.cfg.xsd'
    # XML_PATH = u':/baram.cfg.xml'
    XSD_PATH = "../resources/baram.cfg.xsd"
    XML_PATH = '../resources/baram.cfg.xml'

    def __init__(self):
        self._modified = False

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
        parser = etree.XMLParser(schema=schema)
        self._root = etree.fromstring(xmlBytes, parser)

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
