import time
from pathlib import Path

import pytest


@pytest.mark.parametrize("force_load, current_loaded_files, expected_result", [
    (True, None, ['%NOTFOUND%', '%TEST%', '%TEST2%']),
    (True, None, ['%NOTFOUND%', '%TEST%', '%TEST2%']),
    (False, "older", ['%NOTFOUND%', '%TEST%', '%TEST2%']),
    (False, "newer", None),
    (True, "older", ['%NOTFOUND%', '%TEST%', '%TEST2%']),
    (True, "newer", ['%NOTFOUND%', '%TEST%', '%TEST2%']),
])
def test_reload_unittest(autosubmit_config, tmpdir, force_load, current_loaded_files, expected_result):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={})
    as_conf.conf_folder_yaml = tmpdir / 'conf'
    Path(as_conf.conf_folder_yaml).mkdir(parents=True, exist_ok=True)

    with open(as_conf.conf_folder_yaml / 'test.yml', 'w') as f:
        f.write('VAR: ["%NOTFOUND%", "%TEST%", "%TEST2%"]')
    if current_loaded_files:
        if current_loaded_files == "older":
            as_conf.current_loaded_files[as_conf.conf_folder_yaml / 'test.yml'] = time.time() - 1000
        else:
            as_conf.current_loaded_files[as_conf.conf_folder_yaml / 'test.yml'] = time.time() + 1000
    as_conf.reload(force_load=force_load)
    if expected_result:
        assert as_conf.experiment_data['VAR'] == expected_result
    else:
        assert as_conf.experiment_data.get('VAR', None) is None


@pytest.mark.parametrize("current_loaded_files, expected_result", [
    (None, True),
    ("older", True),
    ("newer", False),
])
def test_needs_reload(autosubmit_config, tmpdir, current_loaded_files, expected_result):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={})
    as_conf.conf_folder_yaml = tmpdir / 'conf'
    Path(as_conf.conf_folder_yaml).mkdir(parents=True, exist_ok=True)

    with open(as_conf.conf_folder_yaml / 'test.yml', 'w') as f:
        f.write('VAR: ["%NOTFOUND%", "%TEST%", "%TEST2%"]')
    if current_loaded_files:
        if current_loaded_files == "older":
            as_conf.current_loaded_files[as_conf.conf_folder_yaml / 'test.yml'] = time.time() - 1000
        else:
            as_conf.current_loaded_files[as_conf.conf_folder_yaml / 'test.yml'] = time.time() + 1000
    assert as_conf.needs_reload() == expected_result
