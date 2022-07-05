#  ICE Revision: $Id$
"""Parse options for the PyFoam-Scripts"""

from optparse import OptionParser,TitledHelpFormatter
import textwrap

from PyFoam import versionString

from PyFoam.FoamInformation import changeFoamVersion
from PyFoam.FoamInformation import oldAppConvention as oldApp

from PyFoam.Error import error,warning
from PyFoam.ThirdParty.six import iteritems
from PyFoam.ThirdParty.six import string_types,integer_types

from os import path,environ
from copy import deepcopy

class FoamHelpFormatter(TitledHelpFormatter):
    """For description and epilog preserve double newlines as one newline"""
    def format_description(self, description):
        if description:
            return "".join(
                 [TitledHelpFormatter.format_description(self,d) for d in description.split("\n\n")])
        else:
            return ""

    def format_epilog(self,epilog):
        if epilog:
            return "\n"+("-"*int(self.width/2))+"\n"+"".join(
                 [TitledHelpFormatter.format_epilog(self,d) for d in epilog.split("\n\n")])
        else:
            return ""

class FoamOptionParser(OptionParser):
    """Wrapper to the usual OptionParser to honor the conventions of OpenFOAM-utilities

    Options that are not used by the script are passed to the OpenFOAM-application"""

    def __init__(self,
                 args=None,
                 usage=None,
                 version=None,
                 description=None,
                 epilog=None,
                 examples=None,
                 interspersed=False):
        """
        :param usage: usage string. If missing a default is used
        :param version: if missing the PyFoam-version is used
        :param description: description of the utility
        :param epilog: Text to be displayed in the help after the options
        :param examples: Usage examples to be displayed after the epilog
        :param interspersed: needs to be false if options should be passed to an OpenFOAM-utility
        :param args: Command line arguments. If unset sys.argv[1:] is used.
        Can be a string: it will be splitted then unsing the spaces (very primitive), or a list of strings (prefered)
        """
        if usage==None:
            if oldApp():
                usage="%prog [options] <foamApplication> <caseDir> <caseName> [foamOptions]"
            else:
                usage="%prog [options] <foamApplication> [foamOptions]"

        if version==None:
            version="%prog "+versionString()

        if args==None:
            self.argLine=None
        elif type(args)==str:
            self.argLine=args.split()
        else:
            self.argLine=[str(a) for a in args]

        if examples:
            if epilog is None:
                epilog=""
            else:
                epilog+="\n\n"
            usageText="Usage examples:"
