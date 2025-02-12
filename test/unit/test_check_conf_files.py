# Improve this in the future.
def test_check_conf_files(autosubmit_config):
    config_dict = {
        "CONFIG": {
            "AUTOSUBMIT_VERSION": "4.1.12",
            "TOTALJOBS": 20,
            "MAXWAITINGJOBS": 20
        },
        "DEFAULT": {
            "EXPID": "",
            "HPCARCH": "",
            "CUSTOM_CONFIG": ""
        },
        "PROJECT": {
            "PROJECT_TYPE": "git",
            "PROJECT_DESTINATION": "git_project"
        },
        "GIT": {
            "PROJECT_ORIGIN": "",
            "PROJECT_BRANCH": "",
            "PROJECT_COMMIT": "",
            "PROJECT_SUBMODULES": "",
            "FETCH_SINGLE_BRANCH": True
        },
        "JOBS": {
            "JOB1": {
                "WALLCLOCK": "01:00",
                "PLATFORM": "test"
            }
        },
        "PLATFORMS": {
            "test": {
                "MAX_WALLCLOCK": "01:30"
            }
        },
    }

    as_conf = autosubmit_config(expid='t000', experiment_data=config_dict)
    as_conf.check_conf_files()
