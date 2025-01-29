from typing import Callable
from pathlib import Path
import pytest

from autosubmitconfigparser.config.configcommon import AutosubmitConfig

"""Basic tests for ``AutosubmitConfig``."""


def test_get_submodules_list_default_empty_list(autosubmit_config: Callable):
    """If nothing is provided, we get a list with an empty string."""
    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={})
    submodules_list = as_conf.get_submodules_list()
    assert submodules_list == ['']


def test_get_submodules_list_returns_false(autosubmit_config: Callable):
    """If the user provides a boolean ``False``, we return that value.

    This effectively disables submodules. See issue https://earth.bsc.es/gitlab/es/autosubmit/-/issues/1130.
    """
    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={
        'GIT': {
            'PROJECT_SUBMODULES': False
        }
    })
    submodules_list = as_conf.get_submodules_list()
    assert submodules_list is False


def test_get_submodules_true_not_valid_value(autosubmit_config: Callable):
    """If nothing is provided, we get a list with an empty string."""
    # TODO: move this to configuration validator when we have that...
    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={
        'GIT': {
            'PROJECT_SUBMODULES': True
        }
    })
    with pytest.raises(ValueError) as cm:
        as_conf.get_submodules_list()

    assert str(cm.value) == 'GIT.PROJECT_SUBMODULES must be false (bool) or a string'


def test_get_submodules(autosubmit_config: Callable):
    """A string separated by spaces is returned as a list."""
    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={
        'GIT': {
            'PROJECT_SUBMODULES': "sub_a sub_b sub_c sub_d"
        }
    })
    submodules_list = as_conf.get_submodules_list()
    assert isinstance(submodules_list, list)
    assert len(submodules_list) == 4
    assert "sub_b" in submodules_list


@pytest.mark.parametrize('owner', [True, False])
def test_is_current_real_user_owner(autosubmit_config: Callable, owner):
    as_conf = autosubmit_config(expid='a000', experiment_data={})
    as_conf.experiment_data = as_conf.load_common_parameters(as_conf.experiment_data)
    if owner:
        as_conf.experiment_data["AS_ENV_CURRENT_USER"] = Path(as_conf.experiment_data['ROOTDIR']).owner()
    else:
        as_conf.experiment_data["AS_ENV_CURRENT_USER"] = "dummy"
    assert as_conf.is_current_real_user_owner == owner


def test_clean_dynamic_variables_special_variables(autosubmit_config: Callable) -> None:
    """Test cleaning special variables.

    In Autosubmit configuration parser, variables that follow the pattern ``^%...%`` are
    special variables, e.g. ``^%EXPID%``.

    This test verifies that ``as_conf.special_variables`` is "cleaned", in the sense that
    when the ``clean_dynamic_variables`` is called with the right argument, the special
    variables dictionary contains only the special dynamic variables - nothing more.
    """
    in_the_end = True

    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={})
    dynamic_variables, pattern, start_long = as_conf._initialize_variables(in_the_end=in_the_end)

    as_conf.special_dynamic_variables = {
        'popeye_eats': 'spinach',
        'penguin_eats': 'fish',
        'thor_eats': '%^DYNAMIC_1%',
        'floki_eats': '%^DYNAMIC_2%',
        'jaspion_eats': '%PLACEHOLDER%'
    }

    as_conf.clean_dynamic_variables(pattern, in_the_end=in_the_end)

    # All other variables, that are not special, have been removed! So we should
    # have only thor_eats and floki_eats here.
    assert len(as_conf.special_dynamic_variables) == 2
    assert 'thor_eats' in as_conf.special_dynamic_variables
    assert 'floki_eats' in as_conf.special_dynamic_variables


def test_clean_dynamic_variables(autosubmit_config: Callable) -> None:
    """Test cleaning dynamic (non-special) variables.

    Read the text in the test above (``test_clean_dynamic_variables_special_variables``),
    as that can be helpful here.

    This tests that once called with the right arguments, ``clean_dynamic_variables`` will
    leave ``as_conf.dynamic_variables`` with only dynamic variables.
    """
    in_the_end = False

    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={})
    dynamic_variables, pattern, start_long = as_conf._initialize_variables(in_the_end=in_the_end)

    as_conf.dynamic_variables = {
        'popeye_eats': 'spinach',
        'penguin_eats': 'fish',
        'thor_eats': '%^DYNAMIC_1%',
        'floki_eats': '%^DYNAMIC_2%',
        'jaspion_eats': '%PLACEHOLDER%'
    }

    as_conf.clean_dynamic_variables(pattern, in_the_end=in_the_end)

    assert len(as_conf.dynamic_variables) == 1
    assert 'jaspion_eats' in as_conf.dynamic_variables


def test_yaml_deprecation_warning(autosubmit_config: Callable):

    as_conf: AutosubmitConfig = autosubmit_config(expid='a000', experiment_data={})
    as_conf_copy: AutosubmitConfig = autosubmit_config(expid='a001', experiment_data={})

    as_path = Path.home() / 'autosubmit'
    expid = str(as_conf.expid)
    expid_copy = str(as_conf_copy.expid)
    file_base = "conf/expdef_"+expid+".conf"
    file_copied = "conf/expdef_"+expid_copy+".conf_AS_v3_backup"
    expected = open(as_path/expid_copy/file_copied, 'r')
    with open(as_path/expid/file_base, 'r') as file:
        assert expected.read() == file.read()