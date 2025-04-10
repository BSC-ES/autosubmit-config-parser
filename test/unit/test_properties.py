import os

import pytest


@pytest.mark.parametrize("is_owner", [True, False])
def test_is_current_real_user_owner(autosubmit_config, mocker, is_owner):
    """Test if the SUDO_USER from the environment matches the owner of the current experiment."""
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={"ROOTDIR": "/dummy/rootdir", "AS_ENV_CURRENT_USER": "dummy"}
    )
    mocker.patch("pathlib.Path.owner", return_value="dummy" if is_owner else "otheruser")
    assert as_conf.is_current_real_user_owner == is_owner


@pytest.mark.parametrize("is_owner", [True, False])
def test_is_current_logged_user_owner(autosubmit_config, mocker, is_owner):
    """Test if the USER from the environment matches the owner of the current experiment."""
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={"ROOTDIR": "/dummy/rootdir"}
    )
    os.environ["USER"] = "dummy" if is_owner else "otheruser"

    mocker.patch("pathlib.Path.owner", return_value="dummy")
    assert as_conf.is_current_logged_user_owner == is_owner
