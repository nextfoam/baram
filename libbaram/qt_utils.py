
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget


def allDirectChildrenAreHidden(widget: QWidget) -> bool:
    children = [child for child in widget.children() if isinstance(child, QWidget)]
    return all(child.isHidden() for child in children) if children else True