import pytest
from pathlib import Path
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
from conftest import prepare_regression_test

as_conf_content = {
    "job": {
        "FOR": {
            "NAME": "%var%"
        },
        "path": "TOFILL"
    },
    "test": "variableX",
    "test2": "variableY",
    "var": [
        "%hola%",
        "%test%",
        "%test2%"
    ],
    "DEFAULT": {
        "EXPID": "a000",
        "HPCARCH": "local",
        "CUSTOM_CONFIG": {
            "PRE": [
                "%job_variableX.path%",
                "%job_variableY.path%"
            ]
        }
    },
    "Jobs": {
        "test": {
            "file": "test.sh"
        }
    }
}


def prepare_custom_config_tests(yaml_file_content, temp_folder):
    # create the folder
    yaml_file_path = Path(f"{temp_folder.strpath}/test_exp_data.yml")
    test_file_variablex_path = Path(f"{temp_folder.strpath}/variableX/test.yml")
    test_file_variablex_path.parent.mkdir(parents=True, exist_ok=True)
    test_file_variabley_path = Path(f"{temp_folder.strpath}/variableY/test.yml")
    test_file_variabley_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_file_variablex_path, "w") as f:
        f.write(str({"varX": "im_a_test"}))
    with open(test_file_variabley_path, "w") as f:
        f.write(str({"varY": "im_a_test"}))
    yaml_file_content["job"]["path"] = f"{temp_folder.strpath}/%NAME%/test.yml"
    # Add each platform to test
    with yaml_file_path.open("w") as f:
        f.write(str(yaml_file_content))
    return yaml_file_content


@pytest.mark.parametrize("yaml_file_content", [as_conf_content])
def test_custom_config_for(temp_folder, yaml_file_content, mocker):
    mocker.patch('pathlib.Path.exists', return_value=True)
    yaml_file_content = prepare_custom_config_tests(yaml_file_content, temp_folder)
    prepare_regression_test(yaml_file_content, temp_folder)
    as_conf = AutosubmitConfig("test")
    as_conf.conf_folder_yaml = Path(temp_folder)
    as_conf.reload(True)
    for file_name in ["variableX/test.yml", "variableY/test.yml", "test_exp_data.yml"]:
        assert f"{temp_folder}/{file_name}" in as_conf.current_loaded_files.keys()
    assert as_conf.experiment_data["VARX"] == "im_a_test"
    assert as_conf.experiment_data["VARY"] == "im_a_test"
    assert as_conf.experiment_data["JOB_VARIABLEX"]["PATH"] == f"{temp_folder.strpath}/variableX/test.yml"
    assert as_conf.experiment_data["JOB_VARIABLEY"]["PATH"] == f"{temp_folder.strpath}/variableY/test.yml"
