import os
import pytest
from autosubmitconfigparser.config.basicconfig import BasicConfig
from conftest import autosubmit_config

def test_read_file_config(tmp_path):
    config_content = """
    [config]
    log_recovery_timeout = 45
    """
    config_file = tmp_path / "autosubmitrc"
    config_file.write_text(config_content)
    assert BasicConfig.LOG_RECOVERY_TIMEOUT == 60
    os.environ = {'AUTOSUBMIT_CONFIGURATION': str(config_file)}
    BasicConfig.read()
    assert BasicConfig.LOG_RECOVERY_TIMEOUT == 45

def test_invalid_expid_path():
    invalid_expids = ["", "12345", "123/", 1234] # empty, more than 4 char, contains folder separator, not string

    with pytest.raises(Exception):
        for expid in invalid_expids:
            BasicConfig.expid_dir(expid)

functions_expid = [BasicConfig.expid_dir,
                   BasicConfig.expid_tmp_dir,
                   BasicConfig.expid_log_dir,
                   BasicConfig.expid_aslog_dir]
root_dirs = [
    lambda root_path, exp_id: os.path.join(root_path, exp_id),
    lambda root_path, exp_id: os.path.join(root_path, exp_id, "tmp"),
    lambda root_path, exp_id: os.path.join(root_path, exp_id, "tmp", f"LOG_{exp_id}"),
    lambda root_path, exp_id: os.path.join(root_path, exp_id, "tmp", "ASLOGS")
]
@pytest.mark.parametrize("foo, dir_func", zip(functions_expid, root_dirs))
def test_expid_dir_structure(foo, dir_func, autosubmit_config):
    exp_id = 'a000'
    root_path = autosubmit_config(expid = exp_id).basic_config.LOCAL_ROOT_DIR
    expected_path = dir_func(root_path, exp_id)
    result = foo(exp_id)
    assert result == expected_path
