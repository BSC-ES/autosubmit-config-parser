import pytest


def test_check_jobs_conf_script_correct(autosubmit_config):
    as_conf = autosubmit_config(expid='a000', experiment_data={
        "JOBS":
        {
            "JOB2": {
                "SCRIPT": "hello",
                "RUNNING": "once"
            },
            "JOB1": {
                "SCRIPT": "hello",
                "DEPENDENCIES": {"JOB2": {}},
                "RUNNING": "once"
            },
        }
    }, ignore_file_path=True)

    result = as_conf.check_jobs_conf()
    assert result is True
    assert not as_conf.wrong_config
    assert not as_conf.warn_config


@pytest.mark.parametrize('experiment_data', [
    # FILE instead of SCRIPT
    ({
        "JOBS": {
            "JOB2": {
                "SCRIPT": "hello",
                "RUNNING": "once"
            },
            "JOB1": {
                "File": "file",
                "DEPENDENCIES": {"JOB2": {}},
                "RUNNING": "once"
            },
        }
    }),
    # No FILE and no SCRIPT
    ({
        "JOBS": {
            "JOB2": {
                "SCRIPT": "hello",
                "RUNNING": "once"
            },
            "JOB1": {
                "DEPENDENCIES": {"JOB2": {}},
                "RUNNING": "once"
            },
        }
    })])
def test_check_jobs_conf_script_error(autosubmit_config, experiment_data):
    as_conf = autosubmit_config(expid='a000', experiment_data=experiment_data, ignore_file_path=True)
    result = as_conf.check_jobs_conf()
    assert result is False
    assert len(as_conf.wrong_config['Jobs']) == 1
    assert 'Mandatory FILE parameter not found' in as_conf.wrong_config['Jobs'][0][1]
    assert not as_conf.warn_config['Jobs']
