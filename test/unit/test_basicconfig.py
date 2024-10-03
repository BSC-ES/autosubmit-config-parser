import os

from autosubmitconfigparser.config.basicconfig import BasicConfig


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
