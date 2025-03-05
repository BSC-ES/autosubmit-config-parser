def test_load_parameters(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={'VAR': {"deep_var": ["%NOTFOUND%", "%TEST%", "%TEST2%"]}})
    parameters = as_conf.load_parameters()
    assert parameters['VAR.DEEP_VAR'] == ['%NOTFOUND%', '%TEST%', '%TEST2%']
