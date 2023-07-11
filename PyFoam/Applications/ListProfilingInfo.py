"""
Application-class that implements pyFoamListProfilingInfo.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from .CommonSelectTimesteps import CommonSelectTimesteps

from PyFoam.ThirdParty.six import print_

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory

from os import path
from glob import glob

class ListProfilingInfo(PyFoamApplication,
                        CommonSelectTimesteps):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
List the profiling information in time directories  (either created by a
patched OpenFOAM-version, Foam-extend or by a OpenFOAM-version with the
profiling-patch applied) and prints them in a human-readable form. Either
gets files or a case directory from which it tries to get the proper files. If
more than one file is specified it is assumed that this is a parallel run and
the data is accumulated

Results are printed as a table. The first column is the name of the
profiling entry. Children entries (entries that are called by that
entry) are indented.  The first numeric column is the percentage that
this entry used of the total time (including time spent in
children). The next entry is the percentages of the 'self' time
(the time spent in this entry minus the time spent in the
children) as the percentage of the total execution time.  After
that the percentages of the parent time (total and 'self').
After that the number of times this
entry was called is printed. Then the total time spent in this entry
and the time without the child entries are printed.

If the data from multiple processors is used then the totalTime and the calls
are the average of all processors. Also are there three more columns: the range
of the totalTime (maximum-minimum). How big that range is compared to the average
totalTime and the range of the calls
"""
        examples="""\
%prog aCase/100/uniform/profilingInfo

  Print the profiling info of a case named aCase at time 100

%prog aCase --time=100

  Also print the profiling info of a case named aCase at time 100

%prog aCase --latest-time

  Print the profiling info from the latest timestep in case aCase

%prog aCase --latest-time --parallel

  Print the profiling information from the latest timestep in the case aCase
  but use the data from all processors and accumulate them

%prog aCase --latest-time --parallel --sort-by=totalTime --depth=2

  Sort the profiling data by the total time that was used and only
  print the first two levels

%prog aCase --latest-time --threshold-low=1 --graphviz-dot | dot -Tsvg -o aCase.svg

  Remove all nodes that need less than 1% of the computation time and
  generate an SVG-file with a graph. This requires the dot-utility from
  GraphViz to be present

%prog aCase --latest-time --threshold-low=1 --graphviz-dot --dot-append-title="$(date)" | dot -Tsvg -o aCase.svg

  Plots the same with the current time added to the title (whether "$(date)" works
  depends on the used shell)
"""

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   examples=examples,
                                   usage="%prog [<caseDirectory>|<profiling file>]",
                                   interspersed=True,
                                   changeVersion=True,
                                   nr=1,
                                   exactNr=False,
                                   **kwargs)

    def addOptions(self):
        CommonSelectTimesteps.addOptions(self,False,singleTime=True)
        output=OptionGroup(self.parser,
                           "Output",
                           "How data should be output")
        self.parser.add_option_group(output)
        sortModes=["id","totalTime","selfTime","description","calls"]
        output.add_option("--sort-by",
                          type="choice",
                          dest="sortBy",
                          default="id",
                          choices=sortModes,
                          help="How the entries should be sorted in their 'subtree'. Possible values are "+", ".join(sortModes)+". Default is 'id' which is more or less the order in which these entries were registered")
        output.add_option("--depth",
                          type="int",
                          dest="depth",
                          default=0,
                          help="How many levels of the tree should be printed. If 0 or smaller then everything is printed")
        output.add_option("--threshold-low",
                          type="float",
                          dest="threshold_low",
                          default=None,
                          help="A percent value. If a node has less than this value it (and its children) will not be displayed")
        output.add_option("--graphviz-dot",
                          default=False,
                          dest="graphviz_dot",
                          action="store_true",
                          help="Instead of the list print out an output that can be piped into the utility called 'dot' of the GraphViz suite to produce a graphical tree representation of the profiling data")

        dot = OptionGroup(self.parser,
                          "Dot",
                          "Options that are used for the graphviz-dot output")
        self.parser.add_option_group(dot)
        dot.add_option("--dot-theme",
                       dest="dot_theme",
                       default=themes.keys()[0],
                       help="Theme to be used. possible values are: " + ", ".join(themes.keys()) + ". Default: %default")
        dot.add_option("--dot-override-title",
                       dest="dot_override_title",
                       default=None,
                       help="For dot plots use this title instead of the automatically generated title of either case-name and time or filename. Can have '\\n' for multiple lines")
        dot.add_option("--dot-append-title",
                       dest="dot_append_title",
                       default=None,
                       help="Append this to the title on a new line. Can have '\\n' for multiple lines")

    def readProfilingInfo(self,fName):
        """Read the info from a file and return a tuple with (date,children,root)"""
        pf=ParsedParameterFile(fName,
                               treatBinaryAsASCII=True)

        try:
            # Foam-extend and Patch
            pi=pf["profilingInfo"]
            newFormat=False
        except KeyError:
            try:
                pi=pf["profiling"]
                newFormat=True
            except KeyError:
                self.error("No profiling info found in",fName)

        data={}
        children={}
        root=None

        for p in pi:
            if newFormat:
                p=pi[p]
            if p["id"] in data:
                print_("Duplicate definition of",p["id"])
                sys.exit(-1)
            if p["description"][0]=='"':
                p["description"]=p["description"][1:]
            if p["description"][-1]=='"':
                p["description"]=p["description"][:-1]

            data[p["id"]]=p
            if "parentId" in p:
                if p["parentId"] in children:
                    children[p["parentId"]].append(p["id"])
                else:
                    children[p["parentId"]]=[p["id"]]
            else:
                if root!=None:
                    print_("Two root elements")
                    sys-exit(-1)
                else:
                    root=p["id"]
            p["selfTime"]=p["totalTime"]-p["childTime"]

        return data,children,root

    def printProfilingInfo(self,data,children,root,parallel=False):
        """Prints the profiling info in a pseudo-graphical form"""
        def depth(i):
            if i in children:
                return max([depth(j) for j in children[i]])+1
            else:
                return 0
        maxdepth=depth(root)

        depths={}

        def nameLen(i,d=0):
            depths[i]=d
            maxi=len(data[i]["description"])
            if i in children:
                maxi=max(maxi,max([nameLen(j,d+1) for j in children[i]]))
            if self.opts.depth>0 and depths[i]>self.opts.depth:
                return 0
            else:
                return maxi+3

        maxLen=nameLen(root)

        format=" %5.1f%% (%5.1f%%) - %5.1f%% (%5.1f%%) | %8d %9.4gs %9.4gs"
        if parallel:
            parallelFormat=" | %9.4gs %5.1f%% %9.4g"
        totalTime=data[root]["totalTime"]

        header=" "*(maxLen)+" |  total  ( self ) - parent ( self ) |    calls      total      self "
        if parallel:
            header+="| range(total) / %   range(calls) "
        print_(header)
        print_("-"*len(header))

        def printItem(i):
            result=""
            if self.opts.depth>0 and depths[i]>self.opts.depth:
                return ""
            if depths[i]>1:
                result+="  "*(depths[i]-1)
            if depths[i]>0:
                result+="|- "
            result+=data[i]["description"]
            result+=" "*(maxLen-len(result)+1)+"| "

            parentTime=data[i]["totalTime"]
            if "parentId" in data[i]:
                parentTime=data[data[i]["parentId"]]["totalTime"]

            tt=data[i]["totalTime"]
            ct=data[i]["childTime"]
            st=data[i]["selfTime"]

            result+=format % (100*tt/totalTime,
                              100*st/totalTime,
                              100*tt/parentTime,
                              100*st/tt,
                              data[i]["calls"],
                              tt,
                              st)
            if parallel:
                timeRange=data[i]["totalTimeMax"]-data[i]["totalTimeMin"]
                result+=parallelFormat % (timeRange,
                                          100*timeRange/tt,
                                          data[i]["callsMax"]-data[i]["callsMin"])
            print_(result)
            if i in children:
                def getKey(k):
                    def keyF(i):
                        return data[i][k]
                    return keyF

                #make sure that children are printed in the correct order
                if self.opts.sortBy=="id":
                    children[i].sort()
                else:
                    children[i].sort(
                        key=getKey(self.opts.sortBy),
                        reverse=self.opts.sortBy in ["totalTime","selfTime","calls"])
                for c in children[i]:
                    printItem(c)

        printItem(root)

    AddFields = ["totalTime", "totalTimeMin", "totalTimeMax",
                 "childTime", "selfTime",
                 "nr_removed",
                 "calls", "callsMin", "callsMax"]

    def printDotGraph(self, data, children, root, theme, title=None):
        totalTime = data[root]["totalTime"]

        terminal_nodes = []
        non_terminal = []

        def get_nodes(node):
            if node in children:
                non_terminal.append(node)
                for c in children[node]:
                    get_nodes(c)
            else:
                terminal_nodes.append(node)
        get_nodes(root)

        dot_nodes = {}
        translation = {}

        for i, n in enumerate(non_terminal):
            translation[n] = i
            dot_nodes[i] = data[n]

        descr = {}

        for n in terminal_nodes:
            d = data[n]
            nm = d["description"]
            if nm not in descr:
                new_id = max(dot_nodes.keys()) + 1
                descr[nm] = new_id
                dot_nodes[new_id] = d.copy()
            else:
                dst = dot_nodes[descr[nm]]
                for k in self.AddFields:
                    if k in dst:
                        dst[k] += d[k]
            translation[n] = descr[nm]

        def color(rgb):
            r, g, b = rgb

            def float2int(f):
                if f <= 0.0:
                    return 0
                if f >= 1.0:
                    return 255
                return int(255.0*f + 0.5)

            return "#" + "".join(["%02x" % float2int(c) for c in (r, g, b)])

        print_("""digraph {{
    graph [fontname={fontname}, nodesep=0.125, ranksep=0.25];
    node [fontcolor={fontcolor}, fontsize=10, fontname={fontname}, height=0, shape=box, style={nodestyle}, width=0];
    edge [fontname={fontname}, fontsize=7];\n""".format(fontname=theme.graph_fontname(),
                                                        fontcolor=theme.graph_fontcolor(),
                                                        nodestyle=theme.node_style()))

        if title is not None:
            print_('label = "{}";'.format(title.replace("\n","\\n")))
            print_('labelloc = "top";')
            print_('labeljust = "left";')

        def node_name(n):
            return "node{}".format(translation[n])

        def make_edges(node):
            if node not in children:
                return

            p = data[node]

            for c in children[node]:
                d = data[c]
                label_text = "{:6g}s = {:.2f}%".format(d["totalTime"], 100*d["totalTime"] / totalTime)
                label_text += "\\n{:6g} x".format(d["calls"])
                frac = d["totalTime"] / p["totalTime"]
                label_text += "\\n{:.2f}% of parent".format(100 * frac)
                total_frac = d["totalTime"] / totalTime
                ratio = 0.5 + 10 * total_frac
                try:
                    label_text += "\\nReplaces {} paths".format(d["nr_removed"])
                except KeyError:
                    pass

                print_('    {src} -> {dst} [color="{color}", fontcolor="{fontcolor}", fontsize="{fontsize}", label="{label}", penwidth="{width}", arrowsize="{arrow}", labeldistance="{width}"];'.format(
                    src=node_name(node),
                    dst=node_name(c),
                    label=label_text,
                    color=color(theme.edge_color(frac)),
                    fontcolor=color(theme.edge_color(frac)),
                    fontsize=theme.edge_fontsize(total_frac),
                    width=ratio,
                    arrow=1/ratio))
                make_edges(c)

        make_edges(root)

        for t, n in translation.items():
            d = dot_nodes[n]
            label_text = d["description"]
            label_text += "\\n{:6g}s = {:.2f}%".format(d["totalTime"], 100*d["totalTime"]/totalTime)
            if t not in terminal_nodes:
                label_text += "\\nSelf: {:.2f}%".format(100*(d["selfTime"]/d["totalTime"]))
            label_text += "\\n{:6g} x".format(d["calls"])
            try:
                label_text += "\\nReplaces {} nodes".format(d["nr_removed"])
            except KeyError:
                pass

            weight = (d["selfTime"] if t in children else d["totalTime"]) / totalTime

            print('   {node} [ color="{bgcolor}", fontcolor="{fontcolor}", fontsize="{fontsize}", label="{label}"];'.format(
                node="node{}".format(n),
                bgcolor=color(theme.node_bgcolor(weight)),
                fontcolor=color(theme.node_fgcolor(weight)),
                fontsize=theme.node_fontsize(weight),
                label=label_text))
        print_("}")

    def clip_small(self, threshold, data, children, root):
        thres = data[root]["totalTime"] * threshold / 100.

        def remove_small_children(node):
            if node not in children:
                return

            remove = []
            for c in children[node]:
                if data[c]["totalTime"] < thres:
                    remove.append(c)

            for c in remove:
                children[node].remove(c)

            for c in children[node]:
                remove_small_children(c)

            if len(remove) > 0:
                rest = data[remove[0]].copy()
                rest["description"] = "< less than {}% >".format(threshold)
                new_id = max(data.keys())+1
                rest["id"] = new_id
                rest["nr_removed"] = 1
                for c in remove[1:]:
                    for k in self.AddFields:
                        if k in data[c]:
                            rest[k] += data[c][k]
                    rest["nr_removed"] += 1

                data[new_id] = rest
                children[node].append(new_id)

        remove_small_children(root)

        return data, children

    def run(self):
        files=self.parser.getArgs()[0:]

        usedTime = None
        usedCase = None

        if self.opts.graphviz_dot and self.opts.depth > 0:
            self.error("The depth-option can't be used for the graphviz plots")

        if len(files)==1 and path.isdir(files[0]):
            usedCase = path.abspath(self.parser.getArgs()[0])
            sol=SolutionDirectory(
                usedCase,
                archive=None,
                parallel=self.opts.parallelTimes,
                paraviewLink=False)
            self.processTimestepOptions(sol)
            if len(self.opts.time)<1:
                self.error("No time specified")
            globStr=self.parser.getArgs()[0]
            if self.opts.parallelTimes:
                globStr=path.join(globStr,"processor*")
            usedTime=sol.timeName(self.opts.time[0])
            globStr=path.join(globStr,
                              usedTime,
                              "uniform","profiling*")

            files=glob(globStr)
            if not self.opts.graphviz_dot:
                print_("Profiling info from time", usedTime)

        used_data = None
        parallel = False

        if len(files)<1:
            self.error("No profiling data found")
        elif len(files)>1:
            lst=[]
            for f in files:
                lst.append(self.readProfilingInfo(f))
            dataAll,children0,root0=lst[0]
            for i in dataAll:
                d=dataAll[i]
                d["totalTimeMin"]=d["totalTime"]
                d["totalTimeMax"]=d["totalTime"]
                d["callsMin"]=d["calls"]
                d["callsMax"]=d["calls"]
            for data,children,root in lst[1:]:
                if root0!=root or children!=children0 or data.keys()!=dataAll.keys():
                    self.error("Inconsistent profiling data. Probably not from same run/timestep")
                for i in data:
                    d=data[i]
                    s=dataAll[i]
                    s["totalTime"]+=d["totalTime"]
                    s["totalTimeMin"]=min(s["totalTimeMin"],d["totalTime"])
                    s["totalTimeMax"]=max(s["totalTimeMax"],d["totalTime"])
                    s["calls"]+=d["calls"]
                    s["callsMin"]=min(s["callsMin"],d["calls"])
                    s["callsMax"]=max(s["callsMax"],d["calls"])
                    s["childTime"]+=d["childTime"]
            for i in dataAll:
                d=dataAll[i]
                d["totalTime"]=d["totalTime"]/len(lst)
                d["childTime"]=d["childTime"]/len(lst)
                d["calls"]=d["calls"]/len(lst)
            used_data = dataAll
            parallel = True
        else:
            used_data, children, root = self.readProfilingInfo(files[0])

        if self.opts.threshold_low is not None:
            used_data, children = self.clip_small(max(min(self.opts.threshold_low, 99.99), 0),
                                                  used_data, children, root)

        if self.opts.graphviz_dot:
            if self.opts.dot_theme not in themes.keys():
                self.error("Unknown theme name '{}'. Possible values are: {}".format(
                    self.opts.dot_theme,
                    ", ".join(themes.keys())))

            title = None
            if usedTime:
                title = "Case: {}\nt={}".format(path.basename(usedCase), usedTime)
            else:
                title = "Files: " + ", ".join(files)
            if self.opts.dot_override_title is not None:
                title = self.opts.dot_override_title
            if self.opts.dot_append_title is not None:
                title += "\n" + self.opts.dot_append_title

            self.printDotGraph(used_data, children, root, themes[self.opts.dot_theme], title=title)
        else:
            self.printProfilingInfo(used_data, children, root, parallel)

    # Color handling. Lifted from
    # https://github.com/jrfonseca/gprof2dot/blob/master/gprof2dot.py
    # Will be moved to basic should th graphviz-dot stuff ever be needed elsewhere
