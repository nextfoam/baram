# $Id: gnuplot_Suites.py 292 2006-03-03 09:49:04Z mhagger $

# This file is provided as part of the Gnuplot.py package for the
# convenience of Mac users.  It was generated primarily using gensuitemodule
# with Mac gnuplot 3.7.1a.  Thanks to Anthony M. Ingraldi and Noboru Yamamoto
# for helping with this.

# file contains
#
#  class gnuplot_Suite
#  class odds_and_ends
#  class Standard_Suite
#  class Miscellaneous_Events
#
"""Suite gnuplot Suite: Events supplied by gnuplot
Level 1, version 1

Generated from Alpha:Desktop Folder:gnuplot.1:gnuplot 3.7.1a
AETE/AEUT resource version 1/0, language 0, script 0
"""

import aetools
import MacOS

_code = 'GPSE'

class gnuplot_Suite:

    def gnuexec(self, _object=None, _attributes={}, **_arguments):
        """exec: execute a gnuplot command
        Required argument: gnuplot command
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'GPSE'
        _subcode = 'exec'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def plot(self, _object=None, _attributes={}, **_arguments):
        """plot: create a 2-D plot


        Required argument: data to be plotted
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'GPLT'
        _subcode = 'plot'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def splot(self, _object=None, _attributes={}, **_arguments):
        """splot: create a 3-D plot
        Required argument: data to be plotted
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'GPLT'
        _subcode = 'splt'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']


class graph(aetools.ComponentItem):
    """graph - graph - a subclass of window"""
    want = 'cGRF'
class picture(aetools.NProperty):
    """picture - gnuplot graph in "PICT" format"""
    which = 'PICT'
    want = 'PICT'
graph._propdict = {
    'picture' : picture,
}
graph._elemdict = {
}
_Enum_lyty = {
    'line' : 'typ1',    # line
    'points' : 'typ2',  # points
    'impulses' : 'typ3',    # impulses
    'linespoints' : 'typ4', # linespoints
    'dots' : 'typ5',    # dots
    'steps' : 'typ6',   # steps
    'fsteps' : 'typ7',  # fsteps
    'errorbars' : 'typ8',   # errorbars
    'xerrorbars' : 'typ9',  # xerrorbars
    'yerrorbars' : 'ty10',  # yerrorbars
    'xyerrorbars' : 'ty11', # xyerrorbars
    'boxes' : 'ty12',   # boxes
    'boxerrorbars' : 'ty13',    # boxerrorbars
    'boxxyerrorbars' : 'ty14',  # boxxyerrorbars
    'vector' : 'ty19',  # vector
}


#
# Indices of types declared in this module
#
_classdeclarations = {
    'cGRF' : graph,
}

_propdeclarations = {
    'PICT' : picture,
}

_compdeclarations = {
}

_enumdeclarations = {
    'lyty' : _Enum_lyty,
}


"""Suite odds and ends: Things that should be in some standard suite, but aren't
Level 1, version 1

Generated from Alpha:Desktop Folder:gnuplot.1:gnuplot 3.7.1a
AETE/AEUT resource version 1/0, language 0, script 0
"""

import aetools
import MacOS

_code = 'Odds'

class odds_and_ends:

    def select(self, _object=None, _attributes={}, **_arguments):
        """select: Select the specified object
        Required argument: the object to select
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'misc'
        _subcode = 'slct'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']


#
# Indices of types declared in this module
#
_classdeclarations = {
}

_propdeclarations = {
}

_compdeclarations = {
}

_enumdeclarations = {
}

"""Suite Standard Suite: Common terms for most applications
Level 1, version 1

Generated from Alpha:Desktop Folder:gnuplot.1:gnuplot 3.7.1a
AETE/AEUT resource version 1/0, language 0, script 0
"""

import aetools
import MacOS

_code = 'CoRe'

