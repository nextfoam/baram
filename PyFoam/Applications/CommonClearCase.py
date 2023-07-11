"""
Class that implements the common functionality for clearing the cases
"""

from PyFoam.ThirdParty.six import print_

class CommonClearCase(object):
    """ The class that clears the case
    """

    def addOptions(self):
        self.ensureGeneralOptions()
        self.generalOpts.add_option("--clear-case",
                                    action="store_true",
                                    default=False,
                                    dest="clearCase",
                                    help="Clear all timesteps except for the first before running")
        self.generalOpts.add_option("--complete-clear",
                                    action="store_true",
                                    default=False,
                                    dest="clearComplete",
                                    help="Like clear-case but removes the function-object data as well")
        self.generalOpts.add_option("--pyfoam-stuff-clear",
                                    action="store_true",
                                    dest="pyfoam",
                                    default=False,
                                    help="Keep the PyFoam-specific directories and logfiles. Will only be used with '--clear-case'")
        self.generalOpts.add_option("--additional-clear",
                                    action="append",
                                    dest="additionalClear",
                                    default=[],
                                    help="Glob-pattern with additional files to be removes. Can be used more than once. Will only be used with '--clear-case'")
        self.generalOpts.add_option("--history-clear",
                                    action="store_true",
                                    dest="clearHistory",
                                    default=False,
                                    help="Clear the PyFoamHistory-file. Will only be used with '--clear-case'")
        self.generalOpts.add_option("--remove-processor-dirs",
                                    action="store_true",
                                    dest="removeProcessorDirs",
                                    default=False,
                                    help="Remove the whole processor directories")
        self.generalOpts.add_option("--keep-postprocessing",
                                    action="store_true",
                                    dest="keepPostprocessing",
                                    default=False,
                                    help="Keep the directory 'postProcessing' where functionObjects write their stuff")
        self.generalOpts.add_option("--verbose-clear",
                                    action="store_true",
                                    dest="verboseClear",
                                    default=False,
                                    help="Print what is being cleared during clearing")

    def clearCase(self,sol,runParallel=False):
        if not self.opts.keepPostprocessing:
            self.opts.additionalClear.append("postProcessing")
        if self.opts.clearComplete:
            self.opts.clearCase=True
        if self.opts.clearCase:
            print_("Clearing out old timesteps ....")
            sol.clear(additional=self.parser.getOptions().additionalClear,
                      verbose=self.parser.getOptions().verboseClear,
                      processor=self.parser.getOptions().removeProcessorDirs and not runParallel,
                      pyfoam=self.parser.getOptions().pyfoam,
                      clearHistory=self.parser.getOptions().clearHistory,
                      functionObjectData=self.opts.clearComplete)

# Should work with Python3 and Python2
