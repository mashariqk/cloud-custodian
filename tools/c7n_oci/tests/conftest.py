# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import os
from distutils.util import strtobool

import pytest
from pytest_terraform import tf

from tools.c7n_oci.tests.oci_flight_recorder import OCIFlightRecorder
from oci_common import replace_ocid, replace_email

tf.LazyReplay.value = not strtobool(os.environ.get('C7N_FUNCTIONAL', 'no'))
tf.LazyPluginCacheDir.value = '../.tfcache'

try:
    from pytest_terraform.tf import LazyPluginCacheDir, LazyReplay

    from c7n.testing import PyTestUtils, reset_session_cache
except ImportError:
    class PyTestUtils:
        pass


    class PillTest:
        pass


    class LazyReplay:
        pass


    class LazyPluginCacheDir:
        pass


class CustodianOCITesting(PyTestUtils, OCIFlightRecorder):
    """Pytest OCI Testing Fixture
        """


@pytest.fixture(scope='function')
def test(request):
    test_utils = CustodianOCITesting(request)
    test_utils.addCleanup(reset_session_cache)
    return test_utils

@pytest.hookimpl(tryfirst=True)
def pytest_xdist_auto_num_workers(config):
    return 1

def pytest_terraform_modify_state(tfstate):
    tfstate.update(replace_ocid(str(tfstate)))
    tfstate.update(replace_email(str(tfstate)))
