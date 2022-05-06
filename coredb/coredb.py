#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PySide6.QtCore import QFile, QTextStream, QDataStream, QIODevice

from lxml import etree
import xmlschema

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc


ns = {'': 'http://www.example.org/baram'}
xs = {'': 'http://www.w3.org/2001/XMLSchema'}


class CoreDB:
    #XSD_PATH = u':/baram.cfg.xsd'
    #XML_PATH = u':/baram.cfg.xml'
    XSD_PATH = "../resources/baram.cfg.xsd"
    XML_PATH = '../resources/baram.cfg.xml'

    def __init__(self):
        xsdFile = QFile(self.XSD_PATH)
        xmlFile = QFile(self.XML_PATH)

        xsdFile.open(QIODevice.ReadOnly)
        xsdUString = xsdFile.readAll()

        xsdTree = etree.fromstring(bytes(xsdUString))
        xsdFile.close()

        schema = etree.XMLSchema(etree=xsdTree)
        parser = etree.XMLParser(schema=schema)

        xmlFile.open(QIODevice.ReadOnly)
        xmlUString = xmlFile.readAll()
        root = etree.fromstring(bytes(xmlUString), parser)
        xmlFile.close()


        # root = tree.getroot()
        # for child in root.findall(".//maxIterationsPerTimeStep", namespaces=ns):
        #     print(child.tag)

    def getValue(self, xpath):
        matches = self.schema.findall(xpath, namespaces=ns)

        if len(matches) != 1:
            raise LookupError

        match = matches[0]

        if not match.type.has_simple_content():
            raise LookupError

        if match.type.is_decimal():
            if match.type.has_restriction():
                pass
            else:
                pass
        else:  # String
            if match.type.is_restriction():
                pass
            else:  # Generic String
                pass

    def setValue(self, xpath, value):
        matches = self.schema.findall(xpath, namespaces=ns)

        if len(matches) != 1:
            raise LookupError

        match = matches[0]

        if not match.type.has_simple_content():
            raise LookupError

        if match.type.is_decimal():
            if match.type.has_restriction():
                print(f'       min {match.type.min_value}')
                print(f'       max {match.type.max_value}')
                pass
            else:
                pass
        else:  # String
            if match.type.is_restriction():
                for e in match.type.enumeration:
                    print(f'        enumeration {e}')
                pass
            else:  # Generic String
                pass



