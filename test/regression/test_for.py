import pytest
from pathlib import Path
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
from conftest import prepare_yaml_files
from typing import Dict, Any

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
