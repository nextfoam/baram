#  ICE Revision: $Id$
"""PermanentStorage

Store data permanently in the metadata of a notebook
"""

from IPython.display import Javascript,display
from PyFoam.ThirdParty.six.moves import cPickle as pickle
import base64
from IPython.utils.py3compat import str_to_bytes, bytes_to_str
from time import sleep

class PermanentStorage(object):
    """Access the stored values in the notebook

    To make sure that only one object is created (so that multiple objects
    can't interfer) it is created as a singleton. See:
    A python singleton: http://code.activestate.com/recipes/52558/"""

    # Value we get from the dark side (Javascript). Technically a global variable. But we're dealing with JavaScript here'
    _data={}
    # this is so ugly. But I don't know a better way

    class __permanentStorage(object):
        """Actual implementation of the storage """

        __storePath="IPython.notebook.metadata.pyFoam.storedData"

        __outputHandle="""
    function handle_output(out){
        console.log(out);
        var res = null;
         // if output is a print statement
        if(out.msg_type == "stream"){
            res = out.content.data;
        }
        // if output is a python object
        else if(out.msg_type === "pyout"){
            res = out.content.data["text/plain"];
        }
        // if output is a python error
        else if(out.msg_type == "pyerr"){
            res = out.content.ename + ": " + out.content.evalue;
        }
        // if output is something we haven't thought of
        else{
            res = "[out type not implemented]";
        }
        console.log(res);
    }
    var callbacks =  {'iopub' : {'output' : handle_output}};
    """

        def __init__(self):
            """Make sure that there is a subdictionary in the notebook-metadata"""
            self.__autowrite=False
            self.__autoread=True
            display(Javascript(self.__outputHandle+"""
function ensurePyFoamStorage() {
  if (typeof IPython =="undefined") {
      alert("Trying to use PyFoam.IPythonHelpers.PermanentStorage outside of IPython");
      return;
  } else if(IPython.notebook==undefined) {
      alert("Trying to use PyFoam.IPythonHelpers.PermanentStorage outside of an IPython-notebook");
      return;
  } else if(IPython.notebook.metadata.pyFoam==undefined) {
      IPython.notebook.metadata.pyFoam=Object();
      console.log("IPython.notebook.metadata.pyFoam created");
  } else {
      console.log("IPython.notebook.metadata.pyFoam found");
  }
  if(IPython.notebook.metadata.pyFoam.storedData==undefined) {
      IPython.notebook.metadata.pyFoam.storedData=Object();
      console.log("IPython.notebook.metadata.pyFoam.storedData created");
  } else {
      console.log("IPython.notebook.metadata.pyFoam.storedData found");
  }

  var store=IPython.notebook.metadata.pyFoam.storedData;
  var expr="from PyFoam.IPythonHelpers.PermanentStorage import PermanentStorage as perm\\nperm._data={}";
  status="Starting transfer";
  var kernel=IPython.notebook.kernel;
  kernel.execute(expr, callbacks, {silent:false});
  for(var k in store) {
      var totalLen=store[k].length;
      console.log("Found stored "+k+" Length: "+totalLen);
//      expr+="'"+k+"' : '"+store[k]+"' ,";
      var chunk=400; // seems to be the best compromise
      var nChunks=(totalLen/chunk|0)+1;
      for(var i=0;i<nChunks;i++) {
          status="chunk "+(i+1)+" of "+nChunks+" of "+k;
          var value = store[k].substring(i*chunk,(i+1)*chunk);
          var command ="perm._data['"+k+"']";
          if(i>0) {
            command+="+=";
          } else {
            command+="=";
          }
          command += "'"+value+"'";
          kernel.execute(command);
      }
  }
  status="Starting transfer (this can take some time)";
  console.log("Execution of python done");
}
ensurePyFoamStorage();
                       """))
            self.__displayModes()

        def __getitem__(self,attr):
             try:
                  return pickle.loads(
                       bytes_to_str(base64.b64decode(str_to_bytes(
                            PermanentStorage._data[attr]))))
             except TypeError as e:
                  return "TypeError: "+str(e)

        def __setitem__(self,attr,value):
            """Set property in the metadata"""
            pick=bytes_to_str(base64.b64encode(str_to_bytes(pickle.dumps(value))))
            name=attr
            PermanentStorage._data[attr]=pick
            display(Javascript('%s["%s"]="%s";console.log("Setting %s");' % (self.__storePath,
                                                 name,
                                                 pick,
                                                 name)));

        def __delitem__(self,attr):
            """Remove the property from the metadata"""
            name=attr
            del PermanentStorage._data[attr]
            display(Javascript('delete %s.%s;console.log("Deleting %s");' % (self.__storePath,
                                                  name,name)));

        def __iter__(self):
             return PermanentStorage._data.__iter__()

        def iterkeys(self):
             return PermanentStorage._data.iterkeys()

        def keys(self):
             return PermanentStorage._data.keys()

        def __contains__(self,key):
             return key in PermanentStorage._data

        def __call__(self,name,f,call=True):
            """Get value or evaluate it.
            :param name: name of the item to get/set
            :param f: function to evaluate if the item is not present. If
            item is not callable (strings for instance) it is set 'as-is'
            :param call: Use f() if possible (otherwise f)"""
            val=None
            if self.__autoread:
                try:
                    val=self[name]
                except KeyError:
                    val=None
            if val is None:
                if hasattr(f,'__call__') and call:
                    val=f()
                else:
                    val=f
                if self.__autowrite:
                    self[name]=val
            return val

        def __displayModes(self):
            msg="Storage status: Autowrite: "+str(self.__autowrite)+" Autoread: "+str(self.__autoread)
            display(Javascript('status="'+msg+'"'))

        def autowriteOn(self):
            """The ()-operator should automatically set the value in the metadata"""
            self.__autowrite=True
            self.__displayModes()

        def autowriteOff(self):
            """The ()-operator should not automatically set the value in the metadata"""
            self.__autowrite=False
            self.__displayModes()

        def autoreadOn(self):
            """The ()-operator should automatically get the value from the metadata"""
            self.__autoread=True
            self.__displayModes()

        def autoreadOff(self):
            """The ()-operator should not automatically get the value from the metadata"""
            self.__autoread=False
            self.__displayModes()

    # storage for the instance reference
    __instance = None

    def __init__(self):
        """ Create the singleon """
        # Check whether we already have an instance
        if PermanentStorage.__instance is None:
            # Create and remember instance
            PermanentStorage.__instance = PermanentStorage.__permanentStorage()

        # Store instance reference as the only member in the handle
        self.__dict__['_PermanentStorage__instance'] = PermanentStorage.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)

    def __getitem__(self,attr):
        """Get property from the metadata"""
        return self.__instance.__getitem__(attr)

    def __delitem__(self,attr):
        """Delete property from the metadata"""
        return self.__instance.__delitem__(attr)

    def __iter__(self):
        """Iterate over properties of the metadata"""
        return self.__instance.__iter__()

    def __contains__(self,key):
        """Is property in the metadata"""
        return self.__instance.__contains__(key)

    def __setitem__(self,attr,value):
        """Set property in the metadata"""
        return self.__instance.__setitem__(attr,value)

    def __call__(self,name,f,call=True):
        return self.__instance(name,f,call)
