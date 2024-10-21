import pytest
from pathlib import Path
import os
import pwd
from ruamel.yaml import YAML


@pytest.fixture
def temp_folder(tmpdir_factory):
    folder = tmpdir_factory.mktemp('tests')
    os.mkdir(folder.join('scratch'))
    file_stat = os.stat(f"{folder.strpath}")
    file_owner_id = file_stat.st_uid
    file_owner = pwd.getpwuid(file_owner_id).pw_name
    folder.owner = file_owner
    return folder


def prepare_yaml_files(yaml_file_content, temp_folder):
    # create the folder
    yaml_file_path = Path(f"{temp_folder.strpath}/test_exp_data.yml")
    # Add each platform to test
    if isinstance(yaml_file_content, dict):
        yaml = YAML()
        with yaml_file_path.open("w") as f:
            yaml.dump(yaml_file_content, f)
    else:
        with yaml_file_path.open("w") as f:
            f.write(str(yaml_file_content))
    return yaml_file_content