class Theme:

    def __init__(self,
            bgcolor = (0.0, 0.0, 1.0),
            mincolor = (0.0, 0.0, 0.0),
            maxcolor = (0.0, 0.0, 1.0),
            fontname = "Arial",
            fontcolor = "white",
            nodestyle = "filled",
            minfontsize = 10.0,
            maxfontsize = 10.0,
            minpenwidth = 0.5,
            maxpenwidth = 4.0,
            gamma = 2.2,
            skew = 1.0):
        self.bgcolor = bgcolor
        self.mincolor = mincolor
        self.maxcolor = maxcolor
        self.fontname = fontname
        self.fontcolor = fontcolor
        self.nodestyle = nodestyle
        self.minfontsize = minfontsize
        self.maxfontsize = maxfontsize
        self.minpenwidth = minpenwidth
        self.maxpenwidth = maxpenwidth
        self.gamma = gamma
        self.skew = skew

    def graph_bgcolor(self):
        return self.hsl_to_rgb(*self.bgcolor)

    def graph_fontname(self):
        return self.fontname

    def graph_fontcolor(self):
        return self.fontcolor

    def graph_fontsize(self):
        return self.minfontsize

    def node_bgcolor(self, weight):
        return self.color(weight)

    def node_fgcolor(self, weight):
        if self.nodestyle == "filled":
            return self.graph_bgcolor()
        else:
            return self.color(weight)

    def node_fontsize(self, weight):
        return self.fontsize(weight)

    def node_style(self):
        return self.nodestyle

    def edge_color(self, weight):
        return self.color(weight)

    def edge_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_penwidth(self, weight):
        return max(weight*self.maxpenwidth, self.minpenwidth)

    def edge_arrowsize(self, weight):
        return 0.5 * math.sqrt(self.edge_penwidth(weight))

    def fontsize(self, weight):
        return max(weight**2 * self.maxfontsize, self.minfontsize)

    def color(self, weight):
        weight = min(max(weight, 0.0), 1.0)

        hmin, smin, lmin = self.mincolor
        hmax, smax, lmax = self.maxcolor

        if self.skew < 0:
            raise ValueError("Skew must be greater than 0")
        elif self.skew == 1.0:
            h = hmin + weight*(hmax - hmin)
            s = smin + weight*(smax - smin)
            l = lmin + weight*(lmax - lmin)
        else:
            base = self.skew
            h = hmin + ((hmax-hmin)*(-1.0 + (base ** weight)) / (base - 1.0))
            s = smin + ((smax-smin)*(-1.0 + (base ** weight)) / (base - 1.0))
            l = lmin + ((lmax-lmin)*(-1.0 + (base ** weight)) / (base - 1.0))

        return self.hsl_to_rgb(h, s, l)

    def hsl_to_rgb(self, h, s, l):
        """Convert a color from HSL color-model to RGB.
        See also:
        - http://www.w3.org/TR/css3-color/#hsl-color
        """

        h = h % 1.0
        s = min(max(s, 0.0), 1.0)
        l = min(max(l, 0.0), 1.0)

        if l <= 0.5:
            m2 = l*(s + 1.0)
        else:
            m2 = l + s - l*s
        m1 = l*2.0 - m2
        r = self._hue_to_rgb(m1, m2, h + 1.0/3.0)
        g = self._hue_to_rgb(m1, m2, h)
        b = self._hue_to_rgb(m1, m2, h - 1.0/3.0)

        # Apply gamma correction
        r **= self.gamma
        g **= self.gamma
        b **= self.gamma

        return (r, g, b)

    def _hue_to_rgb(self, m1, m2, h):
        if h < 0.0:
            h += 1.0
        elif h > 1.0:
            h -= 1.0
        if h*6 < 1.0:
            return m1 + (m2 - m1)*h*6.0
        elif h*2 < 1.0:
            return m2
        elif h*3 < 2.0:
            return m1 + (m2 - m1)*(2.0/3.0 - h)*6.0
        else:
            return m1


