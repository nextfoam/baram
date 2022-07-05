#  ICE Revision: $Id$
""" Wrapper class for the paraview servermanager

Sets up the servermanager to be used with OpenFOAM-Data. Especially makes sure that
the plugins for the OpenFOAM-Data are loaded"""

from math import sqrt
# from glob import glob
from paraview import servermanager
from PyFoam.Paraview import version
from PyFoam.FoamInformation import foamVersion

from PyFoam.ThirdParty.six import print_

if version()>=(3,6):
    from paraview.simple import LoadPlugin
    from paraview import simple

from os import environ,path
from platform import uname

from PyFoam.Error import error,warning

class ServermanagerWrapper(object):
    """Wrapper class for the servermanager

    Load the plugins and build a connection"""

    def __init__(self,requiredReader="PV3FoamReader"):
        """Sets up the Servermanager in such a way that it is usable
        with OpenFOAM-data.
        :param requiredReader: Reader that is needed. If not found, try to load plugins"""

        try:
            self.con=self.module().Connect()
        except RuntimeError:
            # 3.98 doesn't seem to need this naymore
            self.con=None

        dyExt="so"
        if uname()[0]=="Darwin":
            dyExt="dylib"
        elif uname()[0]=="Windows":
            dyExt="DLL"

        if requiredReader in dir(simple) and not "OpenFOAMReader":
            warning("Reader",requiredReader,"already present. No plugins loaded")
            return

        if requiredReader=="PV3FoamReader":
            if uname()[0]=="Darwin":
                import ctypes
                # lib=ctypes.CDLL("/Users/bgschaid/OpenFOAM/ThirdParty-1.6/paraview-3.6.2/platforms/darwinIntel64/lib/paraview-3.6/libpqComponents.dylib",mode=ctypes.RTLD_GLOBAL)
                lib=ctypes.CDLL(path.join(environ["FOAM_LIBBIN"],"libOpenFOAM.dylib"),mode=ctypes.RTLD_GLOBAL)
                # lib=ctypes.CDLL(path.join(environ["FOAM_LIBBIN"],"paraview","libPV3FoamReader.dylib"),mode=ctypes.RTLD_GLOBAL)
                print_(lib)
            elif uname()[0]=="Linux":
                try:
                    import ctypes
                    dirs=[environ["FOAM_LIBBIN"]]+environ["PV_PLUGIN_PATH"].split(":")
                    lib=None
                    for d in dirs:
                        try:
                            lib=ctypes.CDLL(path.join(d,"libPV3FoamReader.so"),mode=ctypes.RTLD_GLOBAL)
                            break
                        except OSError:
                            pass
                    if not lib:
                        warning("Could not find libPV3FoamReader.so in",dirs)
                except ImportError:
                    error("The Workaround for Linux-Systems won't work because there is no ctypes library")

            plug1="libPV3FoamReader."+dyExt
            if foamVersion()>=(1,7):
                plug1=None

            plug2="libPV3FoamReader_SM."+dyExt

            loaded=False
            for p in environ["PV_PLUGIN_PATH"].split(":"):
                if path.exists(path.join(p,plug2)):
                    if version()>=(3,6):
                        LoadPlugin(path.join(p,plug2),ns=globals())
                        try:
                            if plug1:
                                LoadPlugin(path.join(p,plug1),ns=globals())
                            pass
                        except NameError:
                            print_(dir(self.module()))
                            pass
                    else:
                        if plug1:
                            servermanager.LoadPlugin(path.join(p,plug1))
                        servermanager.LoadPlugin(path.join(p,plug2))
                    loaded=True
                    break

            if not loaded:
                error("The plugin",plug2,"was not found in the PV_PLUGIN_PATH",environ["PV_PLUGIN_PATH"])
            if not "PV3FoamReader" in dir(servermanager.sources):
                error("The plugin was not properly loaded. PV3FoamReader not found in the list of sources")
        elif requiredReader=="OpenFOAMReader":
            if "ParaView_DIR" in environ:
                hasPlug=False
                for d in ["plugins","Plugins"]:
                    plug=path.join(environ["ParaView_DIR"],"bin",d,"libPOpenFOAMReaderPlugin."+dyExt)
                    if path.exists(plug):
                        LoadPlugin(plug)
                        hasPlug=True
                        break
                if not hasPlug:
                    warning("Can't find expected plugin 'libPOpenFOAMReaderPlugin' assuming that correct reader is compiled in. Wish me luck")
            else:
                warning("Can't plugin without ParaView_DIR-variable. Continuing without")
        else:
            warning("Loading of plugins for reader",requiredReader,"not implemented")

    def __getattr__(self,attr):
        """Delegate Attributes to the servermanager-module"""

        return getattr(servermanager,attr)

    def __setattr__(self,attr,val):
        """Delegate Attributes to the servermanager-module"""

        return setattr(servermanager,attr,val)

    def useSimple(self):
        return version()>(5,4)

    def module(self):
        """Return the actual module (for developing)"""
        if self.useSimple():
            # Old API seems not to work at 5.6
            return simple
        else:
            return servermanager

    def __call__(self):
        return self.module()

    def __del__(self):
        """Make sure that everything gets thrown out. Doesn't work"""
        for v in self.module().GetRenderViews():
            del v
        if self.con:
            if not self.useSimple():
                self.module().Disconnect(self.con)
            self.con=None
        #        self.module().Finalize()
