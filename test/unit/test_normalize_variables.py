
import pytest

@pytest.mark.parametrize("data, expected_data, must_exists", [
    pytest.param(
        {
            "DEFAULT": {
                "HPCARCH": "local",
                "CUSTOM_CONFIG": {
                    "PRE": ["configpre", "configpre2"],
                    "POST": ["configpost", "configpost2"]
                }
            },
            "WRAPPERS": {
                "wrapper1": {
                    "JOBS_IN_WRAPPER": "job1 job2",
                    "TYPE": "VERTICAL"
                }
            },
            "JOBS": {
                "job1": {
                    "DEPENDENCIES": "job2 job3",
                    "CUSTOM_DIRECTIVES": ["directive1", "directive2"],
                    "FILE": "file1 file2"
                }
            }
        },
        {
            "DEFAULT": {
                "HPCARCH": "LOCAL",
                "CUSTOM_CONFIG": {
                    "PRE": "configpre,configpre2",
                    "POST": "configpost,configpost2"
                }
            },
            "WRAPPERS": {
                "WRAPPER1": {
                    "JOBS_IN_WRAPPER": "JOB1 JOB2",
                    "TYPE": "vertical"
                }
            },
            "JOBS": {
                "JOB1": {
                    "DEPENDENCIES": {"JOB2": {}, "JOB3": {}},
                    "CUSTOM_DIRECTIVES": "['directive1', 'directive2']",
                    "FILE": "file1",
                    "ADDITIONAL_FILES": ["file2"]
                }
            }
        },
        True,
        id="complete_conf_and_unified"
    ),
    pytest.param(
        {
            "WRAPPERS": {
                "wrapper1": "job1 job2"
            }
        },
        {
            "WRAPPERS": {
                "WRAPPER1": "job1 job2"
            }
        },
        False,
        id="wrappers_new_data"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "DEPENDENCIES": "job2 job3"
                }
            }
        },
        {
            "JOBS": {
                "JOB1": {
                    'FILE': '',
                    'ADDITIONAL_FILES': [],
                    "DEPENDENCIES": {"JOB2": {}, "JOB3": {}}
                }
            }
        },
        True,
        id="jobs_with_dependencies_conf_unified"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {}
            }
        },
        {
            'JOBS': {
                'JOB1': {
                    'FILE': '',
                    'ADDITIONAL_FILES': [],
                    'DEPENDENCIES': {},
                },
            }
        },
        True,
        id="jobs_unified_and_empty"
    ),
    pytest.param(
        {
            "JOBS": {
                "JOB": {
                    "PROCESSORS": 30
                }
            }
        },
        {
            'JOBS': {
                'JOB': {
                    'PROCESSORS': 30
                }
            }
        },
        False,
        id="jobs_new_data"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "CUSTOM_DIRECTIVES": "directive1 directive2"
                }
            }
        },
        {
            "JOBS": {
                "JOB1": {
                    "CUSTOM_DIRECTIVES": "directive1 directive2",
                    "FILE": "",
                    "ADDITIONAL_FILES": [],
                    "DEPENDENCIES": {}
                }
            }
        },
        True,
        id="custom_directives_unified"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "CUSTOM_DIRECTIVES": "directive1 directive2"
                }
            }
        },
        {
            "JOBS": {
                "JOB1": {
                    "CUSTOM_DIRECTIVES": "directive1 directive2",
                }
            }
        },
        False,
        id="custom_directives_new_data"
    ),
    pytest.param(
        {
            "JOBS": {
                "job1": {
                    "CUSTOM_DIRECTIVES": ["directive1", "directive2"]
                }
            }
        },
        {
            "JOBS": {
                "JOB1": {
                    "CUSTOM_DIRECTIVES": "['directive1', 'directive2']",
                }
            }
        },
        False,
        id="custom_directives_list_new_data"
    )
])
def test_normalize_variables(autosubmit_config, data, expected_data, must_exists):
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    normalized_data = as_conf.normalize_variables(data, must_exists=must_exists)
    assert normalized_data == expected_data
