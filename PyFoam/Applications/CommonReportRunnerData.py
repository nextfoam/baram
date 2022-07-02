"""
Class that implements the common functionality for reporting the data that was submitted to the runner
"""

from PyFoam.Basics.RestructuredTextHelper import ReSTTable,RestructuredTextHelper

from PyFoam.ThirdParty.six import print_,iteritems

class CommonReportRunnerData(object):
    """ The class that reports the resource usage
    """

    def addOptions(self):
        self.ensureGeneralOptions()
        self.generalOpts.add_option("--report-runner-data",
                                    action="store_true",
                                    default=False,
                                    dest="reportRunnerData",
                                    help="After the execution the data collected by the runner (except for the analyzed data) is printed to the screen")
        self.generalOpts.add_option("--report-analyzed-data",
                                    action="store_true",
                                    default=False,
                                    dest="reportAnalyzedData",
                                    help="After the execution the analyzed data collected by the runner is printed to the screen")
        self.generalOpts.add_option("--dump-runner-data",
                                    action="store_true",
                                    default=False,
                                    dest="dumpRunnerData",
                                    help="After the execution the data collected by the runner is dumped")

    def reportRunnerData(self,run):
        if self.opts.reportRunnerData:
            try:
                data=run.data["analyzed"]
            except KeyError:
                self.error("No analyzed data")

            print_("\n Analyzed data:")
            print_()

            helper=RestructuredTextHelper(RestructuredTextHelper.LevelSubSubSection)

            for n,d in iteritems(data):
                table=helper.table()
                heads=["Descrition","value"]
                table[0]=heads
                table.addLine(head=True)
                lNr=1

                for k,v in iteritems(d):
                    table[(lNr,0)]=k
                    table[(lNr,1)]=v
                    lNr+=1

                print_(helper.heading(n),table)

        if self.opts.reportRunnerData:
            table=ReSTTable()
            heads=["Descrition","value"]
            table[0]=heads
            table.addLine(head=True)
            lNr=1
            done=["analyzed"]

            def addLine(key,description):
                if key in run.data:
                    table[(lNr,0)]=description
                    table[(lNr,1)]=run.data[key]
                    done.append(key)
                    return lNr+1
                return lNr

            lNr=addLine("time","Last simulation time")
            lNr=addLine("stepNr","Number of timesteps")
            lNr=addLine("lines","Lines written to stdout")
            lNr=addLine("warnings","Number of warnings")

            table.addLine()

            for k,v in iteritems(run.data):
                if k not in done:
                    table[(lNr,0)]=k
                    table[(lNr,1)]=v
                    lNr+=1

            print_("\n  Runner data:")
            print_()
            print_(table)

        if self.opts.dumpRunnerData:
            print_("\n  Runner data:",run.data)

# Should work with Python3 and Python2
