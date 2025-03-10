def test_load_current_hpcarch_parameters(autosubmit_config):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={
            "DEFAULT": {
                "HPCARCH": "TEST"
            },
            "PLATFORMS": {
                "TEST": {
                    "BLABLA": "custom_conf"
                }
            },
        }
    )
    as_conf.load_current_hpcarch_parameters()
    assert as_conf.experiment_data['HPCARCH'] == "TEST"
    assert as_conf.experiment_data['HPCBLABLA'] == "custom_conf"