class Standard_Suite:

    _argmap_close = {
        'saving' : 'savo',
        '_in' : 'kfil',
    }

    def close(self, _object, _attributes={}, **_arguments):
        """close: Close an object
        Required argument: the objects to close
        Keyword argument saving: specifies whether or not changes should be saved before closing
        Keyword argument _in: the file in which to save the object
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'core'
        _subcode = 'clos'

        aetools.keysubst(_arguments, self._argmap_close)
        _arguments['----'] = _object

        aetools.enumsubst(_arguments, 'savo', _Enum_savo)

        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def data_size(self, _object, _attributes={}, **_arguments):
        """data size: Return the size in bytes of an object
        Required argument: the object whose data size is to be returned
        Keyword argument _attributes: AppleEvent attribute dictionary
        Returns: the size of the object in bytes
        """
        _code = 'core'
        _subcode = 'dsiz'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def get(self, _object, _attributes={}, **_arguments):
        """get: Get the data for an object
        Required argument: the object whose data is to be returned
        Keyword argument _attributes: AppleEvent attribute dictionary
        Returns: The data from the object
        """
        _code = 'core'
        _subcode = 'getd'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    _argmap_make = {
        'new' : 'kocl',
        'at' : 'insh',
        'with_data' : 'data',
        'with_properties' : 'prdt',
    }

    def make(self, _no_object=None, _attributes={}, **_arguments):
        """make: Make a new element
        Keyword argument new: the class of the new element
        Keyword argument at: the location at which to insert the element
        Keyword argument with_data: the initial data for the element
        Keyword argument with_properties: the initial values for the properties of the element
        Keyword argument _attributes: AppleEvent attribute dictionary
        Returns: Object specifier for the new element
        """
        _code = 'core'
        _subcode = 'crel'

        aetools.keysubst(_arguments, self._argmap_make)
        if _no_object != None: raise TypeError('No direct arg expected')


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def open(self, _object, _attributes={}, **_arguments):
        """open: Open the specified object(s)
        Required argument: Objects to open. Can be a list of files or an object specifier.
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'aevt'
        _subcode = 'odoc'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def _print(self, _object, _attributes={}, **_arguments):
        """print: Print the specified object(s)
        Required argument: Objects to print. Can be a list of files or an object specifier.
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'aevt'
        _subcode = 'pdoc'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    _argmap_save = {
        '_in' : 'kfil',
        'as' : 'fltp',
    }

    def save(self, _object, _attributes={}, **_arguments):
        """save: save a set of objects
        Required argument: Objects to save.
        Keyword argument _in: the file in which to save the object(s)
        Keyword argument as: the file type of the document in which to save the data
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'core'
        _subcode = 'save'

        aetools.keysubst(_arguments, self._argmap_save)
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    _argmap_set = {
        'to' : 'data',
    }

    def set(self, _object, _attributes={}, **_arguments):
        """set: Set an objects data
        Required argument: the object to change
        Keyword argument to: the new value
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'core'
        _subcode = 'setd'

        aetools.keysubst(_arguments, self._argmap_set)
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']


class application(aetools.ComponentItem):
    """application - An application program"""
    want = 'capp'
#        element 'cwin' as ['indx', 'name', 'rele']
#        element 'docu' as ['name']

class window(aetools.ComponentItem):
    """window - A Window"""
    want = 'cwin'
class bounds(aetools.NProperty):
    """bounds - the boundary rectangle for the window"""
    which = 'pbnd'
    want = 'qdrt'
class closeable(aetools.NProperty):
    """closeable - Does the window have a close box?"""
    which = 'hclb'
    want = 'bool'
class titled(aetools.NProperty):
    """titled - Does the window have a title bar?"""
    which = 'ptit'
    want = 'bool'
class index(aetools.NProperty):
    """index - the number of the window"""
    which = 'pidx'
    want = 'long'
class floating(aetools.NProperty):
    """floating - Does the window float?"""
    which = 'isfl'
    want = 'bool'
class modal(aetools.NProperty):
    """modal - Is the window modal?"""
    which = 'pmod'
    want = 'bool'
class resizable(aetools.NProperty):
    """resizable - Is the window resizable?"""
    which = 'prsz'
    want = 'bool'
class zoomable(aetools.NProperty):
    """zoomable - Is the window zoomable?"""
    which = 'iszm'
    want = 'bool'
class zoomed(aetools.NProperty):
    """zoomed - Is the window zoomed?"""
    which = 'pzum'
    want = 'bool'
class name(aetools.NProperty):
    """name - the title of the window"""
    which = 'pnam'
    want = 'itxt'
class visible(aetools.NProperty):
    """visible - is the window visible?"""
    which = 'pvis'
    want = 'bool'
class position(aetools.NProperty):
    """position - upper left coordinates of window"""
    which = 'ppos'
    want = 'QDpt'

class document(aetools.ComponentItem):
    """document - A Document"""
    want = 'docu'
# repeated property name the title of the document
class modified(aetools.NProperty):
    """modified - Has the document been modified since the last save?"""
    which = 'imod'
    want = 'bool'
application._propdict = {
}
application._elemdict = {
    'window' : window,
    'document' : document,
}
window._propdict = {
    'bounds' : bounds,
    'closeable' : closeable,
    'titled' : titled,
    'index' : index,
    'floating' : floating,
    'modal' : modal,
    'resizable' : resizable,
    'zoomable' : zoomable,
    'zoomed' : zoomed,
    'name' : name,
    'visible' : visible,
    'position' : position,
}
window._elemdict = {
}
document._propdict = {
    'name' : name,
    'modified' : modified,
}
document._elemdict = {
}
_Enum_savo = {
    'yes' : 'yes ', # Save objects now
    'no' : 'no  ',  # Do not save objects
    'ask' : 'ask ', # Ask the user whether to save
}


#
# Indices of types declared in this module
#
_classdeclarations = {
    'cwin' : window,
    'docu' : document,
    'capp' : application,
}

_propdeclarations = {
    'ptit' : titled,
    'pidx' : index,
    'ppos' : position,
    'pnam' : name,
    'pbnd' : bounds,
    'imod' : modified,
    'isfl' : floating,
    'hclb' : closeable,
    'iszm' : zoomable,
    'pmod' : modal,
    'pzum' : zoomed,
    'pvis' : visible,
    'prsz' : resizable,
}

_compdeclarations = {
}

_enumdeclarations = {
    'savo' : _Enum_savo,
}

"""Suite Miscellaneous Events: Useful events that aren't in any other suite
Level 1, version 1

