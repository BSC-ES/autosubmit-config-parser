
def test_normalize_variables(autosubmit_config):
    data = {
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
    }
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    normalized_data = as_conf.normalize_variables(data)
    assert normalized_data["DEFAULT"]["HPCARCH"] == "LOCAL"
    assert normalized_data["DEFAULT"]["CUSTOM_CONFIG"]["PRE"] == "configpre,configpre2"
    assert normalized_data["DEFAULT"]["CUSTOM_CONFIG"]["POST"] == "configpost,configpost2"
    assert normalized_data["WRAPPERS"]["wrapper1"]["JOBS_IN_WRAPPER"] == "JOB1 JOB2"
    assert normalized_data["WRAPPERS"]["wrapper1"]["TYPE"] == "vertical"
    assert normalized_data["JOBS"]["job1"]["DEPENDENCIES"] == {"JOB2": {}, "JOB3": {}}
    assert normalized_data["JOBS"]["job1"]["CUSTOM_DIRECTIVES"] == "['directive1', 'directive2']"
    assert normalized_data["JOBS"]["job1"]["FILE"] == "file1"
    assert normalized_data["JOBS"]["job1"]["ADDITIONAL_FILES"] == ["file2"]


def test_normalize_variables_no_dict(autosubmit_config):
    # test when if type(wrappers[wrapper]) is not dict
    data = {
        "WRAPPERS": {
            "wrapper1": "job1 job2"
        }
    }
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    normalized_data = as_conf.normalize_variables(data)
    assert normalized_data["WRAPPERS"]["wrapper1"] == "job1 job2"