#            epilog+=usageText+"\n\n"+("="*len(usageText))+"\n\n"+examples
            epilog+=usageText+"\n\n"+examples

        OptionParser.__init__(self,
                              usage=usage,
                              # prog=self.__type__.__name__,
                              version=version,
                              description=description,
                              epilog=epilog,
                              formatter=FoamHelpFormatter())

        if self.epilog:
             self.epilog=self.expand_prog_name(self.epilog)

        if interspersed:
            self.enable_interspersed_args()
        else:
            self.disable_interspersed_args()

        self.options=None
        self.args=None

        self.__foamVersionChanged=False
        self.__oldEnvironment=None

    def restoreEnvironment(self):
        """Restore the environment to its old glory... if it was changed"""
        if self.__foamVersionChanged:
            #            print "Restoring the environment"
            environ.update(self.__oldEnvironment)

    def parse(self,nr=None,exactNr=True):
        """
        parse the options
        :param nr: minimum number of arguments that are to be passed to the application
        3 is default for pre-1.5 versions of OpenFOAM
        """
        (self.options,self.args)=self.parse_args(args=self.argLine)

        if "foamVersion" in dir(self.options):
            if self.options.foamVersion!=None:
                if self.options.force32 and self.options.force64:
                    error("A version can't be 32 and 64 bit at the same time")

                self.__foamVersionChanged=True
                self.__oldEnvironment=deepcopy(environ)

                changeFoamVersion(self.options.foamVersion,
                                  force64=self.options.force64,
                                  force32=self.options.force32,
                                  compileOption=self.options.compileOption,
                                  foamCompiler=self.options.foamCompiler,
                                  wmCompiler=self.options.wmCompiler)
            elif self.options.force32 or self.options.force64:
                warning("Forcing version to be 32 or 64 bit, but no version chosen. Doing nothing")
            elif self.options.compileOption:
                warning("No OpenFOAM-version chosen. Can't set compile-option to",self.options.compileOption)

        if nr==None:
            if oldApp():
                nr=3
            else:
                nr=1

        if len(self.args)<nr:
            self.error("Too few arguments (%d needed, %d given)" %(nr,len(self.args)))

        maxNr=nr
        if not oldApp():
            if "-case" in self.args:
                maxNr+=2

        if exactNr and len(self.args)>maxNr:
            self.error("Too many arguments (%d needed, %d given)" %(nr,len(self.args)))

        tmp=self.args
        self.args=[]
        for a in tmp:
            if (a.find(" ")>=0 or a.find("(")>=0) and a.find('"')<0:
                a="\""+a+"\""
            self.args.append(a)

    def getArgs(self):
        """Return the arguments left after parsing"""
        if self.args!=None:
            return self.args
        else:
            return []

    def getApplication(self):
        """Return the OpenFOAM-Application to be run"""
        if self.args!=None:
            return self.args[0]
        else:
            return None

    def getOptions(self):
        """Return the options"""
        if self.options==None:
            self.error("options have not been parsed yet")

        return self.options

    def casePath(self):
        """Returns the path to the case (if applicable)"""
        if oldApp():
            return path.join(self.getArgs()[1],self.getArgs()[2])
        else:
            if "-case" in self.getArgs():
                return path.normpath(self.getArgs()[self.getArgs().index("-case")+1])
            else:
                return path.abspath(path.curdir)

    def _buildKeyordArgumentList(self):
        """Go through the lists of options and build a dictionary of keyword
        arguments (in CamelCase)"""
        kwArgs={}
        for og in self.option_groups:
            for o in og.option_list:
                raw=o.get_opt_string().strip("-")
                pos=raw.find("-")
                if pos<0:
                    name=raw.lower()
                    raw=""
                else:
                    name=raw[:pos].lower()
                    raw=raw[pos:].strip("-")
                while len(raw)>0:
                    pos=raw.find("-")
                    if pos<0:
                        name+=raw.capitalize()
                        raw=""
                    else:
                        name+=raw[:pos].capitalize()
                        raw=raw[pos:].strip("-")
                if not name[0].isalpha() and name[0]!="_":
                    error("Option",o.get_opt_string(),"reduces to",name,
                          "with invalid first character")
                # Remove all characters that do not belong in a valid Python-name
                name="".join([c for c in name if c=="_" or c.isalnum])
                if name in kwArgs:
                    error("Keyword arguement",name,"appears at least twice")
                kwArgs[name]=o

        return kwArgs

    def processKeywordArguments(self,kw):
        kwArgs=self._buildKeyordArgumentList()
        for k,v in iteritems(kw):
            if k not in kwArgs:
                raise TypeError("Unknown keyword argument",k,"in",
                                sorted(kwArgs.keys()))
            o=kwArgs[k]
            if o.action=="store_true":
                if type(v)!=bool:
                    raise TypeError("Keyword argument",k,"needs a bool")
                setattr(self.values,o.dest,v)
            elif o.action=="store_false":
                if type(v)!=bool:
                    raise TypeError("Keyword argument",k,"needs a bool")
                setattr(self.values,o.dest,not v)
            elif o.action=="store":
                if o.type:
                    if o.type=="string":
                        if not isinstance(v,string_types) and v!=o.default and o.default!=None:
                            raise TypeError("Keyword argument",k,"must be string or",o.default,". Is a ",type(v))
                    elif o.type in ("int","long"):
                        if not isinstance(v,integer_types):
                            raise TypeError("Keyword argument",k,"must be an integer. Is a ",type(v))
                    elif o.type=="float":
                        if not isinstance(v,integer_types+(float,)):
                            raise TypeError("Keyword argument",k,"must be float. Is a ",type(v))
                    elif o.type=="choice":
                        if v not in o.choices:
                            raise TypeError("Keyword argument",k,"must be one of",o.choices)
                    else:
                        raise RuntimeError("Type",o.type,"not implemented")
                setattr(self.values,o.dest,v)
            elif o.action=="append":
                oldVal=getattr(self.values,o.dest)
                if type(oldVal) not in (list,tuple):
                    if not type(v) in (list,tuple):
                        raise TypeError("Keyword argument",k,"must be a list or a tuple")
                    setattr(self.values,o.dest,v)
                else:
                    if type(v) in (list,tuple):
                        setattr(self.values,o.dest,oldVal+v)
                    else:
                        oldVal.append(v)
            elif o.action=="store_const":
                setattr(self.values,o.dest,o.const)
            elif o.action=="append_const":
                getattr(self.values,o.dest).append(o.const)
            elif o.action=="count":
                oldVal=getattr(self.values,o.dest)
                setattr(self.values,o.dest,oldVal+1)
            else:
                raise RuntimeError("Action",o.action,"not implemented")

