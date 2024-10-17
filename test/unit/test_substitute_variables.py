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

TEST_NESTED_DICT = {
    "TEST": "variableX",
    "TEST2": "variableY",
    "FOO": {
        "BAR": {
            "VAR": ["%NOTFOUND%", "%TEST%", "%TEST2%"],
            "VAR_STRING": "%NOTFOUND% %TEST% %TEST2%"
        }
    }
}

def test_substitute_dynamic_variables_yaml_files_short_format_for(autosubmit_config):
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


def test_substitute_keys_short_strings(autosubmit_config):

    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=ONE_DIM)
    result = as_conf._substitute_keys(
        ["%A%/bar/%B%"],
        ("FOO", "%A%/bar/%B%"),
        {"FOO": "%A%/bar/%B%", "A": "a", "B": "b"},
        "%[a-zA-Z0-9_.-]*%",
        1,
        "short",
        {"FOO": "%A%/bar/%B%"},
    )

    assert result == ({'FOO': 'a/bar/b'}, {'A': 'a', 'B': 'b', 'FOO': 'a/bar/b'})


def test_substitute_keys_short_strings_dict(autosubmit_config):

    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=ONE_DIM)
    result = as_conf._substitute_keys(
        ["%variables.Z%/bar/%VARIABLES.Y%"],
        ("FOO", "%variables.Z%/bar/%variables.Y%"),
        {"FOO": "%variables.Z%/bar/%variables.Y%", "VARIABLES": {"Z": "z", "Y": "y"}},
        "%[a-zA-Z0-9_.-]*%",
        1,
        "short",
        {"FOO": "%variables.Z%/bar/%variables.Y%"},
    )

    assert result[0] == {'FOO': 'z/bar/y'}


def test_substitute_dynamic_variables_yaml_files_short_format_nested(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=TEST_NESTED_DICT)
    as_conf.experiment_data = as_conf.deep_normalize(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.normalize_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.deep_read_loops(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.substitute_dynamic_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.parse_data_loops(as_conf.experiment_data)

    assert as_conf.experiment_data['FOO']['BAR']['VAR'] == ['%NOTFOUND%', 'variableX', 'variableY']
    assert as_conf.experiment_data['FOO']['BAR']['VAR_STRING'] == '%NOTFOUND% variableX variableY'