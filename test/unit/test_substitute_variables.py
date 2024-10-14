FOR_CONF = {
    "TEST": "variableX",
    "TEST2": "variableY",
    "VAR": ["%NOTFOUND%", "%TEST%", "%TEST2%"],
    "jobs": {
        "job": {
            "FOR": {
                "NAME": "%var%"
            },
            "path": "/home/dbeltran/conf/stuff_to_read/%NAME%/test.yml"
        }
    }
}

ONE_DIM = {
    "TEST": "variableX",
    "TEST2": "variableY",
    "VAR": ["%NOTFOUND%", "%TEST%", "%TEST2%"],
    "JOBS": {
        "JOB": {
            "VARIABLEX": "%TEST%",
            "VARIABLEY": "%TEST2%"
        },
    },
}


def test_substitute_dynamic_variables_yaml_files_short_format(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=FOR_CONF)
    as_conf.experiment_data = as_conf.deep_normalize(as_conf.experiment_data)
    as_conf.dynamic_variables = {'VAR': ['%NOTFOUND%', '%TEST%', '%TEST2%']}
    as_conf.experiment_data = as_conf.substitute_dynamic_variables(as_conf.experiment_data)
    assert as_conf.experiment_data['VAR'] == ['%NOTFOUND%', 'variableX', 'variableY']


def test_substitute_dynamic_variables_yaml_files_with_for_short_format(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=FOR_CONF)
    as_conf.experiment_data = as_conf.deep_normalize(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.normalize_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.deep_read_loops(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.substitute_dynamic_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.parse_data_loops(as_conf.experiment_data)

    assert as_conf.experiment_data['VAR'] == ['%NOTFOUND%', 'variableX', 'variableY']
    assert as_conf.experiment_data['JOBS']['JOB_VARIABLEX'] == {'ADDITIONAL_FILES': [], 'DEPENDENCIES': {}, 'FILE': '', 'NAME': 'variableX', 'PATH': '/home/dbeltran/conf/stuff_to_read/variableX/test.yml'}
    assert as_conf.experiment_data['JOBS']['JOB_VARIABLEY'] == {'ADDITIONAL_FILES': [], 'DEPENDENCIES': {}, 'FILE': '', 'NAME': 'variableY', 'PATH': '/home/dbeltran/conf/stuff_to_read/variableY/test.yml'}
    assert as_conf.experiment_data['JOBS'].get('%NOTFOUND%', None) is None


def test_substitute_dynamic_variables_yaml_files_with_for_short_format_and_custom_config(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=FOR_CONF)
    as_conf.experiment_data = as_conf.deep_normalize(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.normalize_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.deep_read_loops(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.substitute_dynamic_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.parse_data_loops(as_conf.experiment_data)

    assert as_conf.experiment_data['VAR'] == ['%NOTFOUND%', 'variableX', 'variableY']
    assert as_conf.experiment_data['JOBS']['JOB_VARIABLEX'] == {'ADDITIONAL_FILES': [], 'DEPENDENCIES': {}, 'FILE': '', 'NAME': 'variableX', 'PATH': '/home/dbeltran/conf/stuff_to_read/variableX/test.yml'}
    assert as_conf.experiment_data['JOBS']['JOB_VARIABLEY'] == {'ADDITIONAL_FILES': [], 'DEPENDENCIES': {}, 'FILE': '', 'NAME': 'variableY', 'PATH': '/home/dbeltran/conf/stuff_to_read/variableY/test.yml'}
    assert as_conf.experiment_data['JOBS'].get('%NOTFOUND%', None) is None

def test_substitute_dynamic_variables_long_format(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=ONE_DIM)
    as_conf.experiment_data = as_conf.deep_normalize(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.normalize_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.deep_read_loops(as_conf.experiment_data)
    param = as_conf.substitute_dynamic_variables()
    assert param['JOBS.JOB.VARIABLEX'] == 'variableX'
    assert param['JOBS.JOB.VARIABLEY'] == 'variableY'
