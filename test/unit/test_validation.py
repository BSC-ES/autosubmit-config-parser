import pytest

from log.log import AutosubmitCritical


@pytest.mark.parametrize("data, must_fail", [
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "WALLCLOCK": "00:20",
                }
            }
        },
        False,
        id="Default wallclock no platform wallclock"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "WALLCLOCK": "48:00",
                }
            }
        },
        True,
        id="Higher wallclock than default"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "WALLCLOCK": "01:50",
                    "PLATFORM": "test"
                }
            },
            "PLATFORMS": {
                "test": {
                    "MAX_WALLCLOCK": "01:30"
                }
            }
        },
        True,
        id="Higher wallclock than platform"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "WALLCLOCK": "01:00",
                    "PLATFORM": "test"
                }
            },
            "PLATFORMS": {
                "test": {
                    "MAX_WALLCLOCK": "01:30"
                }
            }
        },
        False,
        id="Lower wallclock than platform"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "PLATFORM": "test"
                }
            },
            "PLATFORMS": {
                "test": {
                    "MAX_WALLCLOCK": "01:30"
                }
            }
        },
        False,
        id="Empty wallclock"
    ),
])
def test_validate_conf(autosubmit_config, data, must_fail):
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    if must_fail:
        with pytest.raises(AutosubmitCritical):
            as_conf.validate_config(True)
    else:
        assert as_conf.validate_config(True)
    assert as_conf.validate_config(False) is not must_fail
