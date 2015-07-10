# This example demonstrates how to regrid between a grid and a mesh.
# The data files can be retrieved from the ESMF data repository by uncommenting the
# following block of code:
#
# import os
# if not os.path.isdir("data"):
#     os.makedirs("data")
# from ESMF.util.cache_data import cache_data_file
# cache_data_file(os.path.join(os.getcwd(), "data", "ll1deg_grid.nc"))

import ESMF
import numpy

# This call enables debug logging
ESMF.Manager(debug=True)

from ESMF.test.test_api.locstream_utilities import create_locstream_spherical_16, create_locstream_spherical_16_parallel
coord_sys=ESMF.CoordSys.SPH_DEG
if ESMF.pet_count() == 1:
    locstream = create_locstream_spherical_16(coord_sys=coord_sys)
else:
    if ESMF.pet_count() is not 4:
        raise ValueError("processor count must be 4 or 1 for this example")
    else:
        locstream = create_locstream_spherical_16_parallel(coord_sys=coord_sys)

grid1 = "examples/data/ll1deg_grid.nc"
grid = ESMF.Grid(filename=grid1, filetype=ESMF.FileFormat.SCRIP)

# create a field
srcfield = ESMF.Field(grid, name='srcfield')

# create a field on the locstream
dstfield = ESMF.Field(locstream, name='dstfield')
xctfield = ESMF.Field(locstream, name='xctfield')

# initialize the fields
[x, y] = [0, 1]
deg2rad = 3.14159/180

gridXCoord = srcfield.grid.get_coords(x)
gridYCoord = srcfield.grid.get_coords(y)
srcfield.data[...] = 10.0 + (gridXCoord * deg2rad) ** 2 + (gridYCoord * deg2rad) ** 2

gridXCoord = locstream["ESMF:Lon"]
gridYCoord = locstream["ESMF:Lat"]
if coord_sys == ESMF.CoordSys.SPH_DEG:
    xctfield.data[...] = 10.0 + (gridXCoord * deg2rad) ** 2 + (gridYCoord * deg2rad) ** 2
elif coord_sys == ESMF.CoordSys.SPH_RAD:
    xctfield.data[...] = 10.0 + (gridXCoord) ** 2 + (gridYCoord) ** 2
else:
    raise ValueError("coordsys value not supported")

dstfield.data[...] = 1e20

# create an object to regrid data from the source to the destination field
# TODO: this example seems to fail occasionally with UnmappedAction.ERROR, probably due to a tolerance issue - ask Bob
regrid = ESMF.Regrid(srcfield, dstfield,
                     regrid_method=ESMF.RegridMethod.BILINEAR,
                     unmapped_action=ESMF.UnmappedAction.IGNORE)

# do the regridding from source to destination field
dstfield = regrid(srcfield, dstfield)


# compute the mean relative error
from operator import mul
num_nodes = reduce(mul, xctfield.shape)
relerr = 0
meanrelerr = 0
if num_nodes is not 0:
    ind = numpy.where((dstfield.data != 1e20) & (xctfield.data != 0))
    relerr = numpy.sum(numpy.abs(dstfield.data[ind] - xctfield.data[ind]) / numpy.abs(xctfield.data[ind]))
    meanrelerr = relerr / num_nodes

# handle the parallel case
if ESMF.pet_count() > 1:
    try:
        from mpi4py import MPI
    except:
        raise ImportError
    comm = MPI.COMM_WORLD
    relerr = comm.reduce(relerr, op=MPI.SUM)
    num_nodes = comm.reduce(num_nodes, op=MPI.SUM)

# output the results from one processor only
if ESMF.local_pet() is 0:
    meanrelerr = relerr / num_nodes
    print "ESMPy Grid Mesh Regridding Example"
    print "  interpolation mean relative error = {0}".format(meanrelerr)
