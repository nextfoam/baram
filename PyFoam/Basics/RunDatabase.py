#  ICE Revision: $Id: $
"""
Collects data about runs in a small SQLite database
"""

# don't look at it too closely. It's my first sqlite-code

import sqlite3
from os import path
import datetime
import re
import sys

from PyFoam.Error import error
from .CSVCollection import CSVCollection

from PyFoam.ThirdParty.six import print_,iteritems,integer_types
from PyFoam.ThirdParty.six import u as uniCode

class RunDatabase(object):
    """
    Database with information about runs. To be queried etc
    """

    separator = "//"
    unique_id = "uniqueid"
    run_id = "runId"
    TheRunsName = "theRuns"

    def __init__(self,
                 name,
                 create=False,
                 verbose=False):
        """:param name: name of the file
        :param create: should the database be created if it does not exist"""

        self.verbose=verbose
        if not path.exists(name):
            if create==False:
                error("Database",name,"does not exist")
            else:
                self.initDatabase(name)

        self.db=sqlite3.connect(name)
        self.db.row_factory=sqlite3.Row

    def initDatabase(self,name):
        """Create a new database file"""
        db=sqlite3.connect(name)
        with db:
            db.row_factory=sqlite3.Row
            cursor=db.cursor()
            cursor.execute("CREATE TABLE theRuns({} INTEGER PRIMARY KEY, ".format(self.run_id) +
                           self.__normalize("insertionTime") + " TIMESTAMP)")
            cursor.close()

    def id_exists(self, theId):
        return self.get_runID(theId) is not None

    def get_runID(self, uniqueId):
        if uniqueId is None:
            return None
        runCols = self.__getColumns(self.TheRunsName)
        if self.unique_id not in runCols:
            return None
        dataCursor = self.db.cursor()
        dataCursor.execute("SELECT * FROM {} WHERE {}=?".format(self.TheRunsName,
                                                                self.unique_id),
                           (uniqueId, ))
        data = dataCursor.fetchall()
        if len(data) < 1:
            return None
        else:
            return data[0][self.run_id]

    def add(self, data, update_existing=False):
        """Add a dictionary with data to the database"""
        self.__adaptDatabase(data)

        try:
            unique = data[self.unique_id]
        except KeyError:
            unique = None

        exists = self.id_exists(unique)

        if exists and not update_existing:
            raise KeyError("Run with key {} already in database".format(unique))

        runData = dict([("insertionTime", datetime.datetime.now())] +
                       [(k, v) for k, v in iteritems(data) if type(v) != dict])

        update_run = self.get_runID(unique)

        runID = self.__addContent(self.TheRunsName,
                                  runData,
                                  update_run=update_run)

        if update_run is not None:
            runID = update_run

        subtables = dict([(k, v) for k, v in iteritems(data) if type(v) == dict])
        for tn, content in iteritems(subtables):
            self.__addContent(tn+"Data",
                              dict(list(self.__flattenDict(content).items())+
                                   [(self.run_id, runID)]),
                              update_run=update_run)

        self.db.commit()

    def modify(self, unique_id, data):
        """Modify a dataset for which we have a unique id with the data in a dictionary"""

        update_run = self.get_runID(unique_id)
        if update_run is None:
            raise KeyError("Unique ID {} not in database".format(unique_id))

        self.__adaptDatabase(data)

        runData = dict([(k, v) for k, v in iteritems(data) if type(v) != dict])
        runID = self.__addContent(self.TheRunsName,
                                  runData,
                                  update_run=update_run)

        if update_run is not None:
            runID = update_run

        subtables = dict([(k, v) for k, v in iteritems(data) if type(v) == dict])
        for tn, content in iteritems(subtables):
            self.__addContent(tn+"Data",
                              dict(list(self.__flattenDict(content).items())+
                                   [(self.run_id, runID)]),
                              update_run=update_run)

        self.db.commit()

    specialChars={
        '[':'bro',
        ']':'brc',
        '{':'cro',
        '}':'crc',
        '(':'pro',
        ')':'prc',
        '|':'pip',
    }

    specialString="_specialChar"

    def __normalize(self,s):
        """Normalize a column-name so that the case-insensitve column-names of SQlite
        are no problem"""

        if s in [self.run_id,"dataId"]:
            return s
        result=""
        for c in s:
            if c.isupper() or c=="_":
                result+="_"+c.lower()
            elif c in RunDatabase.specialChars:
                result+=RunDatabase.specialString+RunDatabase.specialChars[c]
            else:
                result+=c
        return result

    def __denormalize(self,s):
        """Denormalize the column name that was normalized by _normalize"""

        while s.find(RunDatabase.specialString)>=0:
            pre,post=s.split(RunDatabase.specialString,maxsplit=1)
            spec=post[0:3]
            for k,v in iteritems(RunDatabase.specialChars):
                if spec==v:
                    s=pre+k+post[3:]
                    break
            else:
                error("No special character for encoding",spec,"found")

        result=""
        underFound=False

        for c in s:
            if underFound:
                underFound=False
                result+=c.upper()
            elif c=="_":
                underFound=True
            else:
                result+=c

        if underFound:
            error("String",s,"was not correctly encoded")

        return result

    def __addContent(self, table, data, update_run=None):
        cursor = self.db.cursor()
        if len(data) == 0:
            if self.verbose:
                print_("No data. Nothing done")
            cursor.close()
            return None

        runData={}
        for k,v in iteritems(data):
            if k==self.run_id:
                runData[k]=v
            elif isinstance(v,integer_types+(float,)):
                runData[k]=float(v)
            else:
                runData[k]=uniCode(str(v))
        cols=self.__getColumns(table)[1:]
        addData=[]
        for c in cols:
            try:
                addData.append(runData[c])
            except KeyError:
                addData.append(None)
        addData=tuple(addData)
        if update_run is None:
            cSQL = "insert into "+table+" ("+ \
                ",".join(['"'+self.__normalize(c)+'"' for c in cols])+ \
                ") values ("+",".join(["?"]*len(addData))+")"
            sqlData = addData
        else:
            dataCursor = self.db.cursor()
            dataCursor.execute("SELECT * FROM {} WHERE {}=?".format(table,
                                                                    self.run_id),
                               (update_run, ))
            dataHere = dataCursor.fetchall()
            if len(dataHere) < 1:
                cSQL = "insert into {} ( {} ) values ( {} )".format(table,
                                                                    self.run_id,
                                                                    update_run)
                if self.verbose:
                    print_("Execute SQL", cSQL, "to add an aerelmost empty row")
                cursor.execute(cSQL)
            cols = [c for c in cols if c in data]
            cSQL = "update " + table + " set " + \
                " , ".join(['"{}" = ?'.format(self.__normalize(c)) for c in cols]) + \
                " where {} = ?".format(self.run_id)
            sqlData = tuple(runData[c] for c in cols) + (update_run,)
        if self.verbose:
            print_("Execute SQL",cSQL,"with",sqlData)
        try:
            cursor.execute(cSQL, sqlData)
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            print_("SQL-Expression:",cSQL)
            print_("AddData:",addData)
            raise e

        lastrow=cursor.lastrowid
        cursor.close()

        return lastrow

    def __adaptDatabase(self,data):
        """Make sure that all the required columns and tables are there"""

        c=self.db.execute('SELECT name FROM sqlite_master WHERE type = "table"')
        tables=[ x["name"] for x in c.fetchall() ]

        indata=dict([(k,v) for k,v in iteritems(data) if type(v)!=dict])
        subtables=dict([(k,v) for k,v in iteritems(data) if type(v)==dict])

        self.__addColumnsToTable(self.TheRunsName,indata)

        for tn,content in iteritems(subtables):
            if tn+"Data" not in tables:
                if self.verbose:
                    print_("Adding table",tn)
                self.db.execute(
                    "CREATE TABLE {}Data (dataId INTEGER PRIMARY KEY, {} INTEGER)".format(
                        tn, self.run_id))
            self.__addColumnsToTable(tn+"Data",
                                     self.__flattenDict(content))

    def __flattenDict(self,oData,prefix=""):
        data=[(prefix+k,v) for k,v in iteritems(oData) if type(v)!=dict]
        subtables=dict([(k,v) for k,v in iteritems(oData) if type(v)==dict])
        for name,val in iteritems(subtables):
            data+=list(self.__flattenDict(val,prefix+name+self.separator).items())
        if self.verbose:
            print_("Flattened",oData,"to",data)
        return dict(data)

    def __getColumns(self,tablename):
        c=self.db.execute('SELECT * from '+tablename)
        result=[]
        for desc in c.description:
            if desc[0] in ['dataId',self.run_id]:
                result.append(desc[0])
            else:
                result.append(self.__denormalize(desc[0]))

        return result

    def __addColumnsToTable(self,table,data):
        columns=self.__getColumns(table)

        for k,v in iteritems(data):
            if k not in columns:
                if self.verbose:
                    print_("Adding:",k,"to",table,"(normalized:",
                           self.__normalize(k),")")
                if isinstance(v,integer_types+(float,)):
                    self.db.execute('ALTER TABLE "%s" ADD COLUMN "%s" REAL' %
                                    (table,self.__normalize(k)))
                else:
                    self.db.execute('ALTER TABLE "%s" ADD COLUMN "%s" TEXT' %
                                    (table,self.__normalize(k)))

    def dumpToCSV(self,
                  fname,
                  selection=None,
                  disableRunData=None,
                  pandasFormat=True,
                  excel=False):
        """Dump the contents of the database to a csv-file
        :param name: the CSV-file
        :param selection: list of regular expressions. Only data
        entries fitting those will be added to the CSV-file (except
        for the basic run). If unset all data will be written"""
        file=CSVCollection(fname)

        runCursor=self.db.cursor()
        runCursor.execute("SELECT * from theRuns")

        c=self.db.execute('SELECT name FROM sqlite_master WHERE type = "table"')
        tables=[ x["name"] for x in c.fetchall() ]

        allData=set()
        writtenData=set()

        disabledStandard=set()

        for d in runCursor:
            id=d[self.run_id]
            if self.verbose:
                print_("Dumping run",id)
            for k in list(d.keys()):
                writeEntry=True
                if disableRunData:
                    for e in disableRunData:
                        exp=re.compile(e)
                        if not exp.search(self.__denormalize(k)) is None:
                            writeEntry=False
                            break
                    if writeEntry:
                        file[k]=d[k]
                    else:
                        disabledStandard.add(k)
            for t in tables:
                if t==self.TheRunsName:
                    namePrefix="runInfo"
                else:
                    namePrefix=t[:-4]
                dataCursor=self.db.cursor()
                dataCursor.execute("SELECT * FROM "+t+" WHERE {}=?".format(self.run_id),
                                   (str(id),))
                data=dataCursor.fetchall()
                if len(data)>1:
                    error(len(data),"data items found for id ",id,
                          "in table",t,".Need exactly 1")
                elif len(data)<1:
                    continue
                for k in list(data[0].keys()):
                    if k in ["dataId", self.run_id]:
                        continue
                    if k in disabledStandard:
                        continue
                    name=namePrefix+self.separator+self.__denormalize(k)
                    allData.add(name)
                    writeEntry=True
                    if selection:
                        writeEntry=False
                        for e in selection:
                            exp=re.compile(e)
                            if exp.search(name):
                                writeEntry=True
                                break
                    if writeEntry:
                        writtenData.add(name)
                        file[name]=data[0][k]

            file.write()

        if self.verbose:
            sep="\n    "
            if allData==writtenData:
                print_("Added all data entries:",sep,sep.join(sorted(allData)),sep="")
            else:
                print_("Added parameters:",sep,sep.join(sorted(writtenData)),
                       "\nUnwritten data:",sep,sep.join(sorted(allData-writtenData)),sep="")
            if len(disabledStandard)>0:
                print_("Disabled standard entries:",sep,sep.join(sorted(disabledStandard)),sep="")

        f=file(pandasFormat)
        if excel:
            file(True).to_excel(fname)

        if not f is None:
            return f
        else:
            # retry by forcing to numpy
            return file(False)

# Should work with Python3 and Python2
