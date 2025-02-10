
import pytest

from autosubmitconfigparser.config.configcommon import AutosubmitConfig


def test_validate_wallclock():
    experiment_data = {
        "JOBS": [MockJob(3600, "PLATFORM_A")],
        "PLATFORMS": {"PLATFORM_A": {"MAX_WALLCLOCK": "00:30"}}
    }
    config = MockAutosubmitConfig(experiment_data, "PLATFORM_A")
    err_msg = config.validate_wallclock()
    assert err_msg == "Job <__main__.MockJob object at 0x...> has a wallclock time greater than the platform's wallclock time\n"

def test_validate_jobs_conf():
    experiment_data = {
        "JOBS": [MockJob(3600, "PLATFORM_A")],
        "PLATFORMS": {"PLATFORM_A": {"MAX_WALLCLOCK": "00:30"}}
    }
    config = MockAutosubmitConfig(experiment_data, "PLATFORM_A")
    err_msg = config.validate_jobs_conf()
    assert err_msg == "Job <__main__.MockJob object at 0x...> has a wallclock time greater than the platform's wallclock time\n"

def test_validate_config_runtime_error():
    experiment_data = {
        "JOBS": [MockJob(3600, "PLATFORM_A")],
        "PLATFORMS": {"PLATFORM_A": {"MAX_WALLCLOCK": "00:30"}}
    }
    config = MockAutosubmitConfig(experiment_data, "PLATFORM_A")
    with pytest.raises(AutosubmitCritical) as excinfo:
        config.validate_config(running_time=True)
    assert excinfo.value.code == 7014

def test_validate_config_non_runtime_error():
    experiment_data = {
        "JOBS": [MockJob(3600, "PLATFORM_A")],
        "PLATFORMS": {"PLATFORM_A": {"MAX_WALLCLOCK": "00:30"}}
    }
    config = MockAutosubmitConfig(experiment_data, "PLATFORM_A")
    config.validate_config(running_time=False)
    # Check the output manually or mock Log.critical to assert the message

def test_validate_config_no_error():
    experiment_data = {
        "JOBS": [MockJob(1800, "PLATFORM_A")],
        "PLATFORMS": {"PLATFORM_A": {"MAX_WALLCLOCK": "01:00"}}
    }
    config = MockAutosubmitConfig(experiment_data, "PLATFORM_A")
    config.validate_config(running_time=False)
