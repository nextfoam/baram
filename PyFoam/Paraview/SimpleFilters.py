#  ICE Revision: $Id$ 
""" Simple filters

Builds and displays simple filters. Grants easy access to the actual filter
and the representation objects"""

from paraview import servermanager

from PyFoam.Paraview import proxyManager as pm
from PyFoam.Paraview import renderView as rv
from PyFoam.Paraview import characteristicLength as lc
from PyFoam.Paraview import getCenter as gc

from SimpleSources import SimpleSource

class SimpleFilter(SimpleSource):
    """Base class for the simple filters"""

    def __init__(self,name,src):
        """:param name: The name under which the thing should be displayed
        :param src: the actual source proxy"""
        SimpleSource.__init__(self,name,src)
        
class Group(SimpleFilter):
    """Class for grouping other objects"""

    def __init__(self,name):
        try:
            grp=servermanager.filters.GroupDataSets()
        except AttributeError:
            grp=servermanager.filters.GroupDatasets()
            
        SimpleFilter.__init__(self,name,grp)

    def add(self,obj):
        """Add an object to the group"""
        self.src.Input.append(obj.src)
        self.src.UpdatePipeline()
        