TEMPERATURE_COLORMAP = Theme(
    mincolor = (2.0/3.0, 0.80, 0.25), # dark blue
    maxcolor = (0.0, 1.0, 0.5), # satured red
    gamma = 1.0
)

PINK_COLORMAP = Theme(
    mincolor = (0.0, 1.0, 0.90), # pink
    maxcolor = (0.0, 1.0, 0.5), # satured red
)

GRAY_COLORMAP = Theme(
    mincolor = (0.0, 0.0, 0.85), # light gray
    maxcolor = (0.0, 0.0, 0.0), # black
)

BW_COLORMAP = Theme(
    minfontsize = 8.0,
    maxfontsize = 24.0,
    mincolor = (0.0, 0.0, 0.0), # black
    maxcolor = (0.0, 0.0, 0.0), # black
    minpenwidth = 0.1,
    maxpenwidth = 8.0,
)

PRINT_COLORMAP = Theme(
    minfontsize = 18.0,
    maxfontsize = 30.0,
    fontcolor = "black",
    nodestyle = "solid",
    mincolor = (0.0, 0.0, 0.0), # black
    maxcolor = (0.0, 0.0, 0.0), # black
    minpenwidth = 0.1,
    maxpenwidth = 8.0,
)


themes = {
    "color": TEMPERATURE_COLORMAP,
    "pink": PINK_COLORMAP,
    "gray": GRAY_COLORMAP,
    "bw": BW_COLORMAP,
    "print": PRINT_COLORMAP,
}
