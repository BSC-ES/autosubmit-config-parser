import pytest


@pytest.mark.parametrize("data, expected_data", [
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
            "AS_ENV_PLATFORMS_PATH": "test"
        }
    ),
], ids=["Check_variable_added_to_experiment_data"])
def test_as_env_variables(autosubmit_config, data, expected_data):
    import os
    os.environ["AS_ENV_PLATFORMS_PATH"] = "test"
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=data)
    as_conf.experiment_data = as_conf.load_as_env_variables(as_conf.experiment_data)
    assert as_conf.experiment_data == expected_data
