# -*- coding: utf-8 -*-
"""
EVT (Kinemetrics) support for ObsPy.
Base classes (cannot be directly called)

:copyright:
    Royal Observatory of Belgium, 2013
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from future.builtins import *  # NOQA

from obspy import UTCDateTime


class EVTBaseError(Exception):
    """
    Base Class for all EVT specific errors.
    """
    pass


class EVTBadDataError(EVTBaseError):
    """
    Raised if bad data is encountered while reading an EVT file.
    """
    pass


class EVTBadHeaderError(EVTBaseError):
    """
    Raised if an error occured while parsing an EVT header.
    """
    pass


class EVTEOFError(EVTBaseError):
    """
    Raised if an unexpected EOF is encountered.
    """
    pass


class EVT_Virtual(object):
    """
    class for parameters reading.
    The dictionary has this structure :
       {"name":[header_place,["function","param"],value], ...}
            name is the attribute (key) (in lower cases)
            header_place : offset to find value in file
            function : function to call to set value (option)
            param : parameters to send to function
            value : value of name (can be omitted)
    """
    def __init__(self):
        self.diconame = ""

    def __getattr__(self, item):
        """
        __getattr__ is called only if no class attribute is found
        :type item: str
        :param item: name of the attribute (key)
        :rtype: any
        :return: the value in the dictionary
        """
        key = item.lower()
        if key in self.HEADER:
            return self.HEADER[key][2]

    def unsetdico(self):
        """
        remove all values from dictionary
        """
        for key in self.HEADER:
            try:
                self.HEADER[key].pop(2)
            except IndexError:
                pass

    def setdico(self, val, offset=0):
        """
        fill the dictionary with values found in the input 'val' list
            the nth value in val is placed in the dictionary if a key
            of type 'name':[nth, ''] exist
            the offset is used to include the 'val' list further
            in the dictionary
        :type val: list
        :param val : a list of values
        :type offset: int
        :param offset : offset in the dictionary
        """
        if not isinstance(val, list):
            raise TypeError("setdico() expects a list")
        for key in self.HEADER:
            index = self.HEADER[key][0] - offset
            if index < len(val) and index >= 0:
                if self.HEADER[key][1] != "":
                    fct = self.HEADER[key][1][0]
                    param = self.HEADER[key][1][1]
                    value = getattr(self, fct)(val[index], param, val, offset)
                else:
                    value = val[index]
                try:
                    self.HEADER[key][2] = value
                except IndexError:
                    self.HEADER[key].append(value)

    def __str__(self):
        """
        create a string with all dictionary values
        :rtype:  str
        :return: string representation of dictionary
        """
        chaine = ""
        for vname in sorted(self.HEADER):
            chaine += vname + "\t is \t" + str(getattr(self, vname)) + "\n"
        return chaine

    def _time(self, blocktime, param, val, offset):
        """
        change a EVT time format to
                :class:`~obspy.core.utcdatetime.UTCDateTime` format
        :param blocktime : time in sec after 1980/1/1
        :param param: parameter with milliseconds values (in val)
        :param val: list of value
        :param offset: Not used
        """
        frame_time = blocktime
        if param > 0:
            frame_milli = val[param-offset]
        else:
            frame_milli = 0
        frame_time += 315532800  # diff between 1970/1/1 and 1980/1/1
        time = UTCDateTime(frame_time) + frame_milli/1000.0
        time.precison = 3
        return time

    def _strnull(self, strn, param, val, offset):
        """
        Change a C string (null terminated to Python string)

        :type strn: str
        :param strn: string to convert
        :param param: not used
        :param val: not used
        :param offset: not used
        :rtype: str
        """
        try:
            return strn.rstrip("\0")
        except AttributeError:
            return strn

    def _array(self, firstval, param, val, offset):
        """
        extract a list of values from val
        :param firstval: first value to extract (unused)
        :param param: a list with the size of the list, the dimension of the
                 structure, and the first value to read
        :param val: list of values
        :param offset: not used
        :rtype: list
        :return: a list of values
        """
        ret = []
        sizearray = param[0]
        sizestru = param[1]
        index0 = param[2]
        for i in range(sizearray):
            ret.append(val[index0-offset+(i*sizestru)])
        return ret

    def _arraynull(self, firstval, param, val, offset):
        """
        extract a list of values from val and change C string to python
        :param firstval: first value to extract (unused)
        :param param: a list with the size of the list, the dimension of the
                 structure, and the first value to read
        :param val: list of value
        :param offset:
        :rtype: list
        :return: a list of values
        """

        ret = []
        sizearray = param[0]
        sizestru = param[1]
        index0 = param[2]
        for i in range(sizearray):
            mystr = self._strnull(val[index0-offset+(i*sizestru)], '', '', '')
            ret.append(mystr)
        return ret

    def _instrument(self, code, param, val, offset):
        """
        change instrument type code to name
        :param code: code to convert
        :param param: not used
        :param val: not used
        :param offset: not used
        :rtype: str
        """
        dico = {0: 'QDR', 9: 'K2', 10: 'Makalu', 20: 'New Etna',
                30: 'Rock', 40: 'SSA2EVT'}
        if code in dico:
            return dico[code]
        else:
            raise EVTBadHeaderError("Bad Instrument Code")
