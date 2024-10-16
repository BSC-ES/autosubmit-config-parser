import pytest
from pathlib import Path

from autosubmitconfigparser.config.basicconfig import BasicConfig
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
from conftest import prepare_yaml_files
from typing import Dict, Any
import shutil

as_conf_content: Dict[str, Any] = {
    "job": {
        "FOR": {
            "NAME": "%var%"
        },
        "path": "TOFILL"
    },
    "test": "variableX",
    "test2": "variableY",
    "test3": "variableZ",
    "var": [
        "%hola%",
        "%test%",
        "%test2%",
        "%test3%",
        "variableW"
    ],
    "DEFAULT": {
        "EXPID": "a000",
        "HPCARCH": "local",
        "CUSTOM_CONFIG": {
            "PRE": [
                "%job_variableX.path%",
                "%job_variableY.path%",
                "%job_variableZ.path%",
                "%job_variableW.path%"

            ]
        }
    },
    "Jobs": {
        "test": {
            "file": "test.sh"
        }
    }
}


def prepare_custom_config_tests(default_yaml_file: Dict[str, Any], project_yaml_files: Dict[str, Dict[str, str]], temp_folder: Path) -> Dict[str, Any]:
    """
    Prepare custom configuration tests by creating necessary YAML files.

    :param default_yaml_file: Default YAML file content.
    :type default_yaml_file: Dict[str, Any]
    :param project_yaml_files: Dictionary of project YAML file paths and their content.
    :type project_yaml_files: Dict[str, Dict[str, str]]
    :param temp_folder: Temporary folder .
    :type temp_folder: Path
    :return: Updated default YAML file content.
    :rtype: Dict[str, Any]
    """
    yaml_file_path = Path(f"{str(temp_folder)}/test_exp_data.yml")
    for path, content in project_yaml_files.items():
        test_file_path = Path(f"{str(temp_folder)}{path}")
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file_path, "w") as f:
            f.write(str(content))
    default_yaml_file["job"]["path"] = f"{str(temp_folder)}/%NAME%/test.yml"
    with yaml_file_path.open("w") as f:
        f.write(str(default_yaml_file))
    return default_yaml_file


@pytest.mark.parametrize("default_yaml_file, project_yaml_files, expected_data",
                         [(as_conf_content,
                           {"/variableX/test.yml": {"varX": "a_test"},
                            "/variableY/test.yml": {"varY": "a_test"},
                            "/variableZ/test.yml": {"varZ": "%test3%"},
                            "/variableW/test.yml": {"varW": "%varZ%"}},
                           {"VARX": "a_test",
                            "VARY": "a_test",
                            "VARZ": "variableZ",
                            "VARW": "variableZ",
                            "JOB_VARIABLEX_PATH": "variableX/test.yml",
                            "JOB_VARIABLEY_PATH": "variableY/test.yml"})])
def test_custom_config_for(temp_folder: Path, default_yaml_file: Dict[str, Any], project_yaml_files: Dict[str, Dict[str, str]], expected_data: Dict[str, str], mocker) -> None:
    """
    Test custom configuration and "FOR" for the given YAML files.

    :param temp_folder: Temporary folder path.
    :type temp_folder: Path
    :param default_yaml_file: Default YAML file content.
    :type default_yaml_file: Dict[str, Any]
    :param project_yaml_files: Dictionary of project YAML file paths and their content.
    :type project_yaml_files: Dict[str, Dict[str, str]]
    :param expected_data: Expected data for validation.
    :type expected_data: Dict[str, str]
    :param mocker: Mocker fixture for patching.
    :type mocker: Any
    """
    mocker.patch('pathlib.Path.exists', return_value=True)
    default_yaml_file = prepare_custom_config_tests(default_yaml_file, project_yaml_files, temp_folder)
    prepare_yaml_files(default_yaml_file, temp_folder)
    as_conf = AutosubmitConfig("test")
    as_conf.conf_folder_yaml = Path(temp_folder)
    as_conf.reload(True)
    for file_name in project_yaml_files.keys():
        assert temp_folder / file_name in as_conf.current_loaded_files.keys()
    assert as_conf.experiment_data["VARX"] == expected_data["VARX"]
    assert as_conf.experiment_data["VARY"] == expected_data["VARY"]
    assert as_conf.experiment_data["JOB_VARIABLEX"]["PATH"] == str(temp_folder / expected_data["JOB_VARIABLEX_PATH"])
    assert as_conf.experiment_data["JOB_VARIABLEY"]["PATH"] == str(temp_folder / expected_data["JOB_VARIABLEY_PATH"])
    assert as_conf.experiment_data["VARZ"] == expected_data["VARZ"]
    assert as_conf.experiment_data["VARW"] == expected_data["VARW"]


@pytest.fixture()
def prepare_basic_config(temp_folder):
    basic_conf = BasicConfig()
    BasicConfig.DB_DIR = (temp_folder / "DestinE_workflows")
    BasicConfig.DB_FILE = "as_times.db"
    BasicConfig.LOCAL_ROOT_DIR = (temp_folder / "DestinE_workflows")
    BasicConfig.LOCAL_TMP_DIR = "tmp"
    BasicConfig.LOCAL_ASLOG_DIR = "ASLOGS"
    BasicConfig.LOCAL_PROJ_DIR = "proj"
    BasicConfig.DEFAULT_PLATFORMS_CONF = ""
    BasicConfig.CUSTOM_PLATFORMS_PATH = ""
    BasicConfig.DEFAULT_JOBS_CONF = ""
    BasicConfig.SMTP_SERVER = ""
    BasicConfig.MAIL_FROM = ""
    BasicConfig.ALLOWED_HOSTS = ""
    BasicConfig.DENIED_HOSTS = ""
    BasicConfig.CONFIG_FILE_FOUND = False
    return basic_conf


def test_destine_workflows(temp_folder: Path, mocker, prepare_basic_config: Any) -> None:
    """
    Test the destine workflow (a1q2) hardcoded until CI/CD.
    """
    # Load yaml files
    # a bit Hardcoded pending CI/CD
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch.object(BasicConfig, 'read', return_value=True)
    current_script_location = Path(__file__).resolve().parent
    experiments_root = Path(f"{current_script_location}/DestinE_workflows")
    temp_folder_experiments_root = Path(f"{temp_folder}/DestinE_workflows")
    temp_folder_experiments_root.parent.mkdir(parents=True, exist_ok=True)
    # copy experiment files
    shutil.copytree(experiments_root, temp_folder_experiments_root)
    as_conf = AutosubmitConfig("a000", prepare_basic_config)
    as_conf.reload(True)
    # Check if the files are loaded
    assert len(as_conf.current_loaded_files) > 1
