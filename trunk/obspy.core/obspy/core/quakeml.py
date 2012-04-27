# -*- coding: utf-8 -*-
"""
QuakeML read and write support.

QuakeML is a flexible, extensible and modular XML representation of
seismological data which is intended to cover a broad range of fields of
application in modern seismology. QuakeML is an open standard and is developed
by a distributed team in a transparent collaborative manner.

.. seealso:: https://quake.ethz.ch/quakeml/

:copyright:
    The ObsPy Development Team (devs@obspy.org)
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""

from obspy.core.event import Catalog, Event, Origin, CreationInfo, Magnitude, \
    EventDescription, OriginUncertainty, OriginQuality, CompositeTime, \
    IntegerQuantity, FloatQuantity, TimeQuantity, ConfidenceEllipsoid, \
    StationMagnitude, Comment, WaveformStreamID, Arrival, Pick
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.util.xmlwrapper import XMLParser, tostring, etree
import StringIO


def isQuakeML(filename):
    """
    Checks whether a file is QuakeML format.

    :type filename: str
    :param filename: Name of the QuakeML file to be checked.
    :rtype: bool
    :return: ``True`` if QuakeML file.

    .. rubric:: Example

    >>> isSLIST('/path/to/quakeml.xml')  # doctest: +SKIP
    True
    """
    try:
        p = XMLParser(filename)
    except:
        False
    # check node "*/eventParameters/event" for the global namespace exists
    try:
        namespace = p._getFirstChildNamespace()
        p.xpath('eventParameters/event', namespace=namespace)[0]
    except:
        return False
    return True


class Unpickler(object):
    """
    De-serializes a QuakeML string into an ObsPy Catalog object.
    """
    def __init__(self, parser=None):
        self.parser = parser

    def load(self, file):
        """
        Reads QuakeML file into ObsPy catalog object.

        :type file: str
        :param file: File name to read.
        :rtype: :class:`~obspy.core.event.Catalog`
        :returns: ObsPy Catalog object.
        """
        self.parser = XMLParser(file)
        return self._deserialize()

    def loads(self, string):
        """
        Parses QuakeML string into ObsPy catalog object.

        :type string: str
        :param string: QuakeML string to parse.
        :rtype: :class:`~obspy.core.event.Catalog`
        :returns: ObsPy Catalog object.
        """
        self.parser = XMLParser(StringIO.StringIO(string))
        return self._deserialize()

    def _xpath2obj(self, *args, **kwargs):
        return self.parser.xpath2obj(*args, **kwargs)

    def _xpath(self, *args, **kwargs):
        return self.parser.xpath(*args, **kwargs)

    def _comments(self, element):
        obj = []
        for el in self._xpath('comment', element):
            comment = Comment()
            comment.text = self._xpath2obj('text', el)
            temp = el.get('id', None)
            if temp is not None:
                comment.resource_id = temp
            comment.creation_info = self._creation_info(el)
            obj.append(comment)
        return obj

    def _creation_info(self, element):
        has_creation_info = False
        for child in element:
            if 'creationInfo' in child.tag:
                has_creation_info = True
                break
        if not has_creation_info:
            return None
        obj = CreationInfo()
        obj.agency_uri = self._xpath2obj('creationInfo/agencyURI', element)
        obj.author_uri = self._xpath2obj('creationInfo/authorURI', element)
        obj.agency_id = self._xpath2obj('creationInfo/agencyID', element)
        obj.author = self._xpath2obj('creationInfo/author', element)
        obj.creation_time = self._xpath2obj('creationInfo/creationTime',
            element, UTCDateTime)
        obj.version = self._xpath2obj('creationInfo/version', element)
        return obj

    def _origin_quality(self, element):
        obj = OriginQuality()
        obj.associated_phase_count = self._xpath2obj(
            'quality/associatedPhaseCount', element, int)
        obj.used_phase_count = self._xpath2obj(
            'quality/usedPhaseCount', element, int)
        obj.associated_station_count = self._xpath2obj(
            'quality/associatedStationCount', element, int)
        obj.used_station_count = self._xpath2obj(
            'quality/usedStationCount', element, int)
        obj.depth_phase_count = self._xpath2obj(
            'quality/depthPhaseCount', element, int)
        obj.standard_error = self._xpath2obj(
            'quality/standardError', element, float)
        obj.azimuthal_gap = self._xpath2obj(
            'quality/azimuthalGap', element, float)
        obj.secondary_azimuthal_gap = self._xpath2obj(
            'quality/secondaryAzimuthalGap', element, float)
        obj.ground_truth_level = self._xpath2obj(
            'quality/groundTruthLevel', element)
        obj.minimum_distance = self._xpath2obj(
            'quality/minimumDistance', element, float)
        obj.maximum_distance = self._xpath2obj(
            'quality/maximumDistance', element, float)
        obj.median_distance = self._xpath2obj(
            'quality/medianDistance', element, float)
        return obj

    def _event_description(self, element):
        out = []
        for el in self._xpath('description', element):
            text = self._xpath2obj('text', el)
            type = self._xpath2obj('type', el)
            out.append(EventDescription(text=text, type=type))
        return out

    def _value(self, element, name, quantity_type=FloatQuantity):
        obj = quantity_type()
        try:
            el = self._xpath(name, element)[0]
        except:
            return obj
        obj.value = self._xpath2obj('value', el, quantity_type._value_type)
        obj.uncertainty = self._xpath2obj('uncertainty', el, float)
        obj.lower_uncertainty = self._xpath2obj('lowerUncertainty', el, float)
        obj.upper_uncertainty = self._xpath2obj('upperUncertainty', el, float)
        obj.confidence_level = self._xpath2obj('confidenceLevel', el, float)
        return obj

    def _float_value(self, element, name):
        return self._value(element, name, FloatQuantity)

    def _int_value(self, element, name):
        return self._value(element, name, IntegerQuantity)

    def _time_value(self, element, name):
        return self._value(element, name, TimeQuantity)

    def _composite_times(self, element):
        obj = []
        for el in self._xpath('compositeTime', element):
            ct = CompositeTime()
            ct.year = self._int_value(el, 'year')
            ct.month = self._int_value(el, 'month')
            ct.day = self._int_value(el, 'day')
            ct.hour = self._int_value(el, 'hour')
            ct.minute = self._int_value(el, 'minute')
            ct.second = self._float_value(el, 'second')
            obj.append(ct)
        return obj

    def _confidence_ellipsoid(self, element):
        obj = ConfidenceEllipsoid()
        obj.semi_major_axis_length = self._xpath2obj(
            'semiMajorAxisLength', element, float)
        obj.semi_minor_axis_length = self._xpath2obj(
            'semiMinorAxisLength', element, float)
        obj.semi_intermediate_axis_length = self._xpath2obj(
            'semiIntermediateAxisLength', element, float)
        obj.major_axis_plunge = self._xpath2obj(
            'majorAxisPlunge', element, float)
        obj.major_axis_azimuth = self._xpath2obj(
            'majorAxisAzimuth', element, float)
        obj.major_axis_rotation = self._xpath2obj(
            'majorAxisRotation', element, float)
        return obj

    def _origin_uncertainty(self, element):
        obj = OriginUncertainty()
        obj.preferred_description = self._xpath2obj(
            'originUncertainty/preferredDescription', element)
        obj.horizontal_uncertainty = self._xpath2obj(
            'originUncertainty/horizontalUncertainty', element, float)
        obj.min_horizontal_uncertainty = self._xpath2obj(
            'originUncertainty/minHorizontalUncertainty', element, float)
        obj.max_horizontal_uncertainty = self._xpath2obj(
            'originUncertainty/maxHorizontalUncertainty', element, float)
        obj.azimuth_max_horizontal_uncertainty = self._xpath2obj(
            'originUncertainty/azimuthMaxHorizontalUncertainty', element,
            float)
        try:
            ce_el = self._xpath('originUncertainty/confidenceEllipsoid',
                                element)
            obj.confidence_ellipsoid = self._confidence_ellipsoid(ce_el[0])
        except:
            obj.confidence_ellipsoid = ConfidenceEllipsoid()
        return obj

    def _waveform_id(self, element):
        obj = WaveformStreamID()
        try:
            wid_el = self._xpath('waveformID', element)[0]
        except:
            return obj
        obj.network_code = wid_el.get('networkCode') or ''
        obj.station_code = wid_el.get('stationCode') or ''
        obj.location_code = wid_el.get('locationCode')
        obj.channel_code = wid_el.get('channelCode')
        obj.resource_id = wid_el.text
        return obj

    def _arrival(self, element):
        """
        Converts an etree.Element into an Arrival object.

        :type parser: :class:`~obspy.core.util.xmlwrapper.XMLParser`
        :type element: etree.Element
        :rtype: :class:`~obspy.core.event.Arrival`
        """
        obj = Arrival()
        # required parameter
        obj.resource_id = element.get('publicID')
        obj.phase = self._xpath2obj('phase', element) or ''
        # optional parameter
        obj.pick_id = self._xpath2obj('pickID', element) or ''
        obj.time_correction = self._xpath2obj('timeCorrection', element, float)
        obj.azimuth = self._xpath2obj('azimuth', element, float)
        obj.distance = self._xpath2obj('distance', element, float)
        obj.time_residual = self._xpath2obj('timeResidual', element, float)
        obj.horizontal_slowness_residual = \
            self._xpath2obj('horizontalSlownessResidual', element, float)
        obj.backazimuth_residual = \
            self._xpath2obj('backazimuthResidual', element, float)
        obj.time_used = self._xpath2obj('timeUsed', element, bool)
        obj.horizontal_slowness_used = \
            self._xpath2obj('horizontalSlownessUsed', element, bool)
        obj.backazimuth_used = self._xpath2obj('backazimuthUsed', element,
                                               bool)
        obj.time_weight = self._xpath2obj('timeWeight', element, float)
        obj.earth_model_id = self._xpath2obj('earthModelID', element)
        obj.preliminary = element.get('preliminary')
        obj.comments = self._comments(element)
        obj.creation_info = self._creation_info(element)
        return obj

    def _pick(self, element):
        """
        Converts an etree.Element into a Pick object.

        :type parser: :class:`~obspy.core.util.xmlwrapper.XMLParser`
        :type element: etree.Element
        :rtype: :class:`~obspy.core.event.Pick`
        """
        obj = Pick()
        # required parameter
        obj.resource_id = element.get('publicID')
        obj.time = self._time_value(element, 'time')
        obj.waveform_id = self._waveform_id(element)
        # optional parameter
        obj.filter_id = self._xpath2obj('filterID', element)
        obj.method_id = self._xpath2obj('methodID', element)
        obj.horizontal_slowness = \
            self._float_value(element, 'horizontalSlowness')
        obj.backazimuth = self._float_value(element, 'backazimuth')
        obj.slowness_method_id = self._xpath2obj('slownessMethodID', element)
        obj.onset = self._xpath2obj('onset', element)
        obj.phase_hint = self._xpath2obj('phaseHint', element)
        obj.polarity = self._xpath2obj('polarity', element)
        obj.evaluation_mode = self._xpath2obj('evaluationMode', element)
        obj.evaluation_status = self._xpath2obj('evaluationStatus', element)
        obj.comments = self._comments(element)
        obj.creation_info = self._creation_info(element)
        return obj

    def _origin(self, element):
        """
        Converts an etree.Element into an Origin object.

        :type parser: :class:`~obspy.core.util.xmlwrapper.XMLParser`
        :type element: etree.Element
        :rtype: :class:`~obspy.core.event.Origin`

        .. rubric:: Example

        >>> from obspy.core.util import XMLParser
        >>> XML = '<?xml version="1.0" encoding="UTF-8"?>'
        >>> XML += '<origin><latitude><value>34.23</value></latitude></origin>'
        >>> parser = XMLParser(XML)
        >>> unpickler = Unpickler(parser)
        >>> origin = unpickler._origin(parser.xml_root)
        >>> print(origin.latitude.value)
        34.23
        """
        obj = Origin()
        # required parameter
        obj.resource_id = element.get('publicID')
        obj.time = self._time_value(element, 'time')
        obj.latitude = self._float_value(element, 'latitude')
        obj.longitude = self._float_value(element, 'longitude')
        # optional parameter
        obj.depth = self._float_value(element, 'depth')
        obj.depth_type = self._xpath2obj('depthType', element)
        obj.time_fixed = self._xpath2obj('timeFixed', element, bool)
        obj.epicenter_fixed = self._xpath2obj('epicenterFixed', element, bool)
        obj.reference_system_id = self._xpath2obj('referenceSystemID', element)
        obj.method_id = self._xpath2obj('methodID', element)
        obj.earth_model_id = self._xpath2obj('earthModelID', element)
        obj.composite_times = self._composite_times(element)
        obj.quality = self._origin_quality(element)
        obj.origin_type = self._xpath2obj('type', element)
        obj.evaluation_mode = self._xpath2obj('evaluationMode', element)
        obj.evaluation_status = self._xpath2obj('evaluationStatus', element)
        obj.creation_info = self._creation_info(element)
        obj.comments = self._comments(element)
        obj.origin_uncertainty = self._origin_uncertainty(element)
        return obj

    def _magnitude(self, element):
        """
        Converts an etree.Element into a Magnitude object.

        :type parser: :class:`~obspy.core.util.xmlwrapper.XMLParser`
        :type element: etree.Element
        :rtype: :class:`~obspy.core.event.Magnitude`

        .. rubric:: Example

        >>> from obspy.core.util import XMLParser
        >>> XML = '<?xml version="1.0" encoding="UTF-8"?>'
        >>> XML += '<magnitude><mag><value>3.2</value></mag></magnitude>'
        >>> parser = XMLParser(XML)
        >>> unpickler = Unpickler(parser)
        >>> magnitude = unpickler._magnitude(parser.xml_root)
        >>> print(magnitude.mag.value)
        3.2
        """
        obj = Magnitude()
        # required parameter
        obj.resource_id = element.get('publicID')
        obj.mag = self._float_value(element, 'mag')
        # optional parameter
        obj.magnitude_type = self._xpath2obj('type', element)
        obj.origin_id = self._xpath2obj('originID', element)
        obj.method_id = self._xpath2obj('methodID', element)
        obj.station_count = self._xpath2obj('stationCount', element, int)
        obj.azimuthal_gap = self._xpath2obj('azimuthalGap', element, float)
        obj.evaluation_status = self._xpath2obj('evaluationStatus', element)
        obj.creation_info = self._creation_info(element)
        obj.comments = self._comments(element)
        return obj

    def _station_magnitude(self, element):
        """
        Converts an etree.Element into a StationMagnitude object.

        :type parser: :class:`~obspy.core.util.xmlwrapper.XMLParser`
        :type element: etree.Element
        :rtype: :class:`~obspy.core.event.StationMagnitude`

        .. rubric:: Example

        >>> from obspy.core.util import XMLParser
        >>> XML = '<?xml version="1.0" encoding="UTF-8"?><stationMagnitude>'
        >>> XML += '<mag><value>3.2</value></mag></stationMagnitude>'
        >>> parser = XMLParser(XML)
        >>> unpickler = Unpickler(parser)
        >>> station_mag = unpickler._station_magnitude(parser.xml_root)
        >>> print(station_mag.mag.value)
        3.2
        """
        obj = StationMagnitude()
        # required parameter
        obj.resource_id = element.get('publicID')
        obj.origin_id = self._xpath2obj('originID', element) or ''
        obj.mag = self._float_value(element, 'mag')
        # optional parameter
        obj.station_magnitude_type = self._xpath2obj('type', element)
        obj.amplitude_id = self._xpath2obj('amplitudeID', element)
        obj.method_id = self._xpath2obj('methodID', element)
        obj.waveform_id = self._waveform_id(element)
        obj.creation_info = self._creation_info(element)
        obj.comments = self._comments(element)
        return obj

    def _deserialize(self):
        # check node "quakeml/eventParameters" for global namespace
        try:
            namespace = self.parser._getFirstChildNamespace()
            catalog_el = self._xpath('eventParameters', namespace=namespace)[0]
        except:
            raise Exception("Not a QuakeML compatible file or string")
        # set default namespace for parser
        self.parser.namespace = self.parser._getElementNamespace(catalog_el)
        # create catalog
        catalog = Catalog()
        # optional catalog attributes
        catalog.resource_id = catalog_el.get('publicID')
        catalog.description = self._xpath2obj('description', catalog_el)
        catalog.comments = self._comments(catalog_el)
        catalog.creation_info = self._creation_info(catalog_el)
        # loop over all events
        for event_el in self._xpath('event', catalog_el):
            # create new Event object
            resource_id = event_el.get('publicID')
            event = Event(resource_id)
            # optional event attributes
            event.preferred_origin_id = \
                self._xpath2obj('preferredOriginID', event_el)
            event.preferred_magnitude_id = \
                self._xpath2obj('preferredMagnitudeID', event_el)
            event.preferred_focal_mechanism_id = \
                self._xpath2obj('preferredFocalMechanismID', event_el)
            event.type = self._xpath2obj('type', event_el)
            event.type_certainty = self._xpath2obj('typeCertainty', event_el)
            event.creation_info = self._creation_info(event_el)
            event.descriptions = self._event_description(event_el)
            event.comments = self._comments(event_el)
            # origins
            event.origins = []
            for origin_el in self._xpath('origin', event_el):
                origin = self._origin(origin_el)
                # arrivals
                origin.arrivals = []
                for arrival_el in self._xpath('arrival', origin_el):
                    arrival = self._arrival(arrival_el)
                    origin.arrivals.append(arrival)
                # append origin with arrivals
                event.origins.append(origin)
            # magnitudes
            event.magnitudes = []
            for magnitude_el in self._xpath('magnitude', event_el):
                magnitude = self._magnitude(magnitude_el)
                event.magnitudes.append(magnitude)
            # station magnitudes
            event.station_magnitudes = []
            for magnitude_el in self._xpath('stationMagnitude', event_el):
                magnitude = self._station_magnitude(magnitude_el)
                event.station_magnitudes.append(magnitude)
            # picks
            event.picks = []
            for pick_el in self._xpath('pick', event_el):
                pick = self._pick(pick_el)
                event.picks.append(pick)
            # add current event to catalog
            catalog.append(event)
        return catalog


class Pickler(object):
    """
    Serializes an ObsPy Catalog object into QuakeML format.
    """
    def dump(self, catalog, file):
        """
        Writes ObsPy Catalog into given file.

        :type catalog: :class:`~obspy.core.event.Catalog`
        :param catalog: ObsPy Catalog object.
        :type file: str
        :param file: File name.
        """
        fh = open(file, 'wt')
        fh.write(self._serialize(catalog))
        fh.close()

    def dumps(self, catalog):
        """
        Returns QuakeML string of given ObsPy Catalog object.

        :type catalog: :class:`~obspy.core.event.Catalog`
        :param catalog: ObsPy Catalog object.
        :rtype: str
        :returns: QuakeML formated string.
        """
        return self._serialize(catalog)

    def _id(self, obj, default=""):
        try:
            return obj.getQuakeMLURI()
        except:
            return default

    def _str(self, value, root, tag, always_create=False):
        if always_create is False and value is None:
            return
        etree.SubElement(root, tag).text = "%s" % (value)

    def _bool(self, value, root, tag, always_create=False):
        if always_create is False and value is None:
            return
        etree.SubElement(root, tag).text = str(bool(value)).lower()

    def _time(self, value, root, tag, always_create=False):
        if always_create is False and value is None:
            return
        dt = value.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        etree.SubElement(root, tag).text = "%s" % (dt)

    def _value(self, quantity, element, tag, always_create=False):
        if always_create is False and quantity.value is None:
            return
        subelement = etree.Element(tag)
        self._str(quantity.value, subelement, 'value')
        self._str(quantity.uncertainty, subelement, 'uncertainty')
        self._str(quantity.lower_uncertainty, subelement, 'lowerUncertainty')
        self._str(quantity.upper_uncertainty, subelement, 'upperUncertainty')
        self._str(quantity.confidence_level, subelement, 'confidenceLevel')
        element.append(subelement)

    def _waveform_id(self, obj, element, required=True):  # @UnusedVariable
        attrib = {}
        if obj is None:
            return
        if obj.network_code:
            attrib['networkCode'] = obj.network_code
        if obj.station_code:
            attrib['stationCode'] = obj.station_code
        if obj.location_code:
            attrib['locationCode'] = obj.location_code
        if obj.channel_code:
            attrib['channelCode'] = obj.channel_code
        subelement = etree.Element('waveformID', attrib=attrib)
        subelement.text = self._id(obj.resource_id)
        element.append(subelement)

    def _creation_info(self, creation_info, element):
        if creation_info is None:
            return
        subelement = etree.Element('creationInfo')
        self._str(creation_info.agency_id, subelement, 'agencyID')
        self._str(creation_info.agency_uri, subelement, 'agencyURI')
        self._str(creation_info.author, subelement, 'author')
        self._str(creation_info.author_uri, subelement, 'authorURI')
        self._time(creation_info.creation_time, subelement, 'creationTime')
        self._str(creation_info.version, subelement, 'version')
        # append only if any information is set
        if len(subelement) > 0:
            element.append(subelement)

    def _comments(self, comments, element):
        for comment in comments:
            attrib = {}
            if comment.resource_id:
                attrib['id'] = self._id(comment.resource_id)
            comment_el = etree.Element('comment', attrib=attrib)
            etree.SubElement(comment_el, 'text').text = comment.text
            self._creation_info(comment.creation_info, comment_el)
            element.append(comment_el)

    def _arrival(self, arrival):
        """
        Converts an Arrival into etree.Element object.

        :type arrival: :class:`~obspy.core.event.Arrival`
        :rtype: etree.Element
        """
        attrib = {'publicID': self._id(arrival.resource_id)}
        if arrival.preliminary:
            attrib['preliminary'] = str(arrival.preliminary).lower()
        element = etree.Element('arrival', attrib=attrib)
        # required parameter
        self._str(arrival.pick_id, element, 'pickID', True)
        self._str(arrival.phase, element, 'phase', True)
        # optional parameter
        self._str(arrival.time_correction, element, 'timeCorrection')
        self._str(arrival.azimuth, element, 'azimuth')
        self._str(arrival.distance, element, 'distance')
        self._str(arrival.time_residual, element, 'timeResidual')
        self._str(arrival.horizontal_slowness_residual, element,
                  'horizontalSlownessResidual')
        self._str(arrival.backazimuth_residual, element, 'backazimuthResidual')
        self._bool(arrival.time_used, element, 'timeUsed')
        self._bool(arrival.horizontal_slowness_used, element,
                   'horizontalSlownessUsed')
        self._bool(arrival.backazimuth_used, element, 'backazimuthUsed')
        self._str(arrival.time_weight, element, 'timeWeight')
        self._str(arrival.earth_model_id, element, 'earthModelID')
        self._comments(arrival.comments, element)
        self._creation_info(arrival.creation_info, element)
        return element

    def _magnitude(self, magnitude):
        """
        Converts an Magnitude into etree.Element object.

        :type magnitude: :class:`~obspy.core.event.Magnitude`
        :rtype: etree.Element

        .. rubric:: Example

        >>> from obspy.core.quakeml import Pickler
        >>> from obspy.core.event import Magnitude
        >>> from obspy.core.util import tostring
        >>> magnitude = Magnitude()
        >>> magnitude.mag.value = 3.2
        >>> el = Pickler()._magnitude(magnitude)
        >>> print(tostring(el))  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        <?xml version='1.0' encoding='utf-8'?>
        <magnitude ...<mag><value>3.2</value></mag>...</magnitude>
        """
        element = etree.Element('magnitude',
            attrib={'publicID': self._id(magnitude.resource_id)})
        self._value(magnitude.mag, element, 'mag', True)
        # optional parameter
        self._str(magnitude.magnitude_type, element, 'type')
        self._str(magnitude.origin_id, element, 'originID')
        self._str(magnitude.method_id, element, 'methodID')
        self._str(magnitude.station_count, element, 'stationCount')
        self._str(magnitude.azimuthal_gap, element, 'azimuthalGap')
        self._str(magnitude.evaluation_status, element, 'evaluationStatus')
        self._comments(magnitude.comments, element)
        self._creation_info(magnitude.creation_info, element)
        return element

    def _station_magnitude(self, magnitude):
        """
        Converts an StationMagnitude into etree.Element object.

        :type magnitude: :class:`~obspy.core.event.StationMagnitude`
        :rtype: etree.Element

        .. rubric:: Example

        >>> from obspy.core.quakeml import Pickler
        >>> from obspy.core.event import StationMagnitude
        >>> from obspy.core.util import tostring
        >>> station_mag = StationMagnitude()
        >>> station_mag.mag.value = 3.2
        >>> el = Pickler()._station_magnitude(station_mag)
        >>> print(tostring(el))  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        <?xml version='1.0' encoding='utf-8'?>
        <stationMagnitude ...<value>3.2</value>...</stationMagnitude>
        """
        element = etree.Element('stationMagnitude',
            attrib={'publicID': self._id(magnitude.resource_id)})
        self._str(magnitude.origin_id, element, 'originID', True)
        self._value(magnitude.mag, element, 'mag', True)
        # optional parameter
        self._str(magnitude.station_magnitude_type, element, 'type')
        self._str(magnitude.amplitude_id, element, 'amplitudeID')
        self._str(magnitude.method_id, element, 'methodID')
        self._waveform_id(magnitude.waveform_id, element)
        self._comments(magnitude.comments, element)
        self._creation_info(magnitude.creation_info, element)
        return element

    def _origin(self, origin):
        """
        Converts an Origin into etree.Element object.

        :type origin: :class:`~obspy.core.event.Origin`
        :rtype: etree.Element

        .. rubric:: Example

        >>> from obspy.core.quakeml import Pickler
        >>> from obspy.core.event import Origin
        >>> from obspy.core.util import tostring
        >>> origin = Origin()
        >>> origin.latitude.value = 34.23
        >>> el = Pickler()._origin(origin)
        >>> print(tostring(el))  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
        <?xml version='1.0' encoding='utf-8'?>
        <origin ...<latitude><value>34.23</value></latitude>...</origin>
        """
        element = etree.Element('origin',
            attrib={'publicID': self._id(origin.resource_id)})
        self._value(origin.time, element, 'time', True)
        self._value(origin.latitude, element, 'latitude', True)
        self._value(origin.longitude, element, 'longitude', True)
        # optional parameter
        self._value(origin.depth, element, 'depth')
        self._str(origin.depth_type, element, 'depthType')
        self._bool(origin.time_fixed, element, 'timeFixed')
        self._bool(origin.epicenter_fixed, element, 'epicenterFixed')
        self._str(origin.reference_system_id, element, 'referenceSystemID')
        self._str(origin.method_id, element, 'methodID')
        self._str(origin.earth_model_id, element, 'earthModelID')
        # compositeTime
        for ctime in origin.composite_times:
            ct_el = etree.Element('compositeTime')
            self._value(ctime.year, ct_el, 'year')
            self._value(ctime.month, ct_el, 'month')
            self._value(ctime.day, ct_el, 'day')
            self._value(ctime.hour, ct_el, 'hour')
            self._value(ctime.minute, ct_el, 'minute')
            self._value(ctime.second, ct_el, 'second')
            if len(ct_el) > 0:
                element.append(ct_el)
        # quality
        qu = origin.quality
        if qu:
            qu_el = etree.Element('quality')
            self._str(qu.associated_phase_count, qu_el, 'associatedPhaseCount')
            self._str(qu.used_phase_count, qu_el, 'usedPhaseCount')
            self._str(qu.associated_station_count, qu_el,
                      'associatedStationCount')
            self._str(qu.used_station_count, qu_el, 'usedStationCount')
            self._str(qu.depth_phase_count, qu_el, 'depthPhaseCount')
            self._str(qu.standard_error, qu_el, 'standardError')
            self._str(qu.azimuthal_gap, qu_el, 'azimuthalGap')
            self._str(qu.secondary_azimuthal_gap, qu_el,
                      'secondaryAzimuthalGap')
            self._str(qu.ground_truth_level, qu_el, 'groundTruthLevel')
            self._str(qu.minimum_distance, qu_el, 'minimumDistance')
            self._str(qu.maximum_distance, qu_el, 'maximumDistance')
            self._str(qu.median_distance, qu_el, 'medianDistance')
            if len(qu_el) > 0:
                element.append(qu_el)
        self._str(origin.origin_type, element, 'type')
        self._str(origin.evaluation_mode, element, 'evaluationMode')
        self._str(origin.evaluation_status, element, 'evaluationStatus')
        self._comments(origin.comments, element)
        self._creation_info(origin.creation_info, element)
        # origin uncertainty
        ou = origin.origin_uncertainty
        if ou is not None:
            ou_el = etree.Element('originUncertainty')
            self._str(ou.preferred_description, ou_el, 'preferredDescription')
            self._str(ou.horizontal_uncertainty, ou_el,
                      'horizontalUncertainty')
            self._str(ou.min_horizontal_uncertainty, ou_el,
                      'minHorizontalUncertainty')
            self._str(ou.max_horizontal_uncertainty, ou_el,
                      'maxHorizontalUncertainty')
            self._str(ou.azimuth_max_horizontal_uncertainty, ou_el,
                      'azimuthMaxHorizontalUncertainty')
            ce = ou.confidence_ellipsoid
            if ce is not None:
                ce_el = etree.Element('confidenceEllipsoid')
                self._str(ce.semi_major_axis_length, ce_el,
                          'semiMajorAxisLength')
                self._str(ce.semi_minor_axis_length, ce_el,
                          'semiMinorAxisLength')
                self._str(ce.semi_intermediate_axis_length, ce_el,
                          'semiIntermediateAxisLength')
                self._str(ce.major_axis_plunge, ce_el, 'majorAxisPlunge')
                self._str(ce.major_axis_azimuth, ce_el, 'majorAxisAzimuth')
                self._str(ce.major_axis_rotation, ce_el, 'majorAxisRotation')
                # add confidence ellipsoid to origin uncertainty only if set
                if len(ce_el) > 0:
                    ou_el.append(ce_el)
            # add origin uncertainty to origin only if anything is set
            if len(ou_el) > 0:
                element.append(ou_el)
        # arrivals
        for ar in origin.arrivals:
            element.append(self._arrival(ar))
        return element

    def _pick(self, pick):
        """
        Converts a Pick into etree.Element object.

        :type pick: :class:`~obspy.core.event.Pick`
        :rtype: etree.Element
        """
        element = etree.Element('pick',
        attrib={'publicID': self._id(pick.resource_id)})
        # required parameter
        self._value(pick.time, element, 'time', True)
        self._waveform_id(pick.waveform_id, element, True)
        # optional parameter
        self._str(pick.filter_id, element, 'filterID')
        self._str(pick.method_id, element, 'methodID')
        self._value(pick.horizontal_slowness, element, 'horizontalSlowness')
        self._value(pick.backazimuth, element, 'backazimuth')
        self._str(pick.slowness_method_id, element, 'slownessMethodID')
        self._str(pick.onset, element, 'onset')
        self._str(pick.phase_hint, element, 'phaseHint')
        self._str(pick.polarity, element, 'polarity')
        self._str(pick.evaluation_mode, element, 'evaluationMode')
        self._str(pick.evaluation_status, element, 'evaluationStatus')
        self._comments(pick.comments, element)
        self._creation_info(pick.creation_info, element)
        return element

    def _serialize(self, catalog, pretty_print=True):
        """
        Converts a Catalog object into XML string.
        """
        root_el = etree.Element(
            '{http://quakeml.org/xmlns/quakeml/1.2}quakeml',
            attrib={'xmlns': "http://quakeml.org/xmlns/bed/1.2"})
        catalog_el = etree.Element('eventParameters',
            attrib={'publicID': self._id(catalog.resource_id, None)})
        # optional catalog parameters
        self._str(catalog.description, catalog_el, 'description')
        self._comments(catalog.comments, catalog_el)
        self._creation_info(catalog.creation_info, catalog_el)
        root_el.append(catalog_el)
        for event in catalog:
            # create event node
            event_el = etree.Element('event',
                attrib={'publicID': self._id(event.resource_id)})
            # optional event attributes
            self._str(event.preferred_origin_id, event_el, 'preferredOriginID')
            self._str(event.preferred_magnitude_id, event_el,
                     'preferredMagnitudeID')
            self._str(event.preferred_focal_mechanism_id, event_el,
                     'preferredFocalMechanismID')
            self._str(event.type, event_el, 'type')
            self._str(event.type_certainty, event_el, 'typeCertainty')
            # event descriptions
            for description in event.descriptions:
                el = etree.Element('description')
                self._str(description.text, el, 'text', True)
                self._str(description.type, el, 'type')
                event_el.append(el)
            self._comments(event.comments, event_el)
            self._creation_info(event.creation_info, event_el)
            # origins
            for origin in event.origins:
                event_el.append(self._origin(origin))
            # magnitudes
            for magnitude in event.magnitudes:
                event_el.append(self._magnitude(magnitude))
            # station magnitudes
            for magnitude in event.station_magnitudes:
                event_el.append(self._station_magnitude(magnitude))
            # picks
            for pick in event.picks:
                event_el.append(self._pick(pick))
            # add event node to catalog
            catalog_el.append(event_el)
        return tostring(root_el, pretty_print=pretty_print)


def readQuakeML(filename):
    """
    Reads a QuakeML file and returns a ObsPy Catalog object.

    .. warning::
        This function should NOT be called directly, it registers via the
        ObsPy :func:`~obspy.core.event.readEvents` function, call this instead.

    :type filename: str
    :param filename: QuakeML file to be read.
    :rtype: :class:`~obspy.core.event.Catalog`
    :return: A ObsPy Catalog object.

    .. rubric:: Example

    >>> from obspy.core.event import readEvents
    >>> cat = readEvents('/path/to/iris_events.xml')
    >>> print cat
    2 Event(s) in Catalog:
    2011-03-11T05:46:24.120000Z | +38.297, +142.373 | 9.1 MW
    2006-09-10T04:26:33.610000Z |  +9.614, +121.961 | 9.8 MS
    """
    return Unpickler().load(filename)


def writeQuakeML(catalog, filename, **kwargs):  # @UnusedVariable
    """
    Writes a QuakeML file.

    .. warning::
        This function should NOT be called directly, it registers via the
        the :meth:`~obspy.core.event.Catalog.write` method of an
        ObsPy :class:`~obspy.core.event.Catalog` object, call this instead.

    :type catalog: :class:`~obspy.core.stream.Catalog`
    :param catalog: The ObsPy Catalog object to write.
    :type filename: str
    :param filename: Name of file to write.
    """
    raise NotImplementedError


def readSeisHubEventXML(filename):
    """
    Reads a single SeisHub event XML file and returns a ObsPy Catalog object.
    """
    # XXX: very ugly way to add new root tags without parsing
    lines = open(filename, 'rt').readlines()
    lines.insert(2, '<quakeml xmlns="http://quakeml.org/xmlns/quakeml/1.0">\n')
    lines.insert(3, '  <eventParameters>')
    lines.append('  </eventParameters>\n')
    lines.append('</quakeml>\n')
    temp = StringIO.StringIO(''.join(lines))
    return readQuakeML(temp)


if __name__ == '__main__':
    import doctest
    doctest.testmod(exclude_empty=True)