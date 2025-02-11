
import pytest

from autosubmitconfigparser.config.configcommon import AutosubmitConfig

def test_validate_config(
    config = AutosubmitConfig()
    assert config.validate() == True
