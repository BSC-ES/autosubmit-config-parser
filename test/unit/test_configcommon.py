from typing import Callable

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


@pytest.mark.parametrize(
    "parameters, dynamic_variables_, dict_keys_type, max_deep, pattern, start_long, result",
    [
        (
            {"FOO": "bar", "VARIABLE": "%foo%"},
            [("VARIABLE", "%foo%")],
            "short",
            25 + 1,
            "%[a-zA-Z0-9_.-]*%",
            1,
            {"FOO": "bar", "VARIABLE": "bar"},
        ),
        (
            {
                "JOBS": {"JOB": {"TEST": "%test.a%"}},
                "TEST": {"A": "%test.b%", "B": "b"},
            },
            [("JOBS.JOB.TEST", "%test.a%"), ("TEST.A", "%test.b%")],
            "short",
            25 + 2,
            "%[a-zA-Z0-9_.-]*%",
            1,
            {
                "JOBS": {"JOB": {"TEST": "b"}},
                "TEST": {"A": "b", "B": "b"},
            },
        ),
        (
            {"FOO": "bar/%PATH1%/baz/%PATH2%", "PATH1": "p1", "PATH2": "p2"},
            [("FOO", "bar/%PATH1%/baz/%PATH2%")],
            "short",
            25 + 1,
            "%[a-zA-Z0-9_.-]*%",
            1,
            {"FOO": "bar/p1/baz/p2", "PATH1": "p1", "PATH2": "p2"},
        )
    ],
)
def test_substitute_dynamic_variables_loop(
    parameters,
    dynamic_variables_,
    dict_keys_type,
    max_deep,
    pattern,
    start_long,
    result,
):
    new_parameters = AutosubmitConfig._substitute_dynamic_variables_loop(
        parameters, dynamic_variables_, dict_keys_type, max_deep, pattern, start_long
    )
    assert new_parameters == result
