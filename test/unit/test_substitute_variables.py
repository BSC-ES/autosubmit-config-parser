SHORT_CONF = {
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


def test_autosubmit_config_yaml(autosubmit_config):
    # Create an instance of AutosubmitConfig using the fixture
    expid = "test_experiment"
    experiment_data = {"key": "value"}
    config = autosubmit_config(expid, experiment_data)

    # Perform assertions to verify the configuration
    assert config.expid == expid
    assert config.experiment_data == experiment_data


def test_substitute_dynamic_variables_yaml_files(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=SHORT_CONF)
    as_conf.dynamic_variables = {'VAR': ['%HOLA%', '%TEST%', '%TEST2%']}
    as_conf.experiment_data = as_conf.substitute_dynamic_variables(as_conf.experiment_data)
    assert as_conf.experiment_data['VAR'] == ['%HOLA%', 'variableX', 'variableY']


def test_substitute_dynamic_variables_yaml_files_with_for(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data=SHORT_CONF)
    as_conf.experiment_data = as_conf.normalize_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.deep_read_loops(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.substitute_dynamic_variables(as_conf.experiment_data)
    as_conf.experiment_data = as_conf.parse_data_loops(as_conf.experiment_data, as_conf.data_loops)
    as_conf.experiment_data = as_conf.deep_normalize(as_conf.experiment_data)

    assert as_conf.experiment_data['VAR'] == ['%NOTFOUND%', 'variableX', 'variableY']
    assert as_conf.experiment_data['JOBS']['JOB_VARIABLEX'] == {'NAME': 'variableX', 'PATH': '/home/dbeltran/conf/stuff_to_read/variableX/test.yml'}
    assert as_conf.experiment_data['JOBS']['JOB_VARIABLEY'] == {'NAME': 'variableY', 'PATH': '/home/dbeltran/conf/stuff_to_read/variableY/test.yml'}