Generated from Alpha:Desktop Folder:gnuplot.1:gnuplot 3.7.1a
AETE/AEUT resource version 1/0, language 0, script 0
"""

import aetools
import MacOS

_code = 'misc'

class Miscellaneous_Events:

    def revert(self, _object, _attributes={}, **_arguments):
        """revert: Revert an object to the most recently saved version
        Required argument: object to revert
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'misc'
        _subcode = 'rvrt'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']

    def do_script(self, _object=None, _attributes={}, **_arguments):
        """do script: execute a gnuplot script
        Required argument: a gnuplot script
        Keyword argument _attributes: AppleEvent attribute dictionary
        """
        _code = 'misc'
        _subcode = 'dosc'

        if _arguments: raise TypeError('No optional args expected')
        _arguments['----'] = _object


        _reply, _arguments, _attributes = self.send(_code, _subcode,
                _arguments, _attributes)
        if 'errn' in _arguments:
            raise aetools.Error(aetools.decodeerror(_arguments))
        # XXXX Optionally decode result
        if '----' in _arguments:
            return _arguments['----']


#
# Indices of types declared in this module
#
_classdeclarations = {
}

_propdeclarations = {
}

_compdeclarations = {
}

_enumdeclarations = {
}

# Should work with Python3 and Python2
