#  ICE Revision: $Id: TemplateFile.py,v de6dbd122d11 2020-02-25 11:02:08Z bgschaid $

import re
from math import *
import sys

from PyFoam.Error import error,warning
from PyFoam.ThirdParty.pyratemp import Template as PyratempTemplate
from PyFoam.ThirdParty.pyratemp import EvalPseudoSandbox,TemplateRenderError
from PyFoam.ThirdParty.pyratemp import Renderer as PyratempRenderer

from PyFoam.ThirdParty.six import iteritems,exec_,print_,PY3

class RendererWithFilename(PyratempRenderer):
     """Usual renderer but report a filename"""

     def __init__(self, evalfunc, escapefunc,filename=None):
          PyratempRenderer.__init__(self, evalfunc, escapefunc)

          self.fileName = filename

     def reportString(self,expr, err):
          result="Cannot eval expression '%s'. (%s: %s)" %(expr, err.__class__.__name__, err)
          if self.fileName:
               result+=" in file "+self.fileName
          return result

     def _eval(self, expr, data):
          """evalfunc with error-messages"""
          try:
               return self.evalfunc(expr, data)
          except (TypeError,NameError,IndexError,KeyError,AttributeError, SyntaxError):
              err = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
              raise TemplateRenderError(self.reportString(expr,err))

class TolerantRenderer(RendererWithFilename):
     """Variant of the renderer that doesn't choke on problems with evaluations"""

     def __init__(self, evalfunc, escapefunc,filename=None):
          RendererWithFilename.__init__(self, evalfunc, escapefunc,filename=filename)

     def _eval(self, expr, data):
          """evalfunc with error-messages"""
          try:
               return self.evalfunc(expr, data)
          except (TypeError,NameError,IndexError,KeyError,AttributeError, SyntaxError):
              err = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
              warning(self.reportString(expr,err))
              return "Template evaluation ERROR: "+self.reportString(expr,err)

execIdString="this is meant to be executed:"
substituteIdString="substitute current values into this string:"

class PyratempPreprocessor(object):
    """This class preprocesses the input that is give to it in such a
    way that the old format (using $$ at the line beginnings and $
    .. $ for expressions) is reworked into something that pyratemp understands
    """
    def __init__(self,
                 dovarline=True,
                 doexpr=True,
                 expressionDelimiter="$",
                 assignmentLineStart="$$",
                 allowExec=False,
                 assignmentDebug=None,
                 specials=[]):
        """Create the regexp once for performance reasons
        :param dovarline: look for variable lines that start with $$
        :param doexpr: substitute expressions that are between $
        :param expressionDelimiter: character/string that is used before and after an
        expression. After the expression the reverse of the string is used
        :param assignmentLineStart: character sequence that signals an assignment line
        :param assignmentDebug: Add a commented line to debug assignments. Prefix used is this parameter
        :param allowExec: allows execution of code. This is potentially unsafe
        :param specials: a list. If any expression starts with one of these values then
        the full expression (including delimiters) is left verbatim in the template"""

        self.clip=len(expressionDelimiter)
        self.specials=specials

        tmp=list(expressionDelimiter)
        tmp.reverse()

        self.expressionDelimiter=re.escape(expressionDelimiter)
        self.expressionDelimiterEnd=re.escape("".join(tmp))
        self.expressionDelimiterRaw=expressionDelimiter
        self.expressionDelimiterEndRaw="".join(tmp)

        #        print self.expressionDelimiter,self.expressionDelimiterEnd

        self.assignmentLineStart=assignmentLineStart
        self.assignmentDebug=assignmentDebug

        self.expr=re.compile("%s[^$!\n]+?%s" % (self.expressionDelimiter,self.expressionDelimiterEnd))
        self.dovarline=dovarline
        self.doexpr=doexpr

        self.allowExec=allowExec

    def __call__(self,original):
        """This does the actual work"""

        if len(original)==0:
            return original

        lines=original.split("\n")
        if lines[-1]=="":
            lines=lines[:-1]

        result=""

        def isVarname(name):
            return re.match("[_A-Za-z][_A-Za-z0-9]*$",name.strip())!=None

        for l in lines:
            skipLine=False
            if l[:len(self.assignmentLineStart)]==self.assignmentLineStart and self.dovarline:
                tmp=l[len(self.assignmentLineStart):].split("=")
                if len(tmp)!=2 or not isVarname(tmp[0]):
                    if self.allowExec:
                        execString=l[len(self.assignmentLineStart):].replace("\\","\\\\").replace("\"","\\\"")
                        result+='$!setvar("%s", "%s")!$#!' % (
                            "dummyVarForExecution",
                            execIdString+execString.strip()
                        )
                        result+="\n"
                        skipLine=True
                    else:
                        error("Each definition must be of the form: <name>=<value>",
                              "The string",l,"is not. Try running the utility with the option --allow-exec-instead-of-assignment")
                else:
                    #                if tmp[1].find('"')>=0:
                    #                   error("There is a \" in",tmp[1],"\npyratemp can't cope with that'")
                    exprStr=tmp[1].replace("\\","\\\\").replace("\"","\\\"")
                    result+='$!setvar("%s", "%s")!$#!' % (tmp[0].strip(),exprStr.strip())
                    result+="\n"
                    if self.assignmentDebug and self.doexpr:
                         l=self.assignmentDebug+" "+tmp[0].strip()+" "+self.expressionDelimiterRaw+tmp[0].strip()+self.expressionDelimiterEndRaw
                    else:
                         continue
            elif self.doexpr:
                nl=""
                iStart=0
                for m in self.expr.finditer(l):
                    inner=l[m.start()+self.clip:m.end()-self.clip]
                    hasSpecial=False
                    nl+=l[iStart:m.start()]
                    for k in self.specials:
                        if len(k)<=len(inner):
                            if inner[:len(k)]==k:
                                hasSpecial=True
                                substVarName="dummyVarForSubstitution"
                                #                                nl+=l[m.start():m.end()]
                                nl+='$!setvar("%s", "%s")!$#!\n' % (
                                    substVarName,
                                    substituteIdString+l[m.start():m.end()]
                                )
                                nl+='$!'+substVarName+'!$'

                    if not hasSpecial:
                        nl+="$!"+inner+"!$"
                    iStart=m.end()
                result+=nl+l[iStart:]+"\n"
            else:
                if not skipLine:
                    result+=l+"\n"

        # remove trailing newline if the original had none
        if original[-1]!='\n' and result[-1]=='\n':
            result=result[:-1]

        return result

