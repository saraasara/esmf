# $Id$

"""
examples test file
"""

import pytest

from ESMF.test.base import TestBase, attr

class TestRFFDryrun(TestBase):

    def test_regrid_from_file_dryrun(self):
        from ESMF.test.regrid_from_file import run_regrid_from_file_dryrun
