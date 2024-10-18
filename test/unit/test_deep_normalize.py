import pytest


@pytest.mark.parametrize("data, expected_data", [
    (
        {
            "JOBS": {
                "job1": {
                    "FOR": {
                        "NAME": "var",
                        "lowercase": True
                    }
                }
            },
            "var": ["test", "test2", "test3"]
        },
        {
            "JOBS": {
                "JOB1": {
                    "FOR": {
                        "NAME": "var",
                        "LOWERCASE": True
                    }
                }
            },
            "VAR": ["test", "test2", "test3"]
        }
    ),
    (
        {
            "FOR": {
                "DEPENDENCIES": [
                    {
                        "APP_ENERGY_ONSHORE": {
                            "SPLITS_FROM": {
                                "all": {
                                    "SPLITS_TO": "previous"
                                }
                            }
                        }
                    }
                ]
            },
            "foo": ["bar", "baz"],
            "1": ["one", "two"],
            "3": "three"
        },
        {
            "FOR": {
                "DEPENDENCIES": [
                    {
                        "APP_ENERGY_ONSHORE": {
                            "SPLITS_FROM": {
                                "ALL": {
                                    "SPLITS_TO": "previous"
                                }
                            }
                        }
                    }
                ]
            },
            "FOO": ["bar", "baz"],
            "1": ["one", "two"],
            "3": "three"
        }
    )
])
def test_normalize_variables(autosubmit_config, data, expected_data):
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    normalized_data = as_conf.deep_normalize(data)
    assert normalized_data == expected_data
