"""A simple hook that only prints a user-specified message"""

from PyFoam.Infrastructure.RunHook import RunHook
from PyFoam.ThirdParty.six import print_

class PrintMessageHook(RunHook):
    """Print a small message"""
    def __init__(self,runner,name):
        RunHook.__init__(self,runner,name)

        self.message=self.conf().get("message")

    def __call__(self):
         print_(self.message)

# Should work with Python3 and Python2
