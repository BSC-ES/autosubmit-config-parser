import pytest
from pathlib import Path
from ruamel.yaml import YAML


@pytest.mark.parametrize("data", [
    pytest.param(
        {
            "DEFAULT": {
                "HPCARCH": "local",
            },
        },
        id="save",
    ),
])
def test_save(autosubmit_config, tmpdir, data, mocker):
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    as_conf.metadata_folder = tmpdir / 'metadata'
    Path(as_conf.metadata_folder).mkdir(parents=True, exist_ok=True)
    as_conf.save()
    assert Path(as_conf.metadata_folder) / 'experiment_data.yml' in Path(as_conf.metadata_folder).iterdir()
    assert Path(as_conf.metadata_folder) / 'experiment_data.yml.bak' not in Path(as_conf.metadata_folder).iterdir()
    # check contents
    with open(Path(as_conf.metadata_folder) / 'experiment_data.yml', 'r') as f:
        yaml = YAML(typ="safe")
        assert data == yaml.load(f)

    # Test .bak generated.
    as_conf.save()
    assert Path(as_conf.metadata_folder) / 'experiment_data.yml.bak' in Path(as_conf.metadata_folder).iterdir()

    # force fail save
    mocker.patch("builtins.open", side_effect=Exception("Forced exception"))
    mocker.patch("shutil.copyfile", return_value=True)
    as_conf.save()
    assert Path(as_conf.metadata_folder) / 'experiment_data.yml' not in Path(as_conf.metadata_folder).iterdir()
    assert as_conf.data_changed is True
    assert as_conf.last_experiment_data == {}
