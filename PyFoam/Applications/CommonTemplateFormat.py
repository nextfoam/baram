"""
Class that implements the common functionality for the format of templates
"""
from optparse import OptionGroup

from PyFoam import configuration as config

class CommonTemplateFormat(object):
    """ The class that defines options for template formats
    """

    def addOptions(self):
        tformat=OptionGroup(self.parser,
                            "Format",
                           "Specifying details about the format of the pyratemp-templates (new format)")
        self.parser.add_option_group(tformat)
        tformat.add_option("--expression-delimiter",
                           action="store",
                           default=config().get("Template","expressionDelimiter"),
                           dest="expressionDelimiter",
                           help="String that delimits an expression. At the end of the expression the reverse string is being used. Default: %default")
        tformat.add_option("--assignment-line-start",
                           action="store",
                           default=config().get("Template","assignmentLineStart"),
                           dest="assignmentLineStart",
                           help="String at the start of a line that signifies that this is an assignment. Default: %default")
