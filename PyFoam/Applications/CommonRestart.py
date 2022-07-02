"""
Class that implements the common functionality for restarting cases
"""

class CommonRestart(object):
    """ The class that restarts the case
    """

    def addOptions(self):
        self.ensureGeneralOptions()
        self.generalOpts.add_option("--restart",
                                    action="store_true",
                                    default=False,
                                    dest="restart",
                                    help="Restart the simulation from the last time-step")
                
        
