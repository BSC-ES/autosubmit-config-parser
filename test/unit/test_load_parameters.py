def test_load_parameters(autosubmit_config):

    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={'VAR': {"DEEP_VAR": ["%NOTFOUND%", "%TEST%", "%TEST2%"]}})
    as_conf.experiment_data.update({'d': '%d%', 'd_': '%d_%', 'Y': '%Y%', 'Y_': '%Y_%',
                                   'M': '%M%', 'M_': '%M_%', 'm': '%m%', 'm_': '%m_%'})
    parameters = as_conf.load_parameters()
    assert parameters['VAR.DEEP_VAR'] == ['%NOTFOUND%', '%TEST%', '%TEST2%']
