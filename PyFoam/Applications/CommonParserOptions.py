"""
Class that implements the common functionality for passing options to the parser
"""
from optparse import OptionGroup

class CommonParserOptions(object):
    """ The class that defines the options for the parser
    """

    def addOptions(self):
        parser=OptionGroup(self.parser,
                           "Parser Options",
                           "Options that control the behaviour of the parser for the dictionary files")
        self.parser.add_option_group(parser)
        parser.add_option("--debug-parser",
                          action="store_true",
                          default=None,
                          dest="debugParser"
                          ,help="Debugs the parser")

        parser.add_option("--no-header",
                          action="store_true",
                          default=False,
                          dest="noHeader",
                          help="Don't expect a header while parsing")

        parser.add_option("--no-body",
                          action="store_true",
                          default=False,
                          dest="noBody",
                          help="Don't expect a body while parsing (only parse the header)")

        parser.add_option("--boundary",
                          action="store_true",
                          default=False,
                          dest="boundaryDict",
                          help="Expect that this file is a boundary dictionary")

        parser.add_option("--list-only",
                          action="store_true",
                          default=False,
                          dest="listDict",
                          help="Expect that this file only contains a list")

        parser.add_option("--list-with-header",
                          action="store_true",
                          default=False,
                          dest="listDictWithHeader",
                          help="Expect that this file only contains a list with a header")

        parser.add_option("--unparsed-list-length",
                          action="store",
                          type="int",
                          default=None,
                          dest="listLengthUnparsed",
                          help="Lists longer than this are not parsed")

        parser.add_option("--do-macro-expansion",
                          action="store_true",
                          default=False,
                          dest="doMacros",
                          help="Expand macros with $ and #")


        parser.add_option("--no-preserve-comments",
                          action="store_false",
                          default=True,
                          dest="preserveComments",
                          help="Don't preserve comments when parsing")

        parser.add_option("--treat-binary-as-ascii",
                          action="store_true",
                          default=False,
                          dest="treatBinaryAsASCII",
                          help="Treat binary files as if they were ascii files")
