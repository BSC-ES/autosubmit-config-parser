from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory
from typing import Dict, TYPE_CHECKING

import pytest

from autosubmitconfigparser.config.basicconfig import BasicConfig
from autosubmitconfigparser.config.configcommon import AutosubmitConfig

if TYPE_CHECKING:
    import pytest_mock


@pytest.fixture(scope='function')
def autosubmit_config(request: pytest.FixtureRequest, mocker: "pytest_mock.MockerFixture"):
    """Create an instance of ``AutosubmitConfig``."""

    original_root_dir = BasicConfig.LOCAL_ROOT_DIR
    tmp_dir = TemporaryDirectory()
    tmp_path = Path(tmp_dir.name)

    # Mock this as otherwise BasicConfig.read resets our other mocked values above.
    mocker.patch.object(BasicConfig, 'read', autospec=True)

    def _create_autosubmit_config(expid: str, experiment_data: Dict = None):
        root_dir = tmp_path
        BasicConfig.LOCAL_ROOT_DIR = str(root_dir)
        exp_path = root_dir / expid
        exp_tmp_dir = exp_path / BasicConfig.LOCAL_TMP_DIR
        aslogs_dir = exp_tmp_dir / BasicConfig.LOCAL_ASLOG_DIR
        conf_dir = exp_path / 'conf'
        aslogs_dir.mkdir(parents=True)
        conf_dir.mkdir()

        if not expid:
            raise ValueError('No value provided for expid')
        config = AutosubmitConfig(
            expid=expid,
            basic_config=BasicConfig
        )
        if experiment_data is not None:
            config.experiment_data = experiment_data

        return config

    def finalizer():
        BasicConfig.LOCAL_ROOT_DIR = original_root_dir
        rmtree(tmp_path)

    request.addfinalizer(finalizer)

    return _create_autosubmit_config
