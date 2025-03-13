import time
from pathlib import Path

import pytest

import subprocess

def test_load_workflow_commit(autosubmit_config, tmpdir):
    as_conf = autosubmit_config(
        expid='a000',
        experiment_data={})
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
    # git clone this project
    output = subprocess.check_output("git clone https://github.com/BSC-ES/autosubmit-config-parser git_project", cwd=project_dir, shell=True)
    assert output is not None
    as_conf.load_workflow_commit()
    assert "WORKFLOW_COMMIT" in as_conf.experiment_data["AUTOSUBMIT"]
    assert len(as_conf.experiment_data["AUTOSUBMIT"]["WORKFLOW_COMMIT"]) > 0
