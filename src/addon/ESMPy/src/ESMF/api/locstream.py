# $Id$

"""
The LocStream API
"""

#### IMPORT LIBRARIES #########################################################

from ESMF.api.esmpymanager import *
from ESMF.util.esmpyarray import ndarray_from_esmf
import ESMF.api.constants as constants
from ESMF.util.slicing import get_formatted_slice


#### LocStream class #########################################################

class LocStream(dict):
    """
    The LocStream class is a Python wrapper object for the ESMF LocStream.  LocStream is a derived type of the
    Python dict class.
    The individual values of all key arrays are referenced to those of the underlying Fortran ESMF object.

    A location stream (LocStream) is used to represent the locations of a set of data points. The values of the
    data points are stored within a Field created using the LocStream.

    In the data assimilation world, LocStreams can be thought of as a set of observations. Their locations are
    generally described using Cartesian (x, y, z), or (lat, lon, height) coordinates. There is no assumption of
    any regularity in the positions of the points. To make the concept more general, the locations for each data
    point are represented using a construct called keys. Keys can include other descriptors besides location,
    including a second set of coordinates.

    For more information about the ESMF LocStream class, please see the `ESMF LocStream documentation
    <http://www.earthsystemmodeling.org/esmf_releases/public/last/ESMF_refdoc/node5.html#SECTION05090000000000000000>`_.

    LocStream follows standard Python.dict behavior for setting and getting keys.  For example::

        locstream["ESMF:X"] = [1, 2, 3]
        x = locstream["ESMF:X"]
        locstream["ESMF:Y"] = [1, 2, 3]
        y = locstream["ESMF:Y"]
        locstream["ESMF:Mask"] = [0, 1, 0]
        mask = locstream["ESMF:Mask"]

    NOTE: Setting keys of lists of mixed types can result in errors due to type mismatches from the ESMF library.

    NOTE: Mask must be of type TypeKind.I4, and coordinates must by of type TypeKind.R8

    For ESMF to be able to recognize coordinates specified in a LocStream key they need to be named with the
    appropriate identifiers. The particular identifiers depend on the coordinate system (i.e. coord_sys argument)
    used to create the LocStream.

    The valid values are:

    ===================  ===========  ===========  ===========
    Coordinate System    dimension 1  dimension 2  dimension 3
    ===================  ===========  ===========  ===========
    CoordSys.SPH_DEG     ESMF:Lon     ESMF:Lat     ESMF:Radius
    CoordSys.SPH_RAD     ESMF:Lon     ESMF:Lat     ESMF:Radius
    CoordSys.CART        ESMF:X       ESMF:Y       ESMF:Z
    ===================  ===========  ===========  ===========
    """

    @initialize
    def __init__(self, location_count, coord_sys=None, name=None, esmf=True):
        '''
        Create a LocStream. \n
        Required Arguments: \n
            location_count: the number of point in this stream. \n
        Optional Arguments: \n
            coord_sys: the coordinates system for the Grid. \n
                    Argument values are:\n
                        (default) CoordSys.CART\n
                        CoordSys.SPH_DEG\n
                        CoordSys.SPH_RAD\n
            name: user friendly name for the LocStream. \n
            esmf: internal parameter to allow "shallow" copies. \n
        '''

        # for ocgis compatibility
        self._ocgis = {}

        # bookkeeping
        self._rank = 1
        self._name = name
        self._size = location_count

        # call the ESMP layer
        if esmf:
            self._struct = ESMP_LocStreamCreateLocal(location_count,
                                                     coordSys=coord_sys)

            # get bounds
            lbounds, ubounds = ESMP_LocStreamGetBounds(self.struct)
            self._lower_bounds = lbounds
            self._upper_bounds = ubounds

        # regist with atexit
        import atexit;
        atexit.register(self.__del__)
        self._finalized = False

        # set the single stagger flag
        self._singlestagger = True

        super(LocStream, self).__init__()

    def __del__(self):
        """
        Release the memory associated with a LocStream. \n
        Required Arguments: \n
            None \n
        Optional Arguments: \n
            None \n
        Returns: \n
            None \n
        """
        self.destroy()

    def __getitem__(self, slc):
        # initialize slc_ls
        slc_ls = slc

        # check that this is actually a slicing operation and not just regular item retrieval
        if not isinstance(slc, basestring):
            # parallel slicing is not yet enabled (collective operation)
            if pet_count() > 1:
                raise SerialMethod
            # re-initialize slc_ls
            slc_ls = get_formatted_slice(slc, self.rank)

        # slice at will
        try:
            ret = super(LocStream, self).__getitem__(slc_ls)
        except TypeError:
            ret = self.copy()

            # upper bounds and size
            ret._upper_bounds = len(range(slc_ls.stop - slc_ls.start))
            ret._size = ret.upper_bounds - ret.lower_bounds

            # keys
            for x in ret.iterkeys():
                ret[x] = super(LocStream, self).__getitem__(x)[slc_ls]

        return ret

    def __repr__(self):
        """
        Return a string containing a printable representation of the object
        """
        string = ("LocStream:\n"
                  "    name = %r \n"
                  "    lower_bounds = %r \n"
                  "    upper_bounds = %r \n"
                  "    keys = %r \n"
                  %
                  (self.name,
                   self.lower_bounds,
                   self.upper_bounds,
                   self.items(),
                   ))

        return string

    def __setitem__(self, key, value):
        # check types
        if not isinstance(value, (list, tuple, np.ndarray)):
            raise ValueError("type of value must be list, tuple, or numpy array")
        if type(value) is not np.ndarray:
            value = np.array(value)
        if len(value) != self.size:
            raise ValueError("value must be of length " + str(self.size))

        keyvals = value
        if key not in self:
            keyvals = self._add_(key, typekind=constants._Python2ESMFType[type(value[0])])

        ret = dict.__setitem__(self, key, keyvals)

        keyvals[...] = value

        return ret

    @property
    def lower_bounds(self):
        """
        :return: the lower bounds of the LocStream
        """
        return self._lower_bounds

    @property
    def mask(self):
        """
        :return: the mask of the LocStream
        """
        try:
            return self["ESMF:Mask"]
        except:
            return None
    @property
    def name(self):
        """
        :return: the name of the LocStream
        """
        return self._name

    @property
    def rank(self):
        """
        :return: the rank of the LocStream
        """
        return self._rank

    @property
    def singlestagger(self):
        return self._singlestagger

    @property
    def size(self):
        return self._size

    @property
    def struct(self):
        return self._struct

    @property
    def upper_bounds(self):
        """
        :return: the upper bounds of the LocStream
        """
        return self._upper_bounds

    def copy(self):
        """
        Copy a LocStream in an ESMF-safe manner. \n
        Required Arguments: \n
            None \n
        Optional Arguments: \n
            None \n
        Returns: \n
            A new LocStream copy. \n
        """
        # shallow copy
        ret = LocStream(self._size, name=self._name, esmf=False)

        ret._struct = self._struct
        ret._lower_bounds = self._lower_bounds
        ret._upper_bounds = self._upper_bounds

        for key, value in self.iteritems():
            super(LocStream, ret).__setitem__(key, value)

        # don't call ESMF destructor twice on the same shallow Python object
        ret._finalized = True

        return ret

    def destroy(self):
        """
        Release the memory associated with a LocStream. \n
        Required Arguments: \n
            None \n
        Optional Arguments: \n
            None \n
        Returns: \n
            None \n
        """
        if hasattr(self, '_finalized'):
            if not self._finalized:
                ESMP_LocStreamDestroy(self)
                self._finalized = True

    def _add_(self, key_name, typekind=None):
        # allocate the key
        ESMP_LocStreamAddKeyAlloc(self.struct, key_name, keyTypeKind=typekind)

        # get a pointer to the Fortran buffer to the key
        key_ptr = ESMP_LocStreamGetKeyPtr(self.struct, key_name)

        # create a numpy array out of the pointer
        keyvals = ndarray_from_esmf(key_ptr, typekind, (self.size,))

        return keyvals