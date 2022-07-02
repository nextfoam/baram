#  ICE Revision: $Id: Configuration.py,v 0605f57b0731 2020-02-25 14:25:33Z bgschaid $
"""Reads configuration-files that define defaults for various PyFoam-Settings

Also hardcodes defaults for the settings"""

from PyFoam.ThirdParty.six.moves import configparser
from PyFoam.ThirdParty.six import iteritems,PY3

from PyFoam.Infrastructure.Hardcoded import globalConfigFile,userConfigFile,globalDirectory,userDirectory,globalConfigDir,userConfigDir,pyFoamSiteVar,siteConfigDir,siteConfigFile

from os import path,environ
import glob,re

_defaults={
    "Network": {
        "startServerPort"  : "18000",
        "startServerPortSSL" : "18100",
        "SSLServerDefault" : True,
        "nrServerPorts"    : "100",
        "portWait"         : "1.",
        "socketTimeout"    : "1.",
        "zeroconfTimeout"  : "5.",
        "socketRetries"    : "10",
        "startServerThread": "True",
        "personalSSLCertificate" : path.join(userDirectory(),"foamServerCertificate.cert"),
        "privateSSLKey" :  path.join(userDirectory(),"foamServerCertificate.key"),
        "allowSelfSignedSSL" : True ,
    },
    "Metaserver": {
        "port"             : "17999",
        "ip"               : "192.168.1.11",
        "checkerSleeping"  : "30.",
        "searchServers"    : "192.168.1.0/24,192.168.0.0/24",
        "webhost"          : "127.0.0.1:9000",
        "doWebsync"        : "True",
        "websyncInterval"  : "300.",
    },
    "IsAlive": {
        "maxTimeStart"     : "30.",
        "isLivingMargin"   : "1.1"
    },
    "Logging": {
        "default" : "INFO",
        "server" : "INFO",
    },
    "OpenFOAM": {
        "Forks" : 'openfoam,extend,openfoamplus',
        "DirPatterns-openfoam" : '"^OpenFOAM-(([0-9]\.([0-9]|x)|dev).*)$","^OpenFOAM-([0-9]+)$","^openfoam([0-9]+)$"',
        "DirPatterns-extend" : '"^foam-extend-([0-9]\.[0-9].*)$"',
        "DirPatterns-openfoamplus" : '"^OpenFOAM-((v[0-9]\.[0-9]\+|plus|v[123][0-9]+(\+|)).*)$"',
        "Installation-openfoam" : "~/OpenFOAM",
        "Installation-openfoamplus" : "~/OpenFOAM",
        "Installation-extend" : "~/foam",
        "AdditionalInstallation-openfoam" : '"~/OpenFOAM","/opt/OpenFOAM"',
        "Version" : "4.0",
    },
    "MPI": {
#    "run_OPENMPI":"mpirun",
#    "run_LAM":"mpirun",
        "OpenMPI_add_prefix":"False",
        "options_OPENMPI_pre": '["--mca","pls","rsh","--mca","pls_rsh_agent","rsh"]',
        "options_OPENMPI_post":'["-x","PATH","-x","LD_LIBRARY_PATH","-x","WM_PROJECT_DIR","-x","PYTHONPATH","-x","FOAM_MPI_LIBBIN","-x","MPI_BUFFER_SIZE","-x","MPI_ARCH_PATH"]'
    },
    "Paths": {
        "python" : "/usr/bin/python",
        "bash" : "/bin/bash",
        "paraview" : "paraview",
    },
    "ClusterJob": {
        "useFoamMPI":'["1.5"]',
        "path":"/opt/openmpi/bin",
        "ldpath":"/opt/openmpi/lib",
        "doAutoReconstruct":"True",
        "useMachineFile":"True",
    },
    "Debug": {
#    "ParallelExecution":"True",
    },
    "Execution":{
        "controlDictRestoreWait":"60.",
        "DebuggerCall":"gdb -ex run --args {exe} {args}",
        "DebuggerCall_Darwin":"lldb -o run -k bt -- {exe} {args}"
    },
    "CaseBuilder":{
        "descriptionPath": eval('["'+path.curdir+'","'+path.join(userDirectory(),"caseBuilderDescriptions")+'","'+path.join(globalDirectory(),"caseBuilderDescriptions")+'"]'),
    },
    "Formats":{
        "error"       : "bold,red,standout",
        "warning"     : "under",
        "source"      : "red,bold",
        "destination" : "blue,bold",
        "difference"  : "green,back_black,bold",
        "question"    : "green,standout",
        "input"       : "cyan,under",
    },
    "CommandOptionDefaults":{
        "sortListCases":"mtime",
        "deadThresholdListCases":3601,
    },
    "Plotting":{
        "preferredImplementation":"gnuplot",
        "gnuplot_terminal" : "x11" ,
        "gnuplotCommands":"set xzeroaxis linewidth 4;set grid xtics ytics back lw 0.5",
        "hardcopyOptions_png" : "large size 1024,800",
        "hardcopyOptions_pdf" : "color",
        "hardcopyOptions_postscript" : "color",
        "hardcopyOptions_eps" : "color",
        "autoplots" : [],
        "plotlinear" : True,
        "plotcontinuity" : True,
        "plotbound" : True,
        "plotiterations" : False,
        "plotcourant" : False,
        "plotexecution" : False,
        "plotdeltat" : False,
    },
    "Gnuplot": {
        "prefer_fifo" : False,
    },
    "Curses": {
        "headerTextColor": "red",
        "headerBackgroundColor": "white",
        "textBackgroundColor": "black",
        "textColor": "green",
        "textMatchColor": "cyan",
        "textGroupColor": "yellow",
    },
    "OutfileCollection": {
        "maximumOpenFiles":"100",
    },
    "SolverOutput": {
        "timeRegExp": "^(Time =|Iteration:) (.+)$",
        "stripSpaces":False,
    },
    "Clearing": {
        "additionalPatterns":"[]",
    },
    "postRunHook_WriteMySqlite" : {
        "enabled":False,
        "module":"WriteToSqliteDatabase",
        "createDatabase":False,
        "database":"~/databaseOfAllMyRuns.db",
    },
    "postRunHook_SendToPushover" : {
        "enabled":False,
        "minRunTime":600,
        "useSSL":True,
        "module":"SendToWebservice",
        "host":"api.pushover.net:443",
        "method":"POST",
        "url":"/1/messages",
        "param_token":"invalid_get_yourself_one_at_pushover.net",
        "param_user":"invalid_get_yourself_an_account_at_pushover.net",
        "param_title":"<!--(if OK)-->Finished<!--(else)-->Failed<!--(end)-->: |-casename-| (|-solver-|)",
        "param_message":"""Case |-casefullname-| ended after |-wallTime-|s
Last timestep: t=|-time-|
Machine: |-hostname-|
Full command: |-commandLine-|""",
        "header_Content-type": "application/x-www-form-urlencoded",
        "templates":"title message"
    },
    "postRunHook_mailToMe" : {
        "enabled":False,
        "minRunTime":600,
        "module":"MailToAddress",
        "to":"nobody@here.there",
        "from":"a_concerned_user@your.local.machine",
        "smtpServer":"smtp.server.that.doesnt.need.authentication'",
        "subject":"<!--(if OK)-->Finished<!--(else)-->Failed<!--(end)-->: |-casename-| (|-solver-|)",
        "message":"""Case |-casefullname-| ended after |-wallTime-|s
Last timestep: t=|-time-|
Machine: |-hostname-|
Full command: |-commandLine-|""",
        "mailFields_Reply-To": "nobody@nowhere.com",
    },
    "Cloning" : {
        "addItem":"[]",
        "noForceSymlink":"[]",
    },
    "PrepareCase" : {
        "ClearCaseScript":"clearCase.sh",
        "MeshCreateScript":"meshCreate.sh",
        "PostCopyScript":"postCopy.sh",
        "CaseSetupScript":"caseSetup.sh",
        "DecomposeMeshScript":"decomposeMesh.sh",
        "DecomposeFieldsScript":"decomposeFields.sh",
        "DecomposeCaseScript":"decomposeCase.sh",
        "DefaultParameterFile":"default.parameters",
        "AllowDerivedChanges":False,
        "ZipExtensionlessTemplateResults":False,
        "ZipableExtensions": [],
        "ignoreDirectories": '"processor[0-9]+","postProcessing",".*.analyzed","VTK"'
    },
    "Template" : {
        "allowExecution"                : False,
        "assignmentDebug"               : False,
        "tolerantRender"                : False,
        "expressionDelimiter"           : "|-",
        "assignmentLineStart"           : "$$",
    },
    "SolverBase" : {
        # entries of form solvername: list of base-solvers
    },
    "Blink1" : {
        "baseurl" : "http://localhost:8934/blink1",
        "allowedTimeout" : 1,
        "tictoccolor": "#00FF00",
        "timestepcolor": "#000080",
        "executepattern": "RGB",
        "executeinterleave": 1,
    },
    "Autoplots" : {
        "phaseFraction" : {
            "solvers" : [".+[pP]haseEulerFoam",".*[iI]nterFoam"],
            "plotinfo" : {
                "theTitle" : "Phase fractions",
                "expr" : r"alpha.(.+) volume fraction = (.+)  Min\(alpha1\) = (.+)  Max\(alpha1\) = (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : ["average","min","max"]
            }
        },
        "phaseFractionNew" : {
            "solvers" : [".+[pP]haseEulerFoam",".*[iI]nterFoam"],
            "plotinfo" : {
                "theTitle" : "Phase fractions",
                "expr" : r"Phase.+ volume fraction = (.+)  Min\(alpha\.(.+)\) = (.+)  Max\(alpha\.\2\) = (.+)",
                "type" : "dynamic",
                "idNr" : 2,
                "titles" : ["average","min","max"]
            }
        },
        "interfaceTemperature" : {
            "solvers" : ["reacting.+EulerFoam"],
            "plotinfo" : {
                "theTitle" : "Interface temperature",
                "expr" : r"Tf.(.+): min = (.+), mean = (.+), max = (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : ["min","mean","max"]
            }
        },
        "cloudNumberMass" : {
            "solvers" : [ "coal.+Foam" , ".+Parcel.*Foam" , "sprayFoam" ],
            "plotinfo" : {
                "theTitle" : "Particle number and mass",
                "expr" : r"Cloud: (.+)\n +Current number of parcels += (.+)\n +Current mass in system += (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : [ "nr" , "mass" ],
                "alternateAxis" : [ ".+_mass" ],
                "ylabel" : "Particle number",
                "y2label" : "Mass in system"
            }
        },
        "surfaceFilmMass" : {
            "solvers" : [ ".+Film.*Foam" ],
            "plotinfo" : {
                "theTitle" : "Surface film mass",
                "expr" : r"Surface film: (.+)\n +added mass         = (.+)\n +current mass       = (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : [ "added" , "current" ],
                "alternateAxis" : [ ".+_added" ],
                "ylabel" : "Current mass",
                "y2label" : "Added mass"
            }
        },
        "surfaceFilmCoverage" : {
            "solvers" : [ ".+Film.*Foam" ],
            "plotinfo" : {
                "theTitle" : "Surface film coverage",
                "expr" : r"Surface film: (.+)\n.+\n.+\n.+\n.+\n    coverage           = (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : [ "coverage" ],
                "ylabel" : "Ratio",
            }
        },
        "surfaceFilmVelocity" : {
            "solvers" : [ ".+Film.*Foam" ],
            "plotinfo" : {
                "theTitle" : "Surface film velocity",
                "expr" : r"Surface film: (.+)\n.+\n.+\n    min/max\(mag\(U\)\)    = (.+), (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : [ "min","max" ],
                "ylabel" : "[m/s]",
            }
        },
        "surfaceFilmThickness" : {
            "solvers" : [ ".+Film.*Foam" ],
            "plotinfo" : {
                "theTitle" : "Surface film thickness",
                "expr" : r"Surface film: (.+)\n.+\n.+\n.+\n    min/max\(delta\)     = (.+), (.+)",
                "type" : "dynamic",
                "idNr" : 1,
                "titles" : [ "min","max" ],
                "ylabel" : "[m]",
            }
        },
        "chtPhase" : {
            "solvers" : [ "chtMultiRegion.*Foam" ],
            "plotinfo" : {
                "type" : "phase" ,
                "expr" : r"Solving for .+ region (.+)",
                "idNr" : 1
            }
        },
        "chtPhaseOff" : {
            "solvers" : [ "chtMultiRegion.*Foam" ],
            "plotinfo" : {
                "type" : "phase" ,
                "expr" : r"ExecutionTime(x*) = .+",
                "idNr" : 1
            }
        },
        "chtFluidTemperature" : {
            "solvers" : [ "chtMultiRegion.*Foam" ],
            "plotinfo" : {
                "expr" : r"Min/max T:(\S+) (\S+)$",
                "titles" : [ "min" , "max"],
                "theTitle" : "Temperatures"
            }
        },
        "chtSolidTemperature" : {
            "solvers" : [ "chtMultiRegion.*Foam" ],
            "plotinfo" : {
                "type" : "collector" ,
                "master" : "chtfluidtemperature",
                "expr" : r"Min/max T:min\(T\) \[0 0 0 1 0 0 0\] (.+) max\(T\) \[0 0 0 1 0 0 0\] (.+)",
                "titles" : [ "solid min" , "solid max"]
            }
        },
        "chtFluidCourant" : {
            "solvers" : [ "chtMultiRegion.*Foam" ],
            "plotinfo" : {
                "theTitle" : "Courant and diffusion number",
                "ylabel" : "Courant" ,
                "y2label" : "Diffusion",
                "type" : "dynamic",
                "expr" : r"Region: (.+) Number mean: (.+) max: (.+)",
                "titles" : [ "mean" , "max"],
                "alternateAxis" : [ ".+Diffusion.+" ],
                "idNr" : 1
            }
        },
        "cellVolumesDynamicMesh" : {
            "solvers" : [ "move.*Mesh" , ".*DyM.*" ],
            "plotinfo" : {
                "theTitle" : "Cell volumes",
                "ylabel" : "[m^3]",
                "logscale" : True,
                "expr" : r"Min volume = (\S+)\. Max volume = (\S+)\.  Total volume = (\S+)\.",
                "titles" : ["Minimum","Maximum","Total"],
                "alternateAxis" : ["Total"]
            }
        },
        "faceAreaDynamicMesh" : {
            "solvers" : [ "move.*Mesh" , ".*DyM.*" ],
            "plotinfo" : {
                "theTitle" : "Face areas",
                "ylabel" : "[m^2]",
                "logscale" : True,
                "expr" : r"Minimum face area = (\S+). Maximum face area = (\S+).",
                "titles" : ["Minimum","Maximum"],
            }
        },
        "nonorhogonalityDynamicMesh" : {
            "solvers" : [ "move.*Mesh" , ".*DyM.*" ],
            "plotinfo" : {
                "theTitle" : "Non-orthodonality and aspect ratio",
                "ylabel" : "Non-orthogonality",
                "y2label" : "Aspect ratio",
                "expr" : r"Mesh non-orthogonality Max: (\S+) average: (\S+)",
                "titles" : ["Max non-orth","Average non-orth"],
                "alternateAxis" : ["max aspect"]
            }
        },
        "aspectRatioDynamicMesh" : {
            "solvers" : [ "move.*Mesh" , ".*DyM.*" ],
            "plotinfo" : {
                "type" : "collector",
                "master" : "nonorhogonalitydynamicmesh",
                "expr" : r"Max aspect ratio = (\S+)",
                "titles" : ["max aspect"]
            }
        },
        "interfaceCourant" : {
            "solvers" : [ "inter.*" ],
            "plotinfo" : {
#                "type" : "collector",
#                "master" : "courant",
                "theTitle" : "Interface courant number",
                "expr" : r"Interface Courant Number mean: (.+) max: (.+)",
                "titles" : ["mean","max"]
            }
        },
        "isoAdvectorNrCells" : {
            "solvers" : [ "interIso.*" ],
            "plotinfo" : {
                "expr" : r"Number of isoAdvector surface cells = (\S+)",
                "titles" : ["nr"],
                "theTitle" : "Number of Cells in the interface"
            }
        },
        "cellsPerLevel" : {
            "solvers" : [ "snappyHexMesh.*" ],
            "plotinfo" : {
                "type" : "dynamic",
                "theTitle" : "Cells per refinement level",
                "logscale" : True,
                "titles" : [ "nr" ],
                "expr" : r"([0-9]+)\s+([0-9]+)",
                "idNr" :  1,
                "with" : "fsteps",
                "xlabel" : "Steps",
                "alternateTime" : "countrefinements"
            }
        },
        "countRefinements" : {
            "solvers" : [ "snappyHexMesh.*" ],
            "plotinfo" : {
                "type" : "count",
                "expr" : "Cells per refinement level:"
            }
        },
        "snappyPhases" : {
            "solvers" : [ "snappyHexMesh.*" ],
            "plotinfo" : {
                "type" : "mark",
                "expr" : ".+ phase$|^Stopping .*",
                "targets" : [ "cellsperlevel" ]
            }
        },
        "foamyTotalDistance" : {
            "solvers" : ["foamyHexMesh"],
            "plotinfo" : {
                "expr" : "Total distance = (.+)",
                "theTitle" : "Total distance/displacement",
                "titles" : ["distance"],
                "alternateAxis" : ["distance"],
                "ylabel" : "Displacement",
                "y2label" : "Distance"
            }
        },
        "foamyTotalDisplacement" : {
            "solvers" : ["foamyHexMesh"],
            "plotinfo" : {
                "type" : "collector",
                "master" : "foamytotaldistance",
                "expr" : r"Total displacement = \((.+) (.+) (.+)\)",
                "titles" : ["x","y","z"]
            }
        },
        "foamyInserted" : {
            "solvers" : ["foamyHexMesh"],
            "plotinfo" : {
                "theTitle" : "Inserted Points",
                "expr" : r"(.+) points inserted, failed to insert ([0-9]+) .+",
                "titles" : ["inserted","failed"],
                "ylabel" : "Inserted",
                "y2label" : "Failed",
                "alternateAxis" : ["failed"]
            }
        }
    }
}

