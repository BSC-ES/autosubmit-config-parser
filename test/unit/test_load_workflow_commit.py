from pathlib import Path
import subprocess

import pytest
from log.log import Log


def test_add_autosubmit_dict(autosubmit_config, mocker):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={})
    as_conf._add_autosubmit_dict()
    assert "AUTOSUBMIT" in as_conf.experiment_data
    # test log.warning has been called
    mocker.patch.object(Log, "warning")
    as_conf._add_autosubmit_dict()
    Log.warning.assert_called_once()


@pytest.mark.parametrize("is_owner", [True, False])
def test_load_workflow_commit(autosubmit_config, tmpdir, mocker, is_owner):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={}
    )
    mocker.patch(
        "autosubmitconfigparser.config.configcommon.AutosubmitConfig.is_current_logged_user_owner",
        new_callable=mocker.PropertyMock,  # This is needed for property mocking
        return_value=is_owner
    )
    as_conf.reload()
    assert "AUTOSUBMIT" in as_conf.experiment_data
    assert "WORKFLOW_COMMIT" not in as_conf.experiment_data["AUTOSUBMIT"]

    as_conf.experiment_data = {
        "AUTOSUBMIT": {},
        "ROOTDIR": tmpdir.strpath,
        "PROJECT": {
            "PROJECT_DESTINATION": 'git_project'
        }
    }
    project_dir = f"{as_conf.experiment_data.get('ROOTDIR', '')}/proj"

    Path(project_dir).mkdir(parents=True, exist_ok=True)
    # Project root is third parent, ../../../.
    project_path = Path(__file__).parents[2]
    # git clone this project
    output = subprocess.check_output(f"git clone file://{project_path} git_project",
                                     cwd=project_dir, shell=True)
    assert output is not None
    as_conf.load_workflow_commit()
    if is_owner:
        assert "WORKFLOW_COMMIT" in as_conf.experiment_data["AUTOSUBMIT"]
        assert len(as_conf.experiment_data["AUTOSUBMIT"]["WORKFLOW_COMMIT"]) > 0
    else:
        assert "WORKFLOW_COMMIT" not in as_conf.experiment_data["AUTOSUBMIT"]
