# $Id$

import os
import sys

import ESMF.api.constants as constants

parallel = False
if len(sys.argv) > 1:
    if "--parallel" in sys.argv[1]:
        parallel = True

# run utests, pipe to file
num_proc = 1
if parallel:
    # make sure we are not in uni mode
    if constants._ESMF_COMM == constants._ESMF_COMM_MPIUNI:
        raise ValueError("Cannot run parallel tests when ESMF is built with ESMF_COMM=mpiuni")

    # setup the constants
    num_proc = 4

if constants._ESMF_OS is constants._ESMF_OS_UNICOS:
    os.system("aprun -n "+str(num_proc)+" -a xt nosetests -vs")
else:
    if parallel:
        os.system("mpirun -np "+str(num_proc)+" nosetests -vs")
    else:
        os.system("nosetests -vs")
