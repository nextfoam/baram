"""
Class that implements the common functionality for cases with multiple regions
"""

from optparse import OptionGroup

from PyFoam.FoamInformation import oldAppConvention as oldApp

class CommonMultiRegion(object):
    """ The class that looks for multiple mesh regions
    """

    def addOptions(self):
        grp=OptionGroup(self.parser,
                        "Multiple regions",
                        "Treatment of cases with multiple mesh regions")
        grp.add_option("--all-regions",
                       action="store_true",
                       default=False,
                       dest="regions",
                       help="Executes the command for all available regions (builds a pseudo-case for each region)")

        grp.add_option("--region",
                       dest="region",
                       action="append",
                       default=None,
                       help="Executes the command for a region (builds a pseudo-case for that region). A value of 'region0' is the default region")

        grp.add_option("--keep-pseudocases",
                       action="store_true",
                       default=False,
                       dest="keeppseudo",
                       help="Keep the pseudo-cases that were built for a multi-region case")
        self.parser.add_option_group(grp)


    def buildRegionArgv(self,case,region):
        args=self.parser.getArgs()[:]
        if oldApp():
            if region!=None:
                args[2]+="."+region
        else:
            if region!=None:
                if "-case" in args:
                    args[args.index("-case")+1]=case+"."+region
                else:
                    args+=["-case",case+"."+region]
        return args