class ConfigurationSectionProxy(object):
    """Wraps a Confguration so that the section automatically becomes the
    first argument"""

    def __init__(self,conf,section):
        self.conf=conf
        self.section=section

    def __getattr__(self,name):
        f=getattr(self.conf,name)
        def curried(*args,**kwargs):
            return f(*((self.section,)+args),**kwargs)
        return curried

class Configuration(configparser.ConfigParser):
    """Reads the settings from files (if existing). Otherwise uses hardcoded
    defaults"""

    def __init__(self):
        """Constructs the ConfigParser and fills it with the hardcoded defaults"""
        configparser.ConfigParser.__init__(self)

        for section,content in iteritems(_defaults):
            self.add_section(section)
            for key,value in iteritems(content):
                if isinstance(value,(dict,list)):
                    import pprint
                    self.set(section,key,pprint.pformat(value,indent=2))
                else:
                    self.set(section,key,str(value))

        self.read(self.configFiles())

        self.validSections={}
        for s in self.sections():
            minusPos=s.find('-')
            if minusPos<0:
                name=s
            else:
                name=s[:minusPos]
            try:
                self.validSections[name].append(s)
            except KeyError:
                self.validSections[name]=[s]

        for name,sections in iteritems(self.validSections):
            if not name in sections:
                print("Invalid configuration for",name,"there is no default section for it in",sections)

    def sectionProxy(self,section):
        """Return a proxy object that makes it possible to avoid the section
        specification"""
        return ConfigurationSectionProxy(self,section)

    def bestSection(self,section,option):
        """Get the best-fitting section that has that option"""

        from PyFoam import foamVersionString

        try:
            if len(self.validSections[section])==1 or foamVersionString()=="":
                return section
        except KeyError:
            return section

        result=section
        fullName=section+"-"+foamVersionString()

        for s in self.validSections[section]:
            if fullName.find(s)==0 and len(s)>len(result):
                if self.has_option(s,option):
                    result=s

        return result

    def configSearchPath(self):
        """Defines a search path for the configuration files as a pare of type/name
        pairs"""
        files=[("file",globalConfigFile()),
               ("directory",globalConfigDir())]
        if pyFoamSiteVar in environ:
            files+=[("file",siteConfigFile()),
                    ("directory",siteConfigDir())]
        files+=[("file",userConfigFile()),
                ("directory",userConfigDir())]
        return files

    def configFiles(self):
        """Return a list with the configurationfiles that are going to be used"""
        files=[]

        for t,f in self.configSearchPath():
            if path.exists(f):
                if t=="file":
                    files.append(f)
                elif t=="directory":
                    for ff in glob.glob(path.join(f,"*.cfg")):
                        files.append(ff)
                else:
                    error("Unknown type",t,"for the search entry",f)

        return files

    def addFile(self,filename,silent=False):
        """Add another file to the configuration (if it exists)"""
        if not path.exists(filename):
            if not silent:
                print("The configuration file",filename,"is not there")
        else:
            self.read([filename])

    def dump(self):
        """Dumps the contents in INI-Form
        :return: a string with the contents"""
        result=""
        for section in sorted(self.sections(),key=lambda x:x.lower()):
            result+="[%s]\n" % (section)
            for key,value in sorted(self.items(section),key=lambda x:x[0].lower()):
                result+="%s: %s\n" % (key,value)
            result+="\n"

        return result

    def getList(self,section,option,default="",splitchar=",",stripQuotes=True):
        """Get a list of strings (in the original they are separated by commas)
        :param section: the section
        :param option: the option
        :param default: if set and the option is not found, then this value is used
        :param splitchar: the character by which the values are separated
        :param stripQuotes: remove quotes if present"""

        val=self.get(section,option,default=default)
        if val=="":
            return []
        else:
            result=[]
            for v in val.split(splitchar):
                if v[0]=='"' and v[-1]=='"':
                    result.append(v[1:-1])
                else:
                    result.append(v)
            return result

    def getboolean(self,section,option,default=None):
        """Overrides the original implementation from ConfigParser
        :param section: the section
        :param option: the option
        :param default: if set and the option is not found, then this value is used"""

        try:
            return configparser.ConfigParser.getboolean(self,
                                           self.bestSection(section,option),
                                           option)
        except configparser.NoOptionError:
            if default!=None:
                return default
            else:
                raise

    def getchoice(self,section,option,choices,default=None):
        """Overrides the original implementation from ConfigParser
        :param section: the section
        :param option: the option
        :param choices: list of valid values
        :param default: if set and the option is not found, then this value is used"""

        try:
            val=configparser.ConfigParser.get(self,
                                              self.bestSection(section,option),
                                              option)
            if val not in choices:
                raise ValueError("The option %s in section %s is %s but must be one of %s" % (
                    option,
                    section,
                    val,
                    ", ".join(choices)
                ))
            return val
        except configparser.NoOptionError:
            if default!=None:
                return default
            else:
                raise

    def getint(self,section,option,default=None):
        """Overrides the original implementation from ConfigParser
        :param section: the section
        :param option: the option
        :param default: if set and the option is not found, then this value is used"""

        try:
            return int(configparser.ConfigParser.get(self,
                                                     self.bestSection(section,option),
                                                     option))
        except configparser.NoOptionError:
            if default!=None:
                return default
            else:
                raise

    def getfloat(self,section,option,default=None):
        """Overrides the original implementation from ConfigParser
        :param section: the section
        :param option: the option
        :param default: if set and the option is not found, then this value is used"""

        try:
            return float(configparser.ConfigParser.get(self,
                                                       self.bestSection(section,option),
                                                       option))
        except (configparser.NoOptionError,ValueError):
            if default!=None:
                return default
            else:
                raise

    def getRegexp(self,section,option):
        """Get an entry and interpret it as a regular expression. Subsitute
        the usual regular expression value for floating point numbers
        :param section: the section
        :param option: the option
        :param default: if set and the option is not found, then this value is used"""
        floatRegExp="[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?"

        return re.compile(self.get(section,option).replace("%f%",floatRegExp))

    def getArch(self,section,option):
        """Get an entry. If an entry with <option>_<archname> exists then this is
        used instead of the plain <option>-entry
        :param section: the section
        :param option: the option"""

        import os
        archName=os.uname()[0]

        try:
            return self.get(section,option+"_"+archName)
        except configparser.NoOptionError:
            return self.get(section,option)

    def get(self,section,option,default=None,**kwargs):
        """Overrides the original implementation from ConfigParser
        :param section: the section
        :param option: the option
        :param default: if set and the option is not found, then this value is used"""

        try:
            return configparser.ConfigParser.get(self,
                                                 self.bestSection(section,option),
                                                 option,
                                                 **kwargs)
        except configparser.NoOptionError:
            if default!=None:
                return default
            else:
                raise

    def getdebug(self,name):
        """Gets a debug switch"""

        return self.getboolean("Debug",name,default=False)

# Should work with Python3 and Python2
