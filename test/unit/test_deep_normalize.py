def test_normalize_variables_for(autosubmit_config):
    data = {
        "JOBS": {
            "job1": {
                "FOR": {
                    "NAME": "var",
                    "lowercase": True
                }
            }
        },
        "var": ["test", "test2", "test3"]
    }
    expected_data = {
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
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    normalized_data = as_conf.deep_normalize(data)
    assert normalized_data == expected_data


def test_normalize_variables_for_with_lists(autosubmit_config):
    data = {
        "FOR": {
            "DEPENDENCIES": [
                {
                    "APP_ENERGY_ONSHORE": {
                        "SPLITS_FROM": {
                            "all": {
                                "SPLITS_TO": "previous"
                            }
                        }
                    },
                }
            ],
        },
        "foo": ["bar", "baz"],
        "1": ["one", "two"],
        "3": "three"
    }
    expected_data = {
        "FOR": {
            "DEPENDENCIES": [
                {
                    "APP_ENERGY_ONSHORE": {
                        "SPLITS_FROM": {
                            "ALL": {
                                "SPLITS_TO": "previous"
                            }
                        }
                    },
                }
            ],
        },
        "FOO": ["bar", "baz"],
        "1": ["one", "two"],
        "3": "three"
    }
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    normalized_data = as_conf.deep_normalize(data)
    assert normalized_data == expected_data