class TemplateFileOldFormat(object):
    """Works on template files. Does calculations between $$.
    Lines that start with $$ contain definitions"""

    def __init__(self,name=None,content=None):
        """Exactly one of the parameters must be specified
        :param name: name of the template file.
        :param content: Content of the template"""
        if name==None and content==None:
            error("Either a file name or the content of the template must be specified")
        if name!=None and content!=None:
            error("Both: a file name and the content of the template were specified")
        if content!=None:
            template=content
        else:
            template=open(name).read()
        self.buildTemplate(template)

    def buildTemplate(self,template):
        lines=template.split("\n")
        self.expressions={}
        self.template=""
        for l in lines:
            if l[:2]!="$$":
                self.template+=l+"\n"
            else:
                tmp=l[2:].split("=")
                if len(tmp)!=2:
                    error("Each definition must be of the form: <name>=<value>",
                          "The string",l,"is not")
                self.expressions[tmp[0].strip()]=tmp[1]

    def writeToFile(self, outfile, vals, gzip=False):
        """In  the template, replaces all the strings between $$
        with the evaluation of the expressions and writes the results to a file
        :param outfile: the resulting output file
        :param vals: dictionary with the values
        :param gzip: Zip the file (and add a .gz to the name)"""

        from os import path

        output = self.getString(vals)

        if path.splitext(outfile) == ".gz":
            gzip = True
        elif path.exists(outfile + ".gz"):
            outfile += ".gz"
            gzip = True
        elif gzip:
            outfile += ".gz"

        if gzip:
            import gzip as gz
            if PY3:
                output = output.encode()
            gz.open(outfile, "wb").write(output)
            unzipped=path.splitext(outfile)[0]
            if path.exists(unzipped):
                 warning("Removing",unzipped,"because it might shadow generated",
                         outfile)
                 from os import unlink
                 unlink(unzipped)
        else:
            open(outfile, "w").write(output)

        return outfile

    def getString(self,vals):
        """In the template, replaces all the strings between $$
        with the evaluation of the expressions
        :param vals: dictionary with the values
        :returns: The string with the replaced expressions"""

        symbols=vals.copy()

        exp=re.compile("\$[^$\n]*\$")

        for n,e in iteritems(self.expressions):
            if n in vals:
                error("Key",n,"already existing in",vals)
            symbols[n]="("+str(e)+")"

        keys=list(symbols.keys())

        keys.sort(key=len,reverse=True)

        input=self.template[:]
        m=exp.search(input)
        while m:
            a,e=m.span()
            pre=input[0:a]
            post=input[e:]
            mid=input[a+1:e-1]

            old=""
            while old!=mid:
                old=mid
                for k in keys:
                    if mid.find(k)>=0:
                        mid=mid.replace(k,str(symbols[k]))
                        break

            try:
                input=pre+str(eval(mid))+post
            except ArithmeticError:
                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                print_("Problem evaluating",mid)
                raise e

            m=exp.search(input)

        return input

