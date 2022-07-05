"""
Class that implements the common functionality for executing hooks before and
after the running of the solver
"""
from optparse import OptionGroup
from PyFoam.ThirdParty.six.moves import configparser

from PyFoam import configuration
from PyFoam.Error import FatalErrorPyFoamException

from PyFoam.ThirdParty.six import print_,iteritems

import traceback

import sys

class CommonPrePostHooks(object):
    """ The class that runs the hooks
    """

    def addOptions(self, auto_enable=True):
        grp=OptionGroup(self.parser,
                        "Pre- and Postrun hooks",
                        "These options control the hooks that are either specified in the 'LocalConfigPyFoam' of the case or other config files (for a system-wide configuration)")
        self.parser.add_option_group(grp)

        if auto_enable:
            grp.add_option("--disable-pre-hooks",
                           action="store_false",
                           dest="runPreHook",
                           default=True,
                           help="Disable running of hooks before the solver")
            grp.add_option("--disable-post-hooks",
                           action="store_false",
                           dest="runPostHook",
                           default=True,
                           help="Disable running of hooks after the solver")
        else:
            grp.add_option("--enable-pre-hooks",
                           action="store_true",
                           dest="runPreHook",
                           default=False,
                           help="Enable running of hooks before the solver")
            grp.add_option("--enable-post-hooks",
                           action="store_true",
                           dest="runPostHook",
                           default=False,
                           help="Enable running of hooks after the solver")
        grp.add_option("--disable-all-hooks",
                       action="store_true",
                       dest="disableAllHooks",
                       default=False,
                       help="Disable running of hooks before and after the solver")
        grp.add_option("--verbose-hooks",
                       action="store_true",
                       dest="verboseHooks",
                       default=False,
                       help="Be more informative about what is going on")
        grp.add_option("--list-hooks",
                       action="store_true",
                       dest="listHooks",
                       default=False,
                       help="List the installed hooks")
        grp.add_option("--hook-errors-are-fatal",
                       action="store_true",
                       dest="hookErrorsFatal",
                       default=False,
                       help="If there are problems with the hooks then execution of the runner stops")

    def _hookmessage(self,*args):
        if self.opts.verboseHooks:
            print_(*args)

    def _stopExecutionOnHookError(self,spec=False):
         if spec or self.opts.hookErrorsFatal:
              self.error("Stopping because of error in hook")

    def runPreHooks(self):
        """Run the hooks before the execution of the solver"""
        if self.opts.runPreHook:
            self._hookmessage("Running pre-hooks")
            for h,spec in iteritems(self.preHookInstances):
                self._executeHook(h,spec)
        else:
            self._hookmessage("Pre-hooks disabled")

    def runPostHooks(self):
        """Run the hooks after the execution of the solver"""
        if self.opts.runPostHook:
            self._hookmessage("Running post-hooks")
            for h,spec in iteritems(self.postHookInstances):
                self._executeHook(h,spec)
        else:
            self._hookmessage("Post-hooks disabled")
        pass

    def _executeHook(self,name,hDict):
        try:
            passed=self.getData()["wallTime"]
        except KeyError:
            passed=0
        if passed<hDict["minRunTime"]:
            self._hookmessage("Skipping",name,"because passed time",
                             passed,"smaller than",hDict["minRunTime"])
            return
        self._hookmessage("Executing hook",name)
        try:
             hDict["instance"]()
        except FatalErrorPyFoamException:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'

            self.warning("Problem executing",name,":",e)
        except Exception:
             self.warning("Problem while executing",
                          name,":",traceback.format_exc())
             self._stopExecutionOnHookError(hDict["stopOnError"])

    def prepareHooks(self):
        """Prepare the hooks and output additional info if wanted"""
        self._hookmessage("Preparing hooks")
        if self.opts.disableAllHooks:
            self._hookmessage("Disabling all hooks")
            self.opts.runPreHook=False
            self.opts.runPostHook=False

        if self.opts.listHooks:
            print_("Hooks to execute before run")
            print_("---------------------------")
            self._dumpHooks(self._getHooksWithPrefix("preRunHook"))
            print_()
            print_("Hooks to execute after run")
            print_("--------------------------")
            self._dumpHooks(self._getHooksWithPrefix("postRunHook"))

        self.preHookInstances={}
        self.postHookInstances={}

        self._hookmessage("Creating pre-hooks")
        if self.opts.runPreHook:
            self._checkAndCreateHookInstances(
                self.preHookInstances,
                "preRunHook"
            )
        self._hookmessage("Creating post-hooks")
        if self.opts.runPostHook:
            self._checkAndCreateHookInstances(
                self.postHookInstances,
                "postRunHook"
            )

    def _checkAndCreateHookInstances(self,toDict,prefix):
        for h in self._getHooksWithPrefix(prefix):
            self._hookmessage("Checking",h)
            if configuration().getboolean(h,"enabled",default=True):
                subdict={}
                modName=configuration().get(h,"module",default="")
                if modName=="":
                    self.warning("No module specified for",h)
                    continue
                subdict["minRunTime"]=configuration().getfloat(h,
                                                               "minRunTime",
                                                               default=-1)
                subdict["stopOnError"]=configuration().getboolean(h,
                                                                  "stopOnError",
                                                                  default=False)
                self._hookmessage("Trying to import",modName)

                module=None
                modNames=[modName,
                          "PyFoam.Site."+modName,
                          "PyFoam.Infrastructure.RunHooks."+modName]
                for mod in modNames:
                    try:
                        self._hookmessage("Trying module:",mod)
                        module=__import__(mod,globals(),locals(),["dummy"])
                        self._hookmessage("Got module:",mod)
                        break
                    except ImportError:
                        e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                        self._hookmessage("ImportError:",e,"for",modName)
                    except SyntaxError:
                        e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                        self._hookmessage("SyntaxError:",e)
                        self.warning("Syntax error when trying to import",mod)
                        break
                if module is None:
                    self.warning("Could not import module",modName,
                                 "for",h,"(Tried",", ".join(modNames),")")
                    continue

                try:
                    theClass=getattr(module,mod.split(".")[-1])
                except AttributeError:
                    e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                    self._hookmessage("AttributeError:",e)
                    self._hookmessage("Attributes:",dir(module))
                    self.warning("Class",mod.split(".")[-1],"missing form",
                             mod)
                    continue
                try:
                    subdict["instance"]=theClass(self,h)
                except Exception:
                    self.warning("Problem while creating instance of",
                                 theClass,":",traceback.format_exc())
                    self._stopExecutionOnHookError(subdict["stopOnError"])
                    continue
                toDict[h]=subdict
            else:
                self._hookmessage(h,"is disabled")

    def _dumpHooks(self,lst):
        for h in lst:
            print_(h)
            try:
                print_("  enabled:",configuration().getboolean(h,
                                                               "enabled",
                                                               default=True))
                print_("  module:",configuration().get(h,
                                                       "module"))
                print_("  minRunTime:",configuration().getfloat(h,
                                                                "minRunTime",
                                                                default=0))
                print_("  description:",configuration().get(h,
                                                            "description",
                                                            default="None"))
            except configparser.NoOptionError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                self.error("Hook",h,"incompletely defined (",e,")")

    def _getHooksWithPrefix(self,prefix):
        lst=[]
        for h in configuration().sections():
            if h.find(prefix+"_")==0:
                lst.append(h)
        return lst

# Should work with Python3 and Python2
