import pytest
from pathlib import Path
from ruamel.yaml import YAML


@pytest.mark.parametrize("data, owner", [
    ({
         "DEFAULT": {
             "HPCARCH": "local",
         },
     }, True),
    ({
         "DEFAULT": {
             "HPCARCH": "local",
         },
     }, False)
], ids=["local_true", "local_false"])
def test_save(autosubmit_config, tmpdir, mocker, data, owner):
    data['ROOTDIR'] = tmpdir.strpath
    if owner:
        data['AS_ENV_CURRENT_USER'] = Path(tmpdir).owner()
    else:
        data['AS_ENV_CURRENT_USER'] = 'whatever'
    as_conf = autosubmit_config(expid='t000', experiment_data=data)
    as_conf.save()
    if not owner:
        assert not Path(as_conf.metadata_folder).exists()
    else:
        assert Path(as_conf.metadata_folder).exists()
        assert (Path(as_conf.metadata_folder) / 'experiment_data.yml').exists()

        # check contents
        with open(Path(as_conf.metadata_folder) / 'experiment_data.yml', 'r') as f:
            yaml = YAML(typ="safe")
            assert data == yaml.load(f)

        # Test .bak generated.
        as_conf.save()
        assert (Path(as_conf.metadata_folder) / 'experiment_data.yml.bak').exists()
        # force fail save
        mocker.patch("builtins.open", side_effect=Exception("Forced exception"))
        mocker.patch("shutil.copyfile", return_value=True)
        as_conf.save()
        assert Path(as_conf.metadata_folder) / 'experiment_data.yml' not in Path(as_conf.metadata_folder).iterdir()
        assert as_conf.data_changed is True
        assert as_conf.last_experiment_data == {}
