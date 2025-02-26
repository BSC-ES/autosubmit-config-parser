import pytest
import os


@pytest.mark.parametrize("data, expected_data, sudo_user", [
    (
            {
                "DEFAULT": {
                    "CUSTOM_CONFIG": {
                        "POST": "%AS_ENV_PLATFORMS_PATH%"
                    }
                },
            },
            {
                "DEFAULT": {
                    "CUSTOM_CONFIG": {
                        "POST": "%AS_ENV_PLATFORMS_PATH%"
                    }
                },
                "AS_ENV_PLATFORMS_PATH": "test",
                "AS_ENV_CURRENT_USER": "dummy",
            },
            False,
    ),
    (
            {
                "DEFAULT": {
                    "CUSTOM_CONFIG": {
                        "POST": "%AS_ENV_PLATFORMS_PATH%"
                    }
                },
            },
            {
                "DEFAULT": {
                    "CUSTOM_CONFIG": {
                        "POST": "%AS_ENV_PLATFORMS_PATH%"
                    }
                },
                "AS_ENV_PLATFORMS_PATH": "test",
                "AS_ENV_CURRENT_USER": "testuser",
            },
            True,
    ),
], ids=["Check environment variables with SUDO", "Check environment variables without SUDO"])
def test_as_env_variables(autosubmit_config, data, expected_data, sudo_user):
    os.environ["AS_ENV_PLATFORMS_PATH"] = "test"
    if sudo_user:
        os.environ["SUDO_USER"] = "testuser"
    else:
        os.environ.pop("SUDO_USER", None)
        os.environ["USER"] = "dummy"
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=data)
    as_conf.load_as_env_variables(as_conf.experiment_data)
    assert as_conf.experiment_data == expected_data