class EvalPseudoSandboxWithMath(EvalPseudoSandbox):
    """Add mathematical functions to the valid functons"""
    def __init__(self,allowExec=False):
        EvalPseudoSandbox.__init__(self)
        import math
        for o in dir(math):
            if o[0]!="_":
                self.register(o,getattr(math,o))

        from PyFoam.ThirdParty.six.moves import builtins as __builtin__
        self.register("set",__builtin__.set)

        if allowExec:
            del self.eval_allowed_globals["__import__"]
            self.register("__import__",__builtins__["__import__"])

    def compile(self, expr,mode="eval"):
        """Compile a python-eval-expression. Overrides the default implementation
        to allow '_[1]' as a valid name
        """
        if expr not in self._compile_cache:
            c = compile(expr, "", mode)
            for i in c.co_names:    #prevent breakout via new-style-classes
                if i[0] == '_':
                     if i[1]!='[' or i[-1]!=']':
                          raise NameError("Name '%s' is not allowed." %(i))
            self._compile_cache[expr] = c
        return self._compile_cache[expr]

    def eval(self, expr, locals):
        """Eval a python-eval-expression.

        Sets ``self.locals_ptr`` to ``locales`` and compiles the code
        before evaluating.
        """

        if expr[:len(substituteIdString)]==substituteIdString:
            goOn=True
            replacement=expr[len(substituteIdString):]
            while goOn:
                try:
                    value=replacement % locals
                    goOn=False
                except KeyError:
                    e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                    kExpr="%("+e.args[0]+")"
                    replacement=replacement.replace(kExpr,"%"+kExpr)

            return value
            #            print value

        sav = self.locals_ptr
        self.locals_ptr = locals
        doEval=True

        if expr[:len(execIdString)]==execIdString:
            doEval=False

        if doEval:
            globals= {"__builtins__":self.eval_allowed_globals}
            if PY3:
                 globals.update(locals)
            try:
                 x = eval(self.compile(expr),globals, locals)
            except:
                 e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                 print_("Problem avaluating",expr,":",e)
                 raise e
        else:
            #            globals= {"__builtins__":self.eval_allowed_globals}
            globals= {"__builtins__":__builtins__}
            expr=expr[len(execIdString):]
            exec_(self.compile(expr,mode="exec"),globals,locals)
            x = None
        self.locals_ptr = sav
        return x

class EvalPseudoSandboxWithMathWithImport(EvalPseudoSandboxWithMath):
    """Class that allows the import of packages"""
    def __init__(self):
        EvalPseudoSandboxWithMath.__init__(self,allowExec=True)

class TemplateFile(TemplateFileOldFormat):
    """Works on template files. Does calculations between $$.
    Lines that start with $$ contain definitions"""

    def __init__(self,
                 name=None,
                 content=None,
                 encoding="utf-8",
                 expressionDelimiter="|",
                 assignmentLineStart="$$",
                 assignmentDebug=None,
                 specials=[],
                 renderer_class=None,
                 tolerantRender=False,
                 allowExec=False
             ):
        """Exactly one of the parameters must be specified
        :param name: name of the template file.
        :param content: Content of the template
        :param expressionDelimiter: character/string that delimits expression strings.
        :param assignmentLineStart: Start of a line that holds an assignment operation
        :param assignmentDebug: Add a commented line to debug assignments. Prefix used is this parameter
        :param allowExec: allow execution  (and import). This is potentially unsafe
        :param special: list with strings that leave expression untreated"""

        self.expressionDelimiter=expressionDelimiter
        self.assignmentLineStart=assignmentLineStart
        self.assignmentDebug=assignmentDebug
        self.specials=specials
        self.allowExec=allowExec

        super(TemplateFile,self).__init__(name=name,
                                          content=content,
        )

        if renderer_class==None:
            if tolerantRender:
                 class ConcreteTolerantRenderer(TolerantRenderer):
                      def __init__(self,evalfunc, escapefunc):
                           TolerantRenderer.__init__(self,
                                                     evalfunc,
                                                     escapefunc,filename=name)

                 renderer_class=ConcreteTolerantRenderer
            else:
                 class ConcreteRenderWithFileName(RendererWithFilename):
                      def __init__(self,evalfunc, escapefunc):
                           RendererWithFilename.__init__(self,
                                                         evalfunc,
                                                         escapefunc,filename=name)

                 renderer_class=ConcreteRenderWithFileName

        if allowExec:
            sandbox=EvalPseudoSandboxWithMathWithImport
        else:
            sandbox=EvalPseudoSandboxWithMath

        self.ptemplate=PyratempTemplate(string=self.template,
                                        eval_class=sandbox,
                                        renderer_class=renderer_class,
                                        encoding=encoding,
                                        escape=None
        )

    def buildTemplate(self,template):
        self.template=PyratempPreprocessor(assignmentLineStart=self.assignmentLineStart,
                                           expressionDelimiter=self.expressionDelimiter,
                                           assignmentDebug=self.assignmentDebug,
                                           specials=self.specials,
                                           allowExec=self.allowExec
                                       )(template)

    def getString(self,vals):
        """In the template, replaces all the strings between $$
        with the evaluation of the expressions
        :param vals: dictionary with the values
        :returns: The string with the replaced expressions"""

        return self.ptemplate(**vals)

# Should work with Python3 and Python2