class Subcommand(object):
     """A subcommand of a root command-line application that may be
     invoked by a SubcommandOptionParser.
     Taken from https://gist.github.com/sampsyo/462717
     """
     def __init__(self,
                  name,
                  parser=None,
                  help='',
                  aliases=(),
                  nr=None,
                  exactNr=None):
          """Creates a new subcommand. name is the primary way to invoke
          the subcommand; aliases are alternate names. parser is an
          OptionParser responsible for parsing the subcommand's options.
          help is a short description of the command. If no parser is
          given, it defaults to a new, empty OptionParser.
          """
          self.name = name
          self.parser = parser or OptionParser()
          self.aliases = aliases
          self.help = help
          self.nr=nr
          self.exactNr=exactNr

class SubcommandFoamOptionParser(FoamOptionParser):
     """Subclass of the regular option parser that allows setting subcommands
     Inspired by https://gist.github.com/sampsyo/462717
     """

     # A singleton command used to give help on other subcommands.
     _HelpSubcommand = Subcommand('help', OptionParser(),
                                  help='give detailed help on a specific sub-command',
                                  aliases=('?',))

     def __init__(self,
                  args=None,
                  usage=None,
                  version=None,
                  epilog=None,
                  examples=None,
                  description=None,
                  subcommands=[]):
          """
          :param usage: usage string. If missing a default is used
          :param version: if missing the PyFoam-version is used
          :param description: description of the utility
          :param subcommands: list with subcommands to prepopulate the parser
          :param args: Command line arguments. If unset sys.argv[1:] is used.
          Can be a string: it will be splitted then unsing the spaces (very primitive), or a list of strings (prefered)
          """
          if usage==None:
               usage="""
%prog [general options ...] COMMAND [ARGS ...]
%prog help COMMAND"""

          FoamOptionParser.__init__(self,
                                    args,
                                    usage,
                                    version,
                                    description=description,
                                    epilog=epilog,
                                    examples=examples,
                                    interspersed=False)

          self.subcommands=subcommands[:]
          self.addSubcommand(self._HelpSubcommand)

          # Adjust the help-visible name of each subcommand.
          for subcommand in self.subcommands:
               subcommand.parser.prog = '%s %s' % \
                                        (self.get_prog_name(), subcommand.name)

          self.cmdname=None
          self.__subopts=None
          self.subargs=None

     def addSubcommand(self,cmd,usage=None):
         if usage==None:
             cmd.parser.usage=self.usage
         else:
             cmd.parser.usage=usage
         cmd.parser.formatter=TitledHelpFormatter()
         self.subcommands.append(cmd)

     # Add the list of subcommands to the help message.
     def format_help(self, formatter=None):
          """Taken from https://gist.github.com/sampsyo/462717"""
          # Get the original help message, to which we will append.
          out = OptionParser.format_help(self, formatter)
          if formatter is None:
               formatter = self.formatter

          # Subcommands header.
          result = ["\n"]
          result.append(formatter.format_heading('Commands'))
          formatter.indent()

          # Generate the display names (including aliases).
          # Also determine the help position.
          disp_names = []
          help_position = 0
          for subcommand in self.subcommands:
               name = subcommand.name
               if subcommand.aliases:
                    name += ' (%s)' % ', '.join(subcommand.aliases)
               disp_names.append(name)

               # Set the help position based on the max width.
               proposed_help_position = len(name) + formatter.current_indent + 2
               if proposed_help_position <= formatter.max_help_position:
                    help_position = max(help_position, proposed_help_position)

          # Add each subcommand to the output.
          for subcommand, name in zip(self.subcommands, disp_names):
               # Lifted directly from optparse.py.
               name_width = help_position - formatter.current_indent - 2
               if len(name) > name_width:
                    name = "%*s%s\n" % (formatter.current_indent, "", name)
                    indent_first = help_position
               else:
                    name = "%*s%-*s " % (formatter.current_indent, "",
                                         name_width, name)
                    indent_first = 0
               result.append(name)
               help_width = formatter.width - help_position
               help_lines = textwrap.wrap(subcommand.help, help_width)
               result.append("%*s%s\n" % (indent_first, "", help_lines[0]))
               result.extend(["%*s%s\n" % (help_position, "", line)
                              for line in help_lines[1:]])
          formatter.dedent()

          # Concatenate the original help message with the subcommand
          # list.
          return out + "".join(result)

     def parse(self,nr=None,exactNr=None):
          """Do the parsing of a subcommand"""
          if nr or exactNr:
               self.error("For calling this implementention no setting of nr and exactNr is valid")

          FoamOptionParser.parse(self,nr=1,exactNr=False)

          if not self.args:
               # no command
               self.print_help()
               self.exit()
          else:
               cmdname=self.args.pop(0)
               subcommand = self._subcommand_for_name(cmdname)
               if not subcommand:
                    self.error('unknown command ' + cmdname)

          # make sure we get the canonical name
          self.cmdname=subcommand.name

          nr=subcommand.nr
          exactNr=subcommand.exactNr

          if subcommand is not self._HelpSubcommand:
              subcommand.parser.usage=subcommand.parser.usage.replace("COMMAND",cmdname)

          self.__subopts,self.subargs=subcommand.parser.parse_args(self.args)
          if nr!=None:
              if len(self.subargs)<nr:
                  self.error("Too few arguments for %s (%d needed, %d given)" %(cmdname,nr,len(self.subargs)))

              maxNr=nr
              if exactNr and len(self.subargs)>maxNr:
                  self.error("Too many arguments for %s (%d needed, %d given)" %(cmdname,nr,len(self.subargs)))

          if subcommand is self._HelpSubcommand:
               if self.subargs:
                    # help on a specific command
                    cmdname=self.subargs[0]
                    helpcommand = self._subcommand_for_name(cmdname)
                    if helpcommand!=None:
                        helpcommand.parser.usage=helpcommand.parser.usage.replace("COMMAND",cmdname)
                        helpcommand.parser.print_help()
                    else:
                        self.print_help()
                    self.exit()
               else:
                    # general
                    self.print_help()
                    self.exit()
          self.options._update_loose(self.__subopts.__dict__)

     def getArgs(self):
         """Return the arguments left after parsing"""
         if self.subargs!=None:
             return self.subargs
         else:
             return []

     def _subcommand_for_name(self, name):
          """Return the subcommand in self.subcommands matching the
          given name. The name may either be the name of a subcommand or
          an alias. If no subcommand matches, returns None.
          """
          for subcommand in self.subcommands:
               if name == subcommand.name or \
                  name in subcommand.aliases:
                    return subcommand

          return None
