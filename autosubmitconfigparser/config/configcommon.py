# Copyright 2015-2022 Earth Sciences Department, BSC-CNS
#
# This file is part of Autosubmit.
#
# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

import collections
import copy
import json
import locale
import numbers
import os
import re
import shutil
import subprocess
import traceback
from collections import defaultdict
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from typing import List, Union, Any, Tuple, Dict, Optional, cast

from bscearth.utils.date import parse_date
from configobj import ConfigObj
from pyparsing import nestedExpr
from ruamel.yaml import YAML

from log.log import Log, AutosubmitCritical, AutosubmitError
from .basicconfig import BasicConfig
from .yamlparser import YAMLParserFactory, YAMLParser


class AutosubmitConfig(object):
    """Class to handle experiment configuration coming from file or database."""

    def __init__(self, expid, basic_config=BasicConfig, parser_factory=YAMLParserFactory()):
        self.metadata_folder = None
        self.data_changed = False
        self.ignore_undefined_platforms = False
        self.ignore_file_path = False
        self.expid = expid
        self.basic_config = basic_config
        self.basic_config.read()
        if not Path(BasicConfig.LOCAL_ROOT_DIR, expid).exists():
            raise IOError(f"Experiment {expid} does not exist")
        self.parser_factory = parser_factory
        self.experiment_data = {}
        self.last_experiment_data = {}
        self.data_loops = set()

        self.current_loaded_files = dict()
        self.conf_folder_yaml = Path(BasicConfig.LOCAL_ROOT_DIR, expid, "conf")
        if not Path(BasicConfig.LOCAL_ROOT_DIR, expid, "conf").exists():
            raise IOError(f"Experiment {expid}/conf does not exist")
        self.wrong_config = defaultdict(list)
        self.warn_config = defaultdict(list)
        self.dynamic_variables = dict()
        # variables that will be substituted after all files is loaded
        self.special_dynamic_variables = dict()
        self.misc_files = []
        self.misc_data = list()

    @property
    def jobs_data(self):
        return self.experiment_data["JOBS"]

    @property
    def platforms_data(self):
        return self.experiment_data["PLATFORMS"]

    def get_wrapper_export(self, wrapper=None):
        """
         Returns modules variable from wrapper

         :return: string
         :rtype: str
         """
        if wrapper is None:
            wrapper = {}
        return wrapper.get('EXPORT', self.experiment_data.get("WRAPPERS", {}).get("EXPORT", ""))

    def get_project_submodules_depth(self):
        """
        Returns the max depth of submodule at the moment of cloning
        Default is -1 (no limit)
        :return: depth
        :rtype: list
        """
        git_data = self.experiment_data.get("GIT", {})
        unparsed_depth = git_data.get('PROJECT_SUBMODULES_DEPTH', "-1")
        if "[" in unparsed_depth and "]" in unparsed_depth:
            unparsed_depth = unparsed_depth.strip("[]")
            depth = [int(x) for x in unparsed_depth.split(",")]
        else:
            try:
                depth = int(unparsed_depth)
                depth = [depth]
            except ValueError:
                Log.warning("PROJECT_SUBMODULES_DEPTH is not an integer neither a int. Using default value -1")
                depth = []
        return depth

    def get_full_config_as_json(self):
        """
        Return config as json object
        """
        try:
            return json.dumps(self.experiment_data)
        except Exception:
            Log.warning(
                "Autosubmit was not able to retrieve and save the configuration into the historical database.")
            return ""

    def get_project_dir(self):
        """
        Returns experiment's project directory

        :return: experiment's project directory
        :rtype: str
        """

        dir_templates = os.path.join(self.basic_config.LOCAL_ROOT_DIR, self.expid, BasicConfig.LOCAL_PROJ_DIR,
                                     self.get_project_destination())
        return dir_templates

    def get_section(self, section, d_value="", must_exists=False):
        """
        Gets any section if it exists within the dictionary, else returns None or error if must exist.
        :param section: section to get
        :type section: list
        :param d_value: default value to return if section does not exist
        :type d_value: str
        :param must_exists: if true, error is raised if section does not exist
        :type must_exists: bool
        :return: section value
        :rtype: str

        """
        section = [s.upper() for s in section]
        # For text readability
        section_str = str(section[0])
        for sect in section[1:]:
            section_str += "." + str(sect)
        current_level = self.experiment_data.get(section[0], "")
        for param in section[1:]:
            if current_level:
                if type(current_level) is dict:
                    current_level = cast(dict, current_level).get(param, d_value)
                else:
                    if must_exists:
                        raise AutosubmitCritical(
                            "[INDEX ERROR], {0} must exists. Check that {1} is an section that exists.".format(
                                section_str,
                                str(current_level)),
                            7014)
        if current_level is None or (
                not isinstance(current_level, numbers.Number) and len(current_level) == 0) and must_exists:
            raise AutosubmitCritical(
                "{0} must exists. Check that subsection {1} exists.".format(section_str, str(current_level)), 7014)
        if current_level is None or (not isinstance(current_level, numbers.Number) and len(current_level) == 0):
            return d_value
        else:
            return current_level

    def get_wchunkinc(self, section):
        """
        Gets the chunk increase to wallclock  
        :param section: job type
        :type section: str
        :return: wallclock increase per chunk
        :rtype: str
        """
        return self.jobs_data.get(section, {}).get('WCHUNKINC', "")

    def show_messages(self):

        if len(list(self.warn_config.keys())) == 0 and len(list(self.wrong_config.keys())) == 0:
            Log.result("Configuration files OK\n")
        elif len(list(self.warn_config.keys())) > 0 and len(list(self.wrong_config.keys())) == 0:
            Log.result("Configuration files contain some issues ignored")
        if len(list(self.warn_config.keys())) > 0:
            message = "In Configuration files:\n"
            for section in self.warn_config:
                message += "Issues in [{0}] config file:".format(section)
                for parameter in self.warn_config[section]:
                    message += "\n[{0}] {1} ".format(parameter[0],
                                                     parameter[1])
                message += "\n"
            Log.printlog(message, 6013)

        if len(list(self.wrong_config.keys())) > 0:
            message = "On Configuration files:\n"
            for section in self.wrong_config:
                message += "Critical Issues on [{0}] config file:".format(
                    section)
                for parameter in self.wrong_config[section]:
                    message += "\n[{0}] {1}".format(parameter[0], parameter[1])
                message += "\n"
            raise AutosubmitCritical(message, 7014)
        else:
            return True

    def deep_update(self, unified_config, new_dict) -> None:
        """
        Update a nested dictionary or similar mapping.
        Modify ``source`` in place.
        """
        for key in new_dict.keys():
            if key not in unified_config:
                unified_config[key] = ""
        for key, val in new_dict.items():
            if isinstance(val, collections.abc.Mapping):
                self.deep_update(unified_config.get(key, {}), val)
            elif isinstance(val, list):
                if len(val) > 0 and isinstance(val[0], collections.abc.Mapping):
                    unified_config[key] = val
                else:
                    current_list = unified_config.get(key, [])
                    if current_list != val:
                        unified_config[key] = val
            else:
                unified_config[key] = new_dict[key]

    def normalize_variables(self, data: Dict[str, Any], must_exists: bool) -> None:
        """
        Apply some memory internal variables to normalize its format. (right now only dependencies)

        :param data: The input data dictionary to normalize.
        :param must_exists: If false, add the sections that are not present in the data dictionary.
        """
        deep_normalize(data)
        self._normalize_default_section(data)
        self._normalize_wrappers_section(data)
        self._normalize_jobs_section(data, must_exists)

    def _normalize_default_section(self, data_fixed: dict) -> None:
        default_section = data_fixed.get("DEFAULT", {})
        if "HPCARCH" in default_section:
            data_fixed["DEFAULT"]["HPCARCH"] = default_section["HPCARCH"].upper()
        if "CUSTOM_CONFIG" in default_section:
            with suppress(KeyError):
                data_fixed["DEFAULT"]["CUSTOM_CONFIG"] = _convert_list_to_string(default_section["CUSTOM_CONFIG"])

    @staticmethod
    def _normalize_wrappers_section(data_fixed: dict) -> None:
        wrappers = data_fixed.get("WRAPPERS", {})
        for wrapper, wrapper_data in wrappers.items():
            if isinstance(wrapper_data, dict):
                jobs_in_wrapper = wrapper_data.get("JOBS_IN_WRAPPER", "")
                if "[" in jobs_in_wrapper:  # if it is a list in string format (due to "%" in the string)
                    jobs_in_wrapper = jobs_in_wrapper.strip("[]").replace("'", "").replace(" ", "").replace(",", " ")
                data_fixed["WRAPPERS"][wrapper]["JOBS_IN_WRAPPER"] = jobs_in_wrapper.upper()
                data_fixed["WRAPPERS"][wrapper]["TYPE"] = str(wrapper_data.get("TYPE", "vertical")).lower()

    @staticmethod
    def _normalize_notify_on(data_fixed: dict, job_section) -> None:
        """
        Normalize the NOTIFY_ON section to a consistent format.
        """
        job_section = data_fixed["JOBS"][job_section]
        notify_on = job_section.get("NOTIFY_ON", "")
        if notify_on and isinstance(notify_on, str):
            separator: Optional[str] = ',' if ',' in notify_on else None
            notify_on = notify_on.split(separator)
            job_section["NOTIFY_ON"] = [status.strip(" ").upper() for status in notify_on]

    def _normalize_jobs_section(self, data_fixed: Dict[str, Any], must_exists: bool) -> None:
        for job, job_data in data_fixed.get("JOBS", {}).items():
            if "DEPENDENCIES" in job_data or must_exists:
                data_fixed["JOBS"][job]["DEPENDENCIES"] = self._normalize_dependencies(job_data.get("DEPENDENCIES", {}))

            if "CUSTOM_DIRECTIVES" in job_data:
                custom_directives = job_data.get("CUSTOM_DIRECTIVES", "")
                if isinstance(custom_directives, list):
                    custom_directives = str(custom_directives)
                if type(custom_directives) is str:
                    data_fixed["JOBS"][job]["CUSTOM_DIRECTIVES"] = str(custom_directives)
                else:
                    data_fixed["JOBS"][job]["CUSTOM_DIRECTIVES"] = custom_directives

            if "FILE" in job_data or must_exists:
                files = self._normalize_files(job_data.get("FILE", ""))
                data_fixed["JOBS"][job]["FILE"] = files[0].strip(" ")
                if len(files) > 1:
                    data_fixed["JOBS"][job]["ADDITIONAL_FILES"] = [file.strip(" ") for file in files[1:]]

            if "ADDITIONAL_FILES" not in data_fixed["JOBS"][job] and must_exists:
                data_fixed["JOBS"][job]["ADDITIONAL_FILES"] = []

            if "WALLCLOCK" in job_data:
                self._normalize_wallclock(data_fixed)

            self._normalize_notify_on(data_fixed, job)

    @staticmethod
    def _normalize_wallclock(data_fixed: {}) -> None:
        """
        Normalize the wallclock time format in the job configuration.

        This method iterates through the jobs in the provided data dictionary and checks the format of the "WALLCLOCK" value.
        If the wallclock time is in "HH:MM:SS" format, it truncates it to "HH:MM" and logs a warning.

        :param data_fixed: The dictionary containing job configurations.
        :type data_fixed: dict
        """
        for job in data_fixed.get("JOBS", {}):
            wallclock = data_fixed["JOBS"][job].get("WALLCLOCK", "")
            if wallclock and re.match(r'^\d{2}:\d{2}:\d{2}$', wallclock):
                # Truncate SS to "HH:MM"
                Log.warning(f"Wallclock {wallclock} is in HH:MM:SS format. Autosubmit doesn't suppport ( yet ) the seconds. Truncating to HH:MM")
                data_fixed["JOBS"][job]["WALLCLOCK"] = wallclock[:5]

    @staticmethod
    def _normalize_dependencies(dependencies: Union[str, dict]) -> dict:
        """
        Normalize the dependencies to a consistent format.

        This function takes a string or dictionary of dependencies and normalizes them to a dictionary format.
        If the input is a string, it splits the string by spaces and converts each dependency to uppercase.
        If the input is a dictionary, it converts each dependency key to uppercase and processes the status.

        Additionally, it checks if any final status is allowed, and if so, it sets the flag "ANY_FINAL_STATUS_IS_VALID".

        :param dependencies: The dependencies to normalize, either as a string or a dictionary.
        :type dependencies: Union[str, dict]
        :return: A dictionary with normalized dependencies.
        :rtype: dict
        """
        aux_dependencies = {}
        if isinstance(dependencies, str):
            for dependency in dependencies.upper().split(" "):
                aux_dependencies[dependency] = {}
        elif isinstance(dependencies, dict):
            for dependency, dependency_data in dependencies.items():
                aux_dependencies[dependency.upper()] = dependency_data
                if type(dependency_data) is dict and dependency_data.get("STATUS", None):
                    dependency_data["STATUS"] = dependency_data["STATUS"].upper()
                    if not dependency_data.get("ANY_FINAL_STATUS_IS_VALID", False):
                        if dependency_data["STATUS"][-1] == "?":
                            dependency_data["STATUS"] = dependency_data["STATUS"][:-1]
                            dependency_data["ANY_FINAL_STATUS_IS_VALID"] = True
                        elif dependency_data["STATUS"] not in ["READY", "DELAYED", "PREPARED", "SKIPPED", "FAILED",
                                                               "COMPLETED"]:  # May change in future issues.
                            dependency_data["ANY_FINAL_STATUS_IS_VALID"] = True
                        else:
                            dependency_data["ANY_FINAL_STATUS_IS_VALID"] = False

        return aux_dependencies

    @staticmethod
    def _normalize_files(files: Union[str, List[str]]) -> List[str]:
        if type(files) is not list:
            if ',' in files:
                files = files.split(",")
            elif ' ' in files:
                files = files.split(" ")
            else:
                files = [files]
        return files

    def dict_replace_value(self, d: dict, old: str, new: str, index: int, section_names: list) -> None:
        current_section = section_names.pop()
        if d.get(current_section, None):
            if isinstance(d[current_section], dict):
                self.dict_replace_value(d[current_section], old, new, index, section_names)
            elif isinstance(d[current_section], list):
                d[current_section][index] = d[current_section][index].replace(old[index], new)
            elif isinstance(d[current_section], str) and d[current_section] == old:
                d[current_section] = d[current_section].replace(old, new)

    def load_config_file(self, current_folder_data: Dict[str, Any], yaml_file: Path, load_misc=False) -> None:
        """
        Load a config file and parse it
        :param current_folder_data: current folder data
        :param yaml_file: yaml file to load.
        :param load_misc: Load misc files
        :return: unified config file
        """

        # check if path is file o folder
        # load yaml file with ruamel.yaml

        new_file = AutosubmitConfig.get_parser(self.parser_factory, yaml_file)
        self.normalize_variables(new_file.data, must_exists=False)
        if new_file.data.get("DEFAULT", {}).get("CUSTOM_CONFIG", None) is not None:
            new_file.data["DEFAULT"]["CUSTOM_CONFIG"] = _convert_list_to_string(
                new_file.data["DEFAULT"]["CUSTOM_CONFIG"])
        if new_file.data.get("AS_MISC", False) and not load_misc:
            self.misc_files.append(yaml_file)
            new_file.data = {}
        self.unify_conf(current_folder_data, new_file.data)

    def get_yaml_filenames_to_load(self, yaml_folder, ignore_minimal=False) -> List[str]:
        """
        Get all yaml files in a folder and return a list with the filenames
        :param yaml_folder: folder to search for yaml files
        :param ignore_minimal: ignore minimal files
        :return: list of filenames
        """
        filenames_to_load = []
        if ignore_minimal:
            for yaml_file in sorted([p.resolve() for p in Path(yaml_folder).glob("*") if
                                     p.suffix in {".yml", ".yaml"} and not p.name.endswith(
                                         ("minimal.yml", "minimal.yaml"))]):
                filenames_to_load.append(str(yaml_file))
        else:
            for yaml_file in sorted(
                    [p.resolve() for p in Path(yaml_folder).glob("*") if p.suffix in {".yml", ".yaml"}]):
                filenames_to_load.append(str(yaml_file))
        return filenames_to_load

    def parse_custom_conf_directive(self, custom_conf_directive):
        filenames_to_load = dict()
        filenames_to_load["PRE"] = []
        filenames_to_load["POST"] = []
        if custom_conf_directive is not None:
            # Check if directive is a dictionary
            if type(custom_conf_directive) is not dict:
                if type(custom_conf_directive) is str and custom_conf_directive != "":
                    if ',' in custom_conf_directive:
                        filenames_to_load["PRE"] = custom_conf_directive.split(',')
                    else:
                        filenames_to_load["PRE"] = custom_conf_directive.split(' ')
            else:
                if custom_conf_directive.get('PRE', "") != "":
                    if ',' in custom_conf_directive["PRE"]:
                        filenames_to_load["PRE"] = custom_conf_directive["PRE"].split(',')
                    else:
                        filenames_to_load["PRE"] = custom_conf_directive["PRE"].split(' ')
                if custom_conf_directive.get('POST', "") != "":
                    if ',' in custom_conf_directive["POST"]:
                        filenames_to_load["POST"] = custom_conf_directive["POST"].split(',')
                    else:
                        filenames_to_load["POST"] = custom_conf_directive["POST"].split(' ')
        aux_filenames_to_load = filenames_to_load.copy()
        for file_to_load in aux_filenames_to_load["PRE"]:
            if file_to_load in self.current_loaded_files:
                f_list = filenames_to_load["PRE"]
                f_list.remove(file_to_load)
        for file_to_load in aux_filenames_to_load["POST"]:
            if file_to_load in self.current_loaded_files:
                if file_to_load in self.current_loaded_files:
                    f_list = filenames_to_load["POST"]
                    f_list.remove(file_to_load)
        return filenames_to_load

    def unify_conf(self, current_data, new_data) -> None:
        """
        Unifies all configuration files into a single dictionary.
        :param current_data: dict with current configuration
        :param new_data: dict with new configuration
        :return: dict with new configuration taking priority over current configuration
        """
        # Basic data
        self.deep_update(current_data, new_data)
        self.deep_read_loops(current_data)
        self.substitute_dynamic_variables(current_data)
        self.parse_data_loops(current_data)

    def parse_data_loops(self, experiment_data) -> None:
        """
        This function, looks for the FOR keyword, to generates N amount of subsections of the same section.
        Looks for the "NAME" keyword, inside this FOR keyword to determine the name of the new sections
        Experiment_data is the dictionary that contains all the sections, a subsection could be located at the root but also in a nested section
        The experiment data is modified in place, with the FOR values expanded.
        :param experiment_data: dictionary with all the sections
        """
        exp_data_copy = experiment_data.copy()
        while self.data_loops:
            loops = self.data_loops.pop().split(",")
            pointer_to_last_data = exp_data_copy
            for section in loops[:-1]:
                pointer_to_last_data = pointer_to_last_data[section]
            section_basename = loops[-1]
            current_data = pointer_to_last_data[loops[-1]]
            # Remove the original section  keyword from original data
            pointer_to_last_data.pop(loops[-1])
            for_sections = current_data.pop("FOR")
            for for_section, for_values in for_sections.items():
                if not isinstance(for_values[0], dict):
                    for_values = str(for_values).strip("[]")
                    for_values = [v.strip("' ") for v in for_values.split(",")]
                for_sections[for_section] = for_values
            for name_index in range(len(for_sections["NAME"])):
                section_ending_name = section_basename + "_" + str(for_sections["NAME"][name_index].upper())
                if "%" in section_ending_name:
                    print("Warning: % in a FOR section name, index skipped")
                    continue
                current_data_aux = copy.deepcopy(current_data)
                current_data_aux["NAME"] = for_sections["NAME"][name_index]
                # add the dynamic_var
                self.deep_read_loops(current_data_aux)
                self.substitute_dynamic_variables(current_data_aux)
                pointer_to_last_data[section_ending_name] = current_data_aux
                for key, value in for_sections.items():
                    if key != "NAME":
                        pointer_to_last_data[section_ending_name][key] = value[name_index]
            # Delete pointer, because we are going to use it in the next loop for a different section,
            # so we need to delete the pointer to avoid overwriting.
            del pointer_to_last_data

    def check_dict_keys_type(self, parameters):
        """
        Check the type of keys in the parameters dictionary.
        :param parameters: Dictionary containing the parameters of the experiment.
        :return: Type of keys in the parameters dictionary, either "long" or "short".
        """
        # When a key_type is long, there are no dictionaries.
        dict_keys_type = "short"
        if parameters.get("DEFAULT", None) or parameters.get("EXPERIMENT", None) or parameters.get("JOBS",
                                                                                                   None) or parameters.get(
            "PLATFORMS", None):
            dict_keys_type = "short"
        else:
            for key, values in parameters.items():
                if "." in key:
                    dict_keys_type = "long"
                    break
                elif isinstance(values, dict):
                    dict_keys_type = "short"
                    break
        return dict_keys_type

    def clean_dynamic_variables(self, pattern, in_the_end=False):
        """Resets the local variable of dynamic (or special) variables.

        The ``pattern`` is used to search for dynamic or special variables (they vary
        from normal dynamic by a ``^`` symbol, ``%DYN%`` vs. ``%^SPE%``). Only variables
        whose value matches the given pattern are kept.

        The new dictionary of variable names and values is defined as the local object
        ``self.special_dynamic_variables`` if ``in_the_end`` is ``True``. Otherwise,
        ``self.dynamic_variables``.

        :param pattern: Regex pattern to identify dynamic variables.
        :param in_the_end: Boolean flag to determine which set of dynamic variables to clean.
        :return: None
        """
        dynamic_variables = {}
        if in_the_end:
            dynamic_variables_ = self.special_dynamic_variables
        else:
            dynamic_variables_ = self.dynamic_variables

        for key, dynamic_var in dynamic_variables_.items():
            # if not placeholder in dynamic_var[1], then it is not a dynamic variable
            if isinstance(dynamic_var, list):
                matching_values = list(
                    filter(
                        lambda value: re.search(pattern, value, flags=re.IGNORECASE),
                        dynamic_var
                    )
                )
                if matching_values:
                    dynamic_variables[key] = matching_values
            else:
                match = re.search(pattern, dynamic_var, flags=re.IGNORECASE)
                if match is not None:
                    dynamic_variables[key] = dynamic_var

        if in_the_end:
            self.special_dynamic_variables = dynamic_variables
        else:
            self.dynamic_variables = dynamic_variables

    def substitute_dynamic_variables(
            self,
            parameters: Dict[str, Any],
            max_deep: int = 25,
            dict_keys_type: str = None,
            in_the_end: bool = False,
    ) -> None:
        """
        Substitute dynamic variables in the experiment data.

        This function replaces placeholders in the experiment data with their corresponding values.
        It supports both long (%DEFAULT.EXPID%) and short (DEFAULT[EXPID]) key formats.

        :param dict parameters: Dictionary containing the parameters to be substituted. If None, it will use self.experiment_data.
        :param int max_deep: Maximum depth for recursive substitution. Default is 2+len(self.dynamic_variables).
        :param str dict_keys_type: Type of keys in the parameters dictionary, either "long" or "short".
        :param bool in_the_end: Flag to indicate if special dynamic variables should be used. Default is False.

        :returns: Current loaded experiment data  with substituted dynamic variables.
        :rtype: dict
        """
        max_deep += len(self.dynamic_variables)
        dynamic_variables, pattern, start_long = self._initialize_variables(in_the_end)

        if dict_keys_type is None:
            dict_keys_type = self.check_dict_keys_type(parameters)

        while len(dynamic_variables) > 0 and max_deep > 0:
            if self._process_dynamic_variables(dynamic_variables, parameters, pattern, start_long, dict_keys_type):
                break
            max_deep -= 1

        self.clean_dynamic_variables(pattern, in_the_end)

    def _initialize_variables(self, in_the_end: bool) -> Tuple[Dict[str, str], str, int]:
        """
        Initialize dynamic variables based on the `in_the_end` flag.

        :param bool in_the_end: Flag to indicate if special dynamic variables should be used.
        :returns: A tuple containing the dynamic variables, the regex pattern, and the start index.
        :rtype: tuple
        """
        if not in_the_end:
            return self.dynamic_variables, '%[a-zA-Z0-9_.-]*%', 1
        else:
            return self.special_dynamic_variables, '%\^[a-zA-Z0-9_.-]*%', 2

    def _process_dynamic_variables(
            self,
            dynamic_variables: Dict[str, Any],
            parameters: Dict[str, Any],
            pattern: str,
            start_long: int,
            dict_keys_type: str
    ) -> bool:
        """
        Process and substitute dynamic variables in the parameters.

        :param dict dynamic_variables: Dict of dynamic variables to be processed.
        :param str pattern: Regex pattern to identify dynamic variables.
        :param int start_long: Start index for long key format.
        :param str dict_keys_type: Type of keys in the parameters dictionary, either "long" or "short".
        :return: ``True`` if there were any changes to the dynamic variables.
        :rtype: bool
        """
        modified = False
        dynamic_variables_copy = dynamic_variables.copy()
        for dynamic_var in dynamic_variables_copy.items():
            keys = self._get_keys(dynamic_var, parameters, start_long, dict_keys_type)
            if keys:
                self._substitute_keys(keys, dynamic_var, parameters, pattern,
                                      start_long, dict_keys_type, dynamic_variables)
                modified = True
        del dynamic_variables_copy
        return modified


    @staticmethod
    def _get_keys(
            dynamic_var: Tuple[str, Any],
            parameters: Dict[str, Any],
            start_long: int,
            dict_keys_type: str
    ) -> List[Any]:
        """
        Retrieve keys for dynamic variable substitution.

        :param dynamic_var: The dynamic variable tuple containing the placeholder and its value.
        :type dynamic_var: Tuple[str, Any]
        :param parameters: Dictionary containing the parameters to be substituted.
        :type parameters: Dict[str, Any]
        :param start_long: Start index for long key format.
        :type start_long: int
        :param dict_keys_type: Type of keys in the parameters dictionary, either "long" or "short".
        :type dict_keys_type: str
        :returns: List of keys for substitution.
        :rtype: List[Any]
        """
        if dict_keys_type == "long":
            keys = parameters.get(str(dynamic_var[0][start_long:-1]), None)
            if not keys:
                keys = parameters.get(str(dynamic_var[0]), None)
        else:
            keys = dynamic_var[1]
        return keys if isinstance(keys, list) else [keys]

    def _substitute_keys(
            self,
            keys: List[str],
            dynamic_var: Tuple[str, Any],
            parameters: Dict[str, Any],
            pattern: str,
            start_long: int,
            dict_keys_type: str,
            processed_dynamic_variables: Dict[str, Any]
    ) -> None:
        """
        Substitute dynamic variables in the given keys.

        :param keys: List of keys to be processed.
        :type keys: List[str]
        :param dynamic_var: Tuple containing the dynamic variable and its value.
        :type dynamic_var: Tuple[str, Any]
        :param parameters: Dictionary containing the parameters to be substituted.
        :type parameters: Dict[str, Any]
        :param pattern: Regex pattern to identify dynamic variables.
        :type pattern: str
        :param start_long: Start index for long key format.
        :type start_long: int
        :param dict_keys_type: Type of keys in the parameters dictionary, either "long" or "short".
        :type dict_keys_type: str
        :param processed_dynamic_variables: Dictionary of already processed dynamic variables.
        :type processed_dynamic_variables: Dict[str, Any]
        """
        for i, key in enumerate(filter(None, keys)):
            matches = list(re.finditer(pattern, key, flags=re.IGNORECASE))[::-1]
            for match in matches:
                value = self._get_substituted_value(key, match, parameters, start_long, dict_keys_type)
                if value:
                    self._update_parameters(parameters, dynamic_var, value, i, dict_keys_type)
                    key = value
                    if len(keys) > 1:  # Mantain the list of keys if there are more than one
                        keys[i] = key
                        dynamic_var = (dynamic_var[0], keys)
                    else:
                        dynamic_var = (dynamic_var[0], value)
            processed_dynamic_variables[dynamic_var[0]] = dynamic_var[1]

    @staticmethod
    def _get_substituted_value(
            key: str,
            match: Any,
            parameters: Dict[str, Any],
            start_long: int,
            dict_keys_type: str
    ) -> Optional[str]:
        """
        Get the substituted value for a dynamic variable in the key.

        :param key: The key containing the dynamic variable.
        :type key: str
        :param match: The regex match object for the dynamic variable.
        :type match: Any
        :param parameters: Dictionary containing the parameters to be substituted.
        :type parameters: Dict[str, Any]
        :param start_long: Start index for long key format.
        :type start_long: int
        :param dict_keys_type: Type of keys in the parameters dictionary, either "long" or "short".
        :type dict_keys_type: str
        :return: The key with the substituted value.
        :rtype: str
        """
        rest_of_key_start = key[:match.start()]
        rest_of_key_end = key[match.end():]
        key_parts = key[match.start():match.end()]
        key_parts = key_parts[start_long:-1].split(".") if "." in key_parts and dict_keys_type != "long" else [
            key_parts[start_long:-1]]
        param = parameters
        for k in key_parts:
            param = param.get(k.upper(), None)
            if isinstance(param, int):
                param = str(param)
        if param is None:
            return None
        return str(rest_of_key_start) + str(param) + str(rest_of_key_end)

    def _update_parameters(
            self,
            parameters: Dict[str, Any],
            dynamic_var: Tuple[str, Any],
            value: str,
            index: int,
            dict_keys_type: str
    ) -> None:
        """
        Update the parameters dictionary with the substituted value.

        :param parameters: Dictionary containing the parameters to be updated.
        :type parameters: Dict[str, Any]
        :param dynamic_var: Tuple containing the dynamic variable and its value.
        :type dynamic_var: Tuple[str, Any]
        :param value: The substituted value to update in the parameters.
        :type value: str
        :param index: Index of the dynamic variable in the list of keys.
        :type index: int
        :param dict_keys_type: Type of keys in the parameters dictionary, either "long" or "short".
        :type dict_keys_type: str
        :return: Updated parameters dictionary.
        :rtype: Dict[str, Any]
        """
        if dict_keys_type == "long":
            parameters[str(dynamic_var[0])] = value
        else:
            section_names = dynamic_var[0].split(".")[::-1] if "." in dynamic_var[0] else [dynamic_var[0]]
            self.dict_replace_value(parameters, dynamic_var[1], value, index, section_names)

    def deep_read_loops(self, data, for_keys=None, long_key="") -> None:
        """
        Update a nested dictionary or similar mapping.
        Modify ``source`` in place.
        """
        if for_keys is None:
            for_keys = []

        for key, val in data.items():
            # Placeholders variables
            # Pattern to search a string starting with % and ending with % allowing the chars [],._ to exist in the middle
            dynamic_var_pattern = '%[a-zA-Z0-9_.-]*%'
            # Pattern to search a string starting with %^ and ending with %
            special_dynamic_var_pattern = '%\\^[a-zA-Z0-9_.-]*%'

            if not isinstance(val, collections.abc.Mapping) and re.search(dynamic_var_pattern, str(val),
                                                                          flags=re.IGNORECASE) is not None:
                self.dynamic_variables[long_key + key] = val
            elif not isinstance(val, collections.abc.Mapping) and re.search(special_dynamic_var_pattern, str(val),
                                                                            flags=re.IGNORECASE) is not None:
                self.special_dynamic_variables[long_key + key] = val
            if key == "FOR":
                # special case: check dynamic variables in the for loop
                if not val:
                    val = {}
                for for_section, for_values in val.items():
                    if len(for_values) == 0:
                        raise AutosubmitCritical("Empty for loop in section {0}".format(long_key + key), 7014)
                    if not isinstance(for_values[0], dict):
                        for_values = str(for_values).strip("[]")
                        for_values = for_values.replace("'", "")
                        if re.search(dynamic_var_pattern, for_values, flags=re.IGNORECASE) is not None:
                            self.dynamic_variables[long_key + key + "." + for_section] = for_values
                    val[for_section] = for_values
                # convert for_keys to string
                self.data_loops.add(",".join(for_keys))
            elif isinstance(val, collections.abc.Mapping):
                self.deep_read_loops(val, for_keys + [key], long_key=long_key + key + ".")

    def check_mandatory_parameters(self, no_log=False):
        self.check_expdef_conf(no_log)
        self.check_platforms_conf(no_log)
        self.check_jobs_conf(no_log)
        self.check_autosubmit_conf(no_log)

    def check_conf_files(self, running_time=False, force_load=True, no_log=False):
        """
        Checks configuration files (autosubmit, experiment jobs and platforms), looking for invalid values, missing
        required options. Print results in log
        :param running_time: True if the function is called during the execution of the program
        :type running_time: bool
        :param force_load: True if the function is called during the first load of the program
        :type force_load: bool
        :param no_log: True if the function is called during describe
        :type no_log: bool
        :return: True if everything is correct, False if it finds any error
        :rtype: bool
        """
        if not no_log:
            Log.info('\nChecking configuration files...')
        self.ignore_file_path = running_time
        self.ignore_undefined_platforms = running_time
        self.wrong_config = defaultdict(list)
        self.warn_config = defaultdict(list)
        try:
            self.reload(force_load)
        except IOError as e:
            raise AutosubmitError(
                "I/O Issues con config files", 6016, str(e))
        except (AutosubmitCritical, AutosubmitError):
            raise
        except BaseException as e:
            raise AutosubmitCritical("Unknown issue while checking the configuration files (check_conf_files)", 7040,
                                     str(e))
        # Annotates all errors found in the configuration files in dictionaries self.warn_config and self.wrong_config.
        self.check_mandatory_parameters(no_log=no_log)
        # End of checkers.
        self.validate_config(running_time)
        # This Try/Except is in charge of  print all the info gathered by all the checkers and stop the program if any critical error is found.
        try:
            if not no_log:
                result = self.show_messages()
                return result
        except AutosubmitCritical as e:
            # In case that there are critical errors in the configuration, Autosubmit won't continue.
            if running_time is True:
                raise
            else:
                if not no_log:
                    Log.warning(e.message)
        except Exception:
            raise

    def validate_wallclock(self) -> str:
        """
        Validate the wallclock time for each job against the platform's maximum wallclock time.

        :return: Error message if any job exceeds the platform's wallclock time, otherwise an empty string.
        :rtype: str
        """

        def _calculate_wallclock(wallclock: str) -> float:
            hours, minutes = map(int, wallclock.split(":"))
            return timedelta(hours=hours, minutes=minutes).total_seconds()

        config_job_wallclock = self.experiment_data.get("CONFIG", {}).get("JOB_WALLCLOCK", "24:00")
        default_wallclock = _calculate_wallclock(config_job_wallclock)
        err_msg = ""
        jobs = self.experiment_data.get("JOBS", {})
        platforms = self.experiment_data.get("PLATFORMS", {})
        wallclock_per_platform = {}

        for platform_name in platforms.keys():
            wallclock_per_platform[platform_name] = _calculate_wallclock(platforms[platform_name].get("MAX_WALLCLOCK",
                                                                                                      config_job_wallclock))

        for job_name, job_data in jobs.items():
            platform_wallclock = wallclock_per_platform.get(job_data.get("PLATFORM", ""), default_wallclock)
            total_seconds = _calculate_wallclock(job_data.get("WALLCLOCK", "00:01"))
            if total_seconds > platform_wallclock:
                err_msg += f"Job {job_name} has a wallclock {total_seconds}s time greater than the platform's {total_seconds}s wallclock time\n"
        return err_msg

    def validate_jobs_conf(self) -> str:
        """
        Validate the job configurations.

        :return: Error message if any validation fails, otherwise an empty string.
        :rtype: str
        """
        err_msg = self.validate_wallclock()
        return err_msg

    def validate_config(self, running_time: bool) -> bool:
        """
        Check if the configuration is valid.

        :param running_time: Indicates if the validation is being performed during runtime.
        :type running_time: bool
        :raises AutosubmitCritical: If any validation error occurs during runtime.
        """
        error_msg = self.validate_jobs_conf()
        if not error_msg:
            Log.result('Partial configuration validated correctly')
            return True

        if running_time:
            raise AutosubmitCritical(error_msg, 7014)

        Log.printlog(f"Invalid configuration. You must fix it before running your experiment:{error_msg}", 7014)
        return False

    def check_autosubmit_conf(self, no_log=False):
        """
        Checks experiment's autosubmit configuration file.
        :param no_log: True if the function is called during describe
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        parser_data = self.experiment_data
        if parser_data.get("CONFIG", "") == "":
            self.wrong_config["Autosubmit"] += [['CONFIG', "Mandatory AUTOSUBMIT section doesn't exists"]]
        else:
            if parser_data["CONFIG"].get('AUTOSUBMIT_VERSION', -1.1) == -1.1:
                self.wrong_config["Autosubmit"] += [['config',
                                                     "AUTOSUBMIT_VERSION parameter not found"]]

            if parser_data["CONFIG"].get('MAXWAITINGJOBS', -1) == -1:
                self.wrong_config["Autosubmit"] += [['config',
                                                     "MAXWAITINGJOBS parameter not found or non-integer"]]
            if parser_data["CONFIG"].get('TOTALJOBS', -1) == -1:
                self.wrong_config["Autosubmit"] += [['config',
                                                     "TOTALJOBS parameter not found or non-integer"]]
            if type(parser_data["CONFIG"].get('RETRIALS', 0)) is not int:
                parser_data["CONFIG"]['RETRIALS'] = int(parser_data["CONFIG"].get('RETRIALS', 0))

        if parser_data.get("STORAGE", None) is None:
            parser_data["STORAGE"] = {}
        if parser_data["STORAGE"].get('TYPE', "pkl") not in ['pkl', 'db']:
            self.wrong_config["Autosubmit"] += [['storage',
                                                 "TYPE parameter not found"]]
        wrappers_info = parser_data.get("WRAPPERS", {})
        if wrappers_info:
            self.check_wrapper_conf(wrappers_info)
        if parser_data.get("MAIL", "") != "":
            if str(parser_data["MAIL"].get("NOTIFICATIONS", "false")).lower() == "true":
                mails = parser_data["MAIL"].get("TO", "")
                if type(mails) is list:
                    pass
                elif "," in mails:
                    mails = mails.split(',')
                else:
                    mails = mails.split(' ')
                self.experiment_data["MAIL"]["TO"] = mails

                for mail in self.experiment_data["MAIL"]["TO"]:
                    if not _is_valid_mail_address(mail):
                        self.wrong_config["Autosubmit"] += [['mail',
                                                             "invalid e-mail"]]
        if "Autosubmit" not in self.wrong_config:
            if not no_log:
                Log.result('Autosubmit general sections OK')
            return True
        return False

    def check_platforms_conf(self, no_log=False):
        """
        Checks experiment's platforms configuration file.

        """
        parser_data = self.experiment_data.get("PLATFORMS", {})
        main_platform_found = False
        if self.hpcarch == "LOCAL":
            main_platform_found = True
        elif self.ignore_undefined_platforms:
            main_platform_found = True
        for section in parser_data:
            section_data = parser_data[section]
            if section == self.hpcarch:
                main_platform_found = True
                platform_type = section_data.get('TYPE', "")
                if not platform_type:
                    self.wrong_config["Platform"] += [[section, "Mandatory TYPE parameter not found"]]
                else:
                    platform_type = platform_type.lower()
                if platform_type != 'ps':
                    if not section_data.get('PROJECT', ""):
                        self.wrong_config["Platform"] += [[section, "Mandatory PROJECT parameter not found"]]
                    if not section_data.get('USER', ""):
                        self.wrong_config["Platform"] += [[section,
                                                           "Mandatory USER parameter not found"]]
            if not section_data.get('HOST', ""):
                self.wrong_config["Platform"] += [[section, "Mandatory HOST parameter not found"]]
            if not section_data.get('SCRATCH_DIR', ""):
                self.wrong_config["Platform"] += [[section,
                                                   "Mandatory SCRATCH_DIR parameter not found"]]
        if not main_platform_found:
            self.wrong_config["Expdef"] += [
                ["Default", "Main platform is not defined! check if [HPCARCH = {0}] has any typo".format(self.hpcarch)]]
        main_platform_issues = False
        for platform, error in self.wrong_config.get("Platform", []):
            if platform.upper() == self.hpcarch.upper():
                main_platform_issues = True

        # Delete the platform section if there are no issues with the main platform and thus autosubmit can procced. TODO: Improve this when we have a better config validator.
        # This is a workaround to avoid autosubmit to stop when there is an uncomplete platform section( per example, an user file platform that only has an USER keyword set) that doesn't affect to the experiment itself.
        # During running, if there are issues in any experiment active platform autosubmit will stop and the user will be notified.
        if not main_platform_issues:
            if self.wrong_config.get('Platform', None) is not None:
                Log.warning(
                    f"Some defined platforms have the following issues: {self.wrong_config.get('Platform', [])}")
            self.wrong_config.pop("Platform", None)
            if not no_log:
                Log.result('Platforms sections: OK')
            return True
        return False

    def check_jobs_conf(self, no_log=False):
        """
        Checks experiment's jobs configuration file.
        :param no_log: if True, it doesn't print any log message
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        parser = self.experiment_data
        for section in parser.get("JOBS", {}):
            section_data = parser["JOBS"][section]
            section_file_path = section_data.get('FILE', "")
            if not section_file_path and not section_data.get('SCRIPT', ""):
                self.wrong_config["Jobs"] += [[section,
                                               "Mandatory FILE parameter not found"]]
            else:
                with suppress(KeyError):
                    if self.ignore_file_path:
                        if "SCRIPT" not in section_data:
                            if not os.path.exists(os.path.join(self.get_project_dir(), section_file_path)):
                                check_value = str(section_data.get('CHECK', True)).lower()
                                if check_value != "false":
                                    if check_value not in "on_submission":
                                        self.wrong_config["Jobs"] += [
                                            [section,
                                             "FILE {0} doesn't exist and check parameter is not set on_submission value".format(
                                                 section_file_path)]]
                                else:
                                    self.wrong_config["Jobs"] += [[section, "FILE {0} doesn't exist".format(
                                        os.path.join(self.get_project_dir(), section_file_path))]]

            dependencies = section_data.get('DEPENDENCIES', '')
            if dependencies != "":
                if type(dependencies) is dict:
                    for dependency, values in dependencies.items():
                        if '-' in dependency:
                            dependency = dependency.split('-')[0]
                        elif '+' in dependency:
                            dependency = dependency.split('+')[0]
                        elif '*' in dependency:
                            dependency = dependency.split('*')[0]
                        elif '?' in dependency:
                            dependency = dependency.split('?')[0]
                        if '[' in dependency:
                            dependency = dependency[:dependency.find('[')]
                        if dependency.upper() not in parser["JOBS"].keys():
                            self.warn_config["Jobs"].append(
                                [section,
                                 "Dependency parameter is invalid, job {0} is not configured".format(dependency)])
            rerun_dependencies = section_data.get('RERUN_DEPENDENCIES', "").upper()
            if rerun_dependencies:
                for dependency in rerun_dependencies.split(' '):
                    if '-' in dependency:
                        dependency = dependency.split('-')[0]
                    if '[' in dependency:
                        dependency = dependency[:dependency.find('[')]
                    if dependency not in parser["JOBS"].keys():
                        self.warn_config["Jobs"] += [
                            [section,
                             "RERUN_DEPENDENCIES parameter is invalid, job {0} is not configured".format(dependency)]]
            running_type = section_data.get('RUNNING', "once").lower()
            if running_type not in ['once', 'date', 'member', 'chunk']:
                self.wrong_config["Jobs"] += [[section,
                                               "Mandatory RUNNING parameter is invalid"]]
        if "Jobs" not in self.wrong_config:
            if not no_log:
                Log.result('Jobs sections OK')
            return True
        return False

    def check_expdef_conf(self, no_log=False):
        """
        Checks experiment's experiment configuration file.
        :param no_log: if True, it doesn't print any log message
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        parser = self.experiment_data
        self.hpcarch = ""
        if parser.get('DEFAULT', "") == "":
            self.wrong_config["Expdef"] += [['DEFAULT', "Mandatory DEFAULT section doesn't exists"]]
        else:
            if not parser.get('DEFAULT').get('EXPID', ""):
                self.wrong_config["Expdef"] += [['DEFAULT', "Mandatory DEFAULT.EXPID parameter is invalid"]]

            self.hpcarch = parser['DEFAULT'].get('HPCARCH', "").upper()
            if not self.hpcarch:
                self.wrong_config["Expdef"] += [['DEFAULT', "Mandatory DEFAULT.HPCARCH parameter is invalid"]]
        if parser.get('EXPERIMENT', "") == "":
            self.wrong_config["Expdef"] += [['EXPERIMENT', "Mandatory EXPERIMENT section doesn't exists"]]
        else:
            if not parser['EXPERIMENT'].get('DATELIST', ""):
                self.wrong_config["Expdef"] += [['DEFAULT', "Mandatory EXPERIMENT.DATELIST parameter is invalid"]]
            if not parser['EXPERIMENT'].get('MEMBERS', ""):
                self.wrong_config["Expdef"] += [['DEFAULT', "Mandatory EXPERIMENT.MEMBERS parameter is invalid"]]
            if parser['EXPERIMENT'].get('CHUNKSIZEUNIT', "").lower() not in ['year', 'month', 'day', 'hour']:
                self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.CHUNKSIZEUNIT choice is invalid"]]
            if type(parser['EXPERIMENT'].get('CHUNKSIZE', "-1")) not in [int]:
                if parser['EXPERIMENT']['CHUNKSIZE'] == "-1":
                    self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.CHUNKSIZE is not defined"]]
                parser['EXPERIMENT']['CHUNKSIZE'] = int(parser['EXPERIMENT']['CHUNKSIZE'])
            if type(parser['EXPERIMENT'].get('NUMCHUNKS', "-1")) not in [int]:
                if parser['EXPERIMENT']['NUMCHUNKS'] == "-1":
                    self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.NUMCHUNKS is not defined"]]
                parser['EXPERIMENT']['NUMCHUNKS'] = int(parser['EXPERIMENT']['NUMCHUNKS'])
            if parser['EXPERIMENT'].get('CALENDAR', "").lower() not in ['standard', 'noleap']:
                self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.CALENDAR choice is invalid"]]
        if parser.get('PROJECT', "") == "":
            self.wrong_config["Expdef"] += [['PROJECT', "Mandatory PROJECT section doesn't exists"]]
            project_type = ""
        else:
            project_type = parser['PROJECT'].get('PROJECT_TYPE', "")
        if project_type.lower() not in ['none', 'git', 'svn', 'local']:
            self.wrong_config["PROJECT"] += [['PROJECT_TYPE', "Mandatory PROJECT_TYPE choice is invalid"]]
        else:
            if project_type == 'git':
                if parser.get('GIT', "") == "":
                    self.wrong_config["Expdef"] += [['GIT', "Mandatory GIT section doesn't exists"]]
                else:
                    if not parser['GIT'].get('PROJECT_ORIGIN', ""):
                        self.wrong_config["Expdef"] += [['git',
                                                         "PROJECT_ORIGIN parameter is invalid"]]
                    if not parser['GIT'].get('PROJECT_BRANCH', ""):
                        self.wrong_config["Expdef"] += [['git',
                                                         "PROJECT_BRANCH parameter is invalid"]]

            elif project_type == 'svn':
                if parser.get('SVN', "") == "":
                    self.wrong_config["Expdef"] += [['SVN', "Mandatory SVN section doesn't exists"]]
                else:
                    if not parser['SVN'].get('PROJECT_URL', ""):
                        self.wrong_config["Expdef"] += [['svn',
                                                         "PROJECT_URL parameter is invalid"]]
                    if not parser['SVN'].get('PROJECT_REVISION', ""):
                        self.wrong_config["Expdef"] += [['svn',
                                                         "PROJECT_REVISION parameter is invalid"]]
            elif project_type == 'local':
                if parser.get('LOCAL', "") == "":
                    self.wrong_config["Expdef"] += [['LOCAL', "Mandatory LOCAL section doesn't exists"]]
                else:

                    if not parser['LOCAL'].get('PROJECT_PATH', ""):
                        self.wrong_config["Expdef"] += [['local',
                                                         "PROJECT_PATH parameter is invalid"]]
            elif project_type == 'none':  # debug propouses
                self.ignore_file_path = False
        if "Expdef" not in self.wrong_config:
            if not no_log:
                Log.result("Expdef config file is correct")
            return True
        return False

    def check_wrapper_conf(self, wrappers=None, no_log=False) -> bool:
        """
        Checks wrapper config file

        :param wrappers:
        :param no_log:
        :return:
        """
        if wrappers is None:
            wrappers = {}
        for wrapper_name, wrapper_values in wrappers.items():
            # continue if it is a global option (non-dicT)
            if type(wrapper_values) is not dict:
                continue

            jobs_in_wrapper = wrapper_values.get('JOBS_IN_WRAPPER', "")
            if type(jobs_in_wrapper) is not list:
                if "[" in jobs_in_wrapper:  # if it is a list in string format ( due "%" in the string )
                    jobs_in_wrapper = jobs_in_wrapper.strip("[]")
                    jobs_in_wrapper = jobs_in_wrapper.replace("'", "")
                    jobs_in_wrapper = jobs_in_wrapper.replace(" ", "")
                    jobs_in_wrapper = jobs_in_wrapper.split(",")
                elif "&" in jobs_in_wrapper:
                    jobs_in_wrapper = jobs_in_wrapper.split("&")
                else:
                    jobs_in_wrapper = jobs_in_wrapper.split(" ")
            for section in jobs_in_wrapper:
                try:
                    platform_name = self.jobs_data[section.upper()].get('PLATFORM', "").upper()
                except Exception:
                    self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                       "JOBS_IN_WRAPPER contains non-defined jobs.  parameter is invalid"]]
                    continue
                if platform_name == "":
                    platform_name = self.get_platform().upper()
                if platform_name == "LOCAL":
                    continue
                if not self.is_valid_jobs_in_wrapper(wrapper_values):
                    self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                       "JOBS_IN_WRAPPER contains non-defined jobs.  parameter is invalid"]]
                if 'horizontal' in self.get_wrapper_type(wrapper_values):
                    if not self.experiment_data["PLATFORMS"][platform_name].get('PROCESSORS_PER_NODE', None):
                        self.wrong_config["WRAPPERS"] += [
                            [wrapper_name, "PROCESSORS_PER_NODE no exist in the horizontal-wrapper platform"]]
                    if not self.experiment_data["PLATFORMS"][platform_name].get('MAX_PROCESSORS', ""):
                        self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                           "MAX_PROCESSORS no exist in the horizontal-wrapper platform"]]
                if 'vertical' in self.get_wrapper_type(wrapper_values):
                    if not self.experiment_data.get("PLATFORMS", {}).get(platform_name, {}).get('MAX_WALLCLOCK', ""):
                        self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                           "MAX_WALLCLOCK no exist in the vertical-wrapper platform"]]
            if "WRAPPERS" not in self.wrong_config:
                if not no_log:
                    Log.result('wrappers OK')
                return True
        return False

    def load_common_parameters(self, parameters) -> None:
        """
        Loads common parameters not specific to a job neither a platform
        :param parameters:
        :return:
        """
        parameters['ROOTDIR'] = os.path.join(BasicConfig.LOCAL_ROOT_DIR, self.expid)
        project_destination = parameters.get('PROJECT', {}).get('PROJECT_DESTINATION', "project_files")
        parameters['PROJDIR'] = os.path.join(parameters['ROOTDIR'], "proj", project_destination)

    def load_custom_config(self, current_data, filenames_to_load) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Loads custom config files
        :param current_data: dict with current data
        :param filenames_to_load: list of filenames to load
        """
        current_data_pre = {}
        current_data_post = {}
        # at this point, filenames_to_load should be a list of filenames of an specific section PRE or POST.
        for filename in filenames_to_load:
            filename = filename.strip(", ")  # Remove commas and spaces if any
            if filename.startswith("~"):
                filename = os.path.expanduser(filename)
            self.unify_conf(self.experiment_data, current_data)
            current_data_aux = {
                "AS_TEMP": {
                    "FILENAME_TO_LOAD": filename
                }
            }
            self.dynamic_variables["AS_TEMP.FILENAME_TO_LOAD"] = filename
            self.substitute_dynamic_variables(current_data_aux)
            filename = Path(current_data_aux["AS_TEMP"]["FILENAME_TO_LOAD"])
            del current_data_aux
            if not filename.exists() and "%" not in str(filename):
                Log.info(f"Yaml file {filename} not found")
            if filename.exists() and str(filename) not in self.current_loaded_files:
                # Check if this file is already loaded. If not, load it
                self.current_loaded_files[str(filename)] = filename.stat().st_mtime
                # Load a folder or a file
                if not filename.is_file():
                    # Load a folder by calling recursively to this function as a list of files
                    filenames_to_load = self.get_yaml_filenames_to_load(filename, ignore_minimal=False)
                    current_data_pre, current_data_post = self.load_custom_config(current_data, filenames_to_load)
                    self.unify_conf(self.experiment_data, current_data_pre)
                    self.unify_conf(self.experiment_data, current_data_post)
                else:
                    self.load_config_file(self.experiment_data, filename)

                    # Load next level if any
                    custom_conf_directive = current_data.get('DEFAULT', {}).get('CUSTOM_CONFIG', None)
                    filenames_to_load_level = self.parse_custom_conf_directive(custom_conf_directive)
                    if custom_conf_directive:
                        del current_data["DEFAULT"]["CUSTOM_CONFIG"]

                    pre_files = [
                        to_load for to_load in filenames_to_load_level["PRE"]
                        if to_load not in self.current_loaded_files
                    ]
                    post_files = [
                        to_load for to_load in filenames_to_load_level["POST"]
                        if to_load not in self.current_loaded_files
                    ]

                    if pre_files:
                        self.load_custom_config_section(current_data, pre_files)
                    else:
                        current_data_pre = current_data

                    self.unify_conf(self.experiment_data, current_data_pre)

                    if post_files:
                        self.load_custom_config_section(current_data, post_files)
                    else:
                        current_data_post = current_data

                    self.unify_conf(self.experiment_data, current_data_post)

                    filenames_to_load_level["PRE"] = pre_files
                    filenames_to_load_level["POST"] = post_files

        return current_data_pre, current_data_post

    def load_custom_config_section(self, current_data: Dict[str, Any], filenames_to_load: List[str]) -> None:
        """
        Loads a section (PRE or POST ), simple str are also PRE data of the custom config files
        :param current_data: data until now
        :param filenames_to_load: files to load in this section
        """
        # This is a recursive call
        current_data_pre, current_data_post = self.load_custom_config(current_data, filenames_to_load)
        # Unifies all pre- and post-data of the current pre- or post-data. Think of it as a tree with
        # two branches that needs to be unified at each level
        self.unify_conf(current_data_pre, current_data)

    @property
    def is_current_real_user_owner(self) -> bool:
        """
        Check if the real user(AS_ENV_CURRENT_USER) is the owner of the experiment folder
        :return: bool
        """
        return Path(self.experiment_data["ROOTDIR"]).owner() == self.experiment_data["AS_ENV_CURRENT_USER"]

    @staticmethod
    def load_as_env_variables(parameters: Dict[str, Any]) -> None:
        """
        Loads all environment variables that starts with AS_ENV into the parameters dictionary and obtains the current user running it.
        :param parameters: current loaded parameters.
        """
        for key, value in os.environ.items():
            if key.startswith("AS_ENV"):
                parameters[key] = value
        parameters["AS_ENV_CURRENT_USER"] = os.environ.get("SUDO_USER", os.environ.get("USER", None))

    def reload(self, force_load=False, only_experiment_data=False) -> None:
        """
        Reloads the configuration files
        :param force_load: If True, reloads all the files, if False, reloads only the modified files
        :param only_experiment_data: If ``True`` skips pre- and post-files.
        """
        # Check if the files have been modified or if they need a reload
        files_to_reload = []
        # Reload only the files that have been modified
        # Only reload the data if there are changes or there is no data loaded yet
        reload_while_running = self.experiment_data.get("CONFIG", {}).get("RELOAD_WHILE_RUNNING", True)
        should_reload = force_load or (self.data_changed and reload_while_running)

        if should_reload:
            files_to_reload = self.current_loaded_files.keys()

        if files_to_reload or self.current_loaded_files:
            # Load all the files starting from the $expid/conf folder
            # reset loaded files
            self.current_loaded_files = {}
            for filename in self.get_yaml_filenames_to_load(self.conf_folder_yaml):
                self.load_config_file(self.experiment_data, Path(filename))
            self.load_as_env_variables(self.experiment_data)
            self.load_common_parameters(self.experiment_data)
            # Same data without the minimal config ( if any ), need to be here due to current_loaded_files variable
            non_minimal_conf = {}
            for filename in self.get_yaml_filenames_to_load(self.conf_folder_yaml, ignore_minimal=True):
                self.current_loaded_files[str(filename)] = Path(filename).stat().st_mtime
                self.load_config_file(non_minimal_conf, Path(filename))
            self.load_common_parameters(non_minimal_conf)  # FIXME: why?

            # Start loading the custom config files
            # Gets the files to load
            custom_config_files = self.experiment_data.get("DEFAULT", {}).get("CUSTOM_CONFIG", None)
            filenames_to_load = self.parse_custom_conf_directive(custom_config_files)
            if not only_experiment_data:
                self.load_custom_config_section(self.experiment_data, filenames_to_load["PRE"])
                self.load_custom_config_section(self.experiment_data, filenames_to_load["POST"])

            if "AS_TEMP" in self.experiment_data:
                del self.experiment_data["AS_TEMP"]

            # IF expid and hpcarch are not defined, use the ones from the minimal.yml file
            self.normalize_variables(self.experiment_data, must_exists=True)
            self.deep_read_loops(self.experiment_data)
            self.substitute_dynamic_variables(self.experiment_data)
            self.substitute_dynamic_variables(self.experiment_data, in_the_end=True)

        self.load_last_run()
        
        self.misc_data = {}
        self.misc_files = list(set(self.misc_files))
        for filename in self.misc_files:
            self.load_config_file(self.misc_data, Path(filename), load_misc=True)

    def load_last_run(self):
        try:
            self.metadata_folder = Path(self.conf_folder_yaml) / "metadata"
            if not self.metadata_folder.exists():
                os.makedirs(self.metadata_folder)
                os.chmod(self.metadata_folder, 0o775)
            if not os.access(self.metadata_folder, os.W_OK):
                print(f"WARNING: Can't save the experiment data into {self.metadata_folder}, no write permissions")
            else:
                # Load data from last run
                if (Path(self.metadata_folder) / "experiment_data.yml").exists():
                    with open(Path(self.metadata_folder) / "experiment_data.yml", 'r') as stream:
                        yaml_loader = YAML(typ='safe')
                        self.last_experiment_data = yaml_loader.load(stream)
                    self.data_changed = self.quick_deep_diff(self.experiment_data, self.last_experiment_data)
                else:
                    self.last_experiment_data = {}
                    self.data_changed = True
        except IOError as e:
            self.last_experiment_data = {}
            self.data_changed = True
            Log.warning(f"Can't load the last experiment data: {e}")

    def save(self):
        """
        Saves the experiment data into the experiment_folder/conf/metadata folder as a yaml file
        :return: True if the data has changed, False otherwise
        """
        # changed = False
        # check if the folder exists and we have write permissions, if folder doesn't exist create it with rwx/rwx/r-x permissions
        # metadata folder is inside the experiment folder / conf folder / metadata folder
        # If this function is called before load_last_run, we need to load the last run
        if self.last_experiment_data and len(self.last_experiment_data) == 0:
            self.load_last_run()
        if (Path(self.metadata_folder) / "experiment_data.yml").exists():
            shutil.copy(Path(self.metadata_folder) / "experiment_data.yml",
                        Path(self.metadata_folder) / "experiment_data.yml.bak")
        try:
            with open(Path(self.metadata_folder) / "experiment_data.yml", 'w') as stream:
                # Not using typ="safe" to preserve the readability of the file
                YAML().dump(self.experiment_data, stream)
        except Exception:
            if (Path(self.metadata_folder) / "experiment_data.yml").exists():
                os.remove(Path(self.metadata_folder) / "experiment_data.yml")
            self.data_changed = True
            self.last_experiment_data = {}
        return self.data_changed

    def detailed_deep_diff(self, current_data, last_run_data, level=0):
        """
        Returns a dictionary with for each key, the difference between the current configuration and the last_run_data
        :param current_data: dictionary with the current data
        :param last_run_data: dictionary with the last_run_data data
        :return: differences: dictionary
        """
        differences = {}
        if current_data is None:
            current_data = {}
        if last_run_data is None:
            last_run_data = {}
        # Check if current_data key is present on last_run_data
        # If present, obtain the new value
        for key, val in current_data.items():
            if isinstance(val, collections.abc.Mapping):
                if key not in last_run_data.keys():
                    differences[key] = val
                else:
                    if type(last_run_data[key]) is not dict:
                        differences[key] = val
                    elif len(last_run_data[key]) == 0 and len(last_run_data[key]) == len(current_data[key]):
                        continue
                    else:
                        diff = self.detailed_deep_diff(last_run_data[key], val, level)
                        if diff:
                            differences[key] = diff
            else:
                if key not in last_run_data.keys() or last_run_data[key] != val:
                    differences[key] = val
        # Now check the keys that are in last_run_data but not in current_data
        # We don't want the old value
        for key, val in last_run_data.items():
            if isinstance(val, collections.abc.Mapping):
                if key not in current_data.keys():
                    differences[key] = val
                else:
                    if type(current_data[key]) is dict and len(current_data[key]) == 0:
                        diff = self.detailed_deep_diff(current_data[key], val, level)
                        if diff:
                            differences[key] = diff
            else:
                if key not in current_data.keys():
                    differences[key] = val
        if not differences and level > 0:
            return None
        return differences

    def quick_deep_diff(self, current_data, last_run_data, changed=False):
        """
        Returns if there is any difference between the current configuration and the stored one
        :param last_run_data: dictionary with the stored data
        :return: changed: boolean, True if the configuration has changed
        """
        if not current_data:
            return changed
        if changed:
            return True
        try:
            for key, val in current_data.items():
                if isinstance(val, collections.abc.Mapping):
                    if not last_run_data or key not in last_run_data.keys():
                        changed = True
                        break
                    else:
                        changed = self.quick_deep_diff(last_run_data[key], val, changed)
                else:
                    if key not in last_run_data.keys() or str(last_run_data[key]).lower() != str(val).lower():
                        changed = True
                        break
        except Exception:
            changed = True
        return changed

    def deep_get_long_key(self, section_data, long_key):
        parameters_dict = dict()
        for key, val in section_data.items():
            if isinstance(val, collections.abc.Mapping):
                parameters_dict.update(self.deep_get_long_key(section_data.get(key, {}), long_key + "." + key))
            else:
                parameters_dict[long_key + "." + key] = val
        return parameters_dict

    def deep_parameters_export(self, data: Dict[str, Any]) -> None:
        """Modifies the given dictionary in-place, making keys all uppercase.

        Export all variables of this experiment.
        Resultant format will be Section.{subsections1...subsectionN} = Value.
        In other words, it plain the dictionary into one level
        """
        data_copy = data.copy()
        for key, value in data_copy.items():
            if value is None:
                value = {}
            if isinstance(value, collections.abc.Mapping):
                data.update(self.deep_get_long_key(value, key))
            else:
                data[key] = value
        del data_copy
        _normalize_parameters_keys(data)

    def load_parameters(self):
        """
        Load all experiment data
        :return: a dictionary containing tuples [parameter_name, parameter_value]
        :rtype: dict
        """
        self.deep_parameters_export(self.experiment_data)
        return self.experiment_data

    def get_project_type(self):
        """
        Returns project type from experiment config file

        :return: project type
        :rtype: str
        """
        return self.get_section(["project", "project_type"], must_exists=False).lower()

    def get_parse_two_step_start(self):
        """
        Returns two-step start jobs

        :return: jobs_list
        :rtype: str
        """

        return self.get_section(['EXPERIMENT', 'TWO_STEP_START'], "")

    def get_rerun_jobs(self):
        """
        Returns rerun jobs

        :return: jobs_list
        :rtype: str
        """
        try:
            return self.get_section(['RERUN', 'RERUN_JOBLIST'], "")
        except Exception:
            return ""

    def get_file_project_conf(self):
        """
        Returns path to project config file from experiment config file

        :return: path to project config file
        :rtype: str
        """
        return self.get_section(['PROJECT_FILES', 'FILE_PROJECT_CONF'])

    def get_file_jobs_conf(self):
        """
        Returns path to project config file from experiment config file

        :return: path to project config file
        :rtype: str
        """
        return self.get_section(['PROJECT_FILES', 'FILE_JOBS_CONF'], "")

    def get_git_project_origin(self):
        """
        Returns git origin from experiment config file

        :return: git origin
        :rtype: str
        """
        return self.get_section(['GIT', 'PROJECT_ORIGIN'], "")

    def get_git_project_branch(self):
        """
        Returns git branch  from experiment's config file

        :return: git branch
        :rtype: str
        """
        return self.get_section(['GIT', 'PROJECT_BRANCH'], 'master')

    def get_git_project_commit(self):
        """
        Returns git commit from experiment's config file

        :return: git commit
        :rtype: str
        """
        return self.get_section(['GIT', 'PROJECT_COMMIT'], "")

    def get_git_remote_project_root(self):
        """
        Returns remote machine ROOT PATH

        :return: git commit
        :rtype: str
        """
        return self.get_section(['GIT', 'REMOTE_CLONE_ROOT'], "")

    def get_submodules_list(self) -> Union[List[str], bool]:
        """
        Returns submodules list from experiment's config file.
        Default is --recursive.
        Can be disabled by setting the configuration key to ``False``.
        :return: submodules to load
        :rtype: Union[List[str], bool]
        """
        project_submodules: Union[str, bool] = self.get_section(['GIT', 'PROJECT_SUBMODULES'], "")
        if project_submodules is False:
            return project_submodules
        if not isinstance(project_submodules, str):
            raise ValueError('GIT.PROJECT_SUBMODULES must be false (bool) or a string')
        return project_submodules.split(" ")

    def get_fetch_single_branch(self):
        """
        Returns fetch single branch from experiment's config file
        Default is -single-branch
        :return: fetch_single_branch(Y/N)
        :rtype: str
        """
        return str(self.get_section(['GIT', 'FETCH_SINGLE_BRANCH'], "true")).lower()

    def get_project_destination(self):
        """
        Returns git commit from experiment's config file

        :return: git commit
        :rtype: str
        """
        try:
            value = self.experiment_data.get("PROJECT", {}).get("PROJECT_DESTINATION", "project_files")
            if not value:
                if self.experiment_data.get("PROJECT", {}).get("PROJECT_TYPE", "").lower() == "local":
                    value = os.path.split(self.experiment_data.get("LOCAL", {}).get("PROJECT_PATH", ""))[-1]
                elif self.experiment_data.get("PROJECT", {}).get("PROJECT_TYPE", "").lower() == "svn":
                    value = self.experiment_data.get("SVN", {}).get("PROJECT_URL", "").split('/')[-1]
                elif self.experiment_data.get("PROJECT", {}).get("PROJECT_TYPE", "").lower() == "git":
                    value = self.experiment_data.get("GIT", {}).get("PROJECT_ORIGIN", "").split('/')[-1]
                    if "." in value:
                        value = value.split('.')[-2]

            return value

        except Exception as exp:
            Log.debug(str(exp))
            Log.debug(traceback.format_exc())
        return "project_files"

    def set_git_project_commit(self, as_conf):
        """
        Function to register in the configuration the commit SHA of the git project version.
        :param as_conf: Configuration class for exteriment
        :type as_conf: AutosubmitConfig
        """
        full_project_path = as_conf.get_project_dir()
        try:
            output = subprocess.check_output("cd {0}; git rev-parse --abbrev-ref HEAD".format(full_project_path),
                                             shell=True)
        except subprocess.CalledProcessError as e:
            raise AutosubmitCritical(
                "Failed to retrieve project branch...", 7014, str(e))

        project_branch = output
        Log.debug("Project branch is: " + project_branch)
        try:
            output = subprocess.check_output(
                "cd {0}; git rev-parse HEAD".format(full_project_path), shell=True)
        except subprocess.CalledProcessError as e:
            raise AutosubmitCritical(
                "Failed to retrieve project commit SHA...", 7014, str(e))
        project_sha = output
        Log.debug("Project commit SHA is: " + project_sha)

        # register changes
        content = open(self._exp_parser_file).read()
        if re.search('PROJECT_BRANCH:.*', content):
            content = content.replace(re.search('PROJECT_BRANCH:.*', content).group(0),
                                      "PROJECT_BRANCH: " + project_branch)
        if re.search('PROJECT_COMMIT:.*', content):
            content = content.replace(re.search('PROJECT_COMMIT:.*', content).group(0),
                                      "PROJECT_COMMIT: " + project_sha)
        open(self._exp_parser_file, 'wb').write(content)
        Log.debug(
            "Project commit SHA succesfully registered to the configuration file.")
        return True

    def get_svn_project_url(self):
        """
        Gets subversion project url

        :return: subversion project url
        :rtype: str
        """
        return self.get_section(['SVN', 'PROJECT_URL'])

    def get_svn_project_revision(self):
        """
        Get revision for subversion project

        :return: revision for subversion project
        :rtype: str
        """
        return self.get_section(['SVN', 'PROJECT_REVISION'])

    def get_local_project_path(self):
        """
        Gets path to origin for local project

        :return: path to local project
        :rtype: str
        """
        return self.get_section(['LOCAL', 'PROJECT_PATH'])

    def get_date_list(self):
        """
        Returns startdates list from experiment's config file

        :return: experiment's startdates
        :rtype: list
        """
        date_list = list()
        date_value = str(self.get_section(['EXPERIMENT', 'DATELIST'], "20220401"))
        # Allows to use the old format for define a list.
        if type(date_value) is not list:
            if not date_value.startswith("["):
                string = '[{0}]'.format(date_value)
            else:
                string = date_value
            split_string = nestedExpr('[', ']').parseString(string).asList()
            string_date = None
            for split in split_string[0]:
                if type(split) is list:
                    for split_in in split:
                        if split_in.find("-") != -1:
                            numbers = split_in.split("-")
                            for count in range(int(numbers[0]), int(numbers[1]) + 1):
                                date_list.append(parse_date(string_date + str(count).zfill(len(numbers[0]))))
                        else:
                            date_list.append(parse_date(string_date + split_in))
                    string_date = None
                else:
                    if string_date is not None and len(str(string_date)) > 0:
                        date_list.append(parse_date(string_date))
                    string_date = split
            if string_date is not None and len(str(string_date)) > 0:
                date_list.append(parse_date(string_date))
        else:
            for str_date in date_value:
                date_list.append(parse_date(str_date))
        return date_list

    def get_num_chunks(self):
        """
        Returns number of chunks to run for each member

        :return: number of chunks
        :rtype: int
        """
        return int(self.get_section(['EXPERIMENT', 'NUMCHUNKS']))

    def get_chunk_ini(self, default=1):
        """
        Returns the first chunk from where the experiment will start

        :param default:
        :return: initial chunk
        :rtype: int
        """
        chunk_ini = self.get_section(
            ['experiment', 'CHUNKINI'], default)
        if not chunk_ini:
            return default
        return int(chunk_ini)

    def get_chunk_size_unit(self):
        """
        Unit for the chunk length

        :return: Unit for the chunk length  Options: {hour, day, month, year}
        :rtype: str
        """
        return self.get_section(['EXPERIMENT', 'CHUNKSIZEUNIT'])

    def get_chunk_size(self, default=1) -> int:
        """
        Chunk Size as defined in the expdef file.

        :return: Chunksize, 1 as default.
        :rtype: int
        """
        chunk_size = int(self.get_section(['experiment', 'CHUNKSIZE'], str(default)))
        if not chunk_size:
            return default
        return int(chunk_size)

    def get_member_list(self, run_only=False):
        """
        Returns members list from experiment's config file

        :return: experiment's members
        :rtype: list
        """
        member_list = list()
        string = str(self.get_section(['EXPERIMENT', 'MEMBERS'], "") if run_only is False else self.get_section(
            ['EXPERIMENT', 'RUN_ONLY_MEMBERS'], ""))
        if not string:
            return member_list
        elif not string.startswith("["):
            string = '[{0}]'.format(string)
        split_string = nestedExpr('[', ']').parseString(string).asList()
        string_member = None
        for split in split_string[0]:
            if type(split) is list:
                for split_in in split:
                    if split_in.find("-") != -1:
                        numbers = split_in.split("-")
                        for count in range(int(numbers[0]), int(numbers[1]) + 1):
                            member_list.append(
                                string_member + str(count).zfill(len(numbers[0])))
                    else:
                        member_list.append(string_member + split_in)
                string_member = None
            else:
                if string_member is not None and len(str(string_member)) > 0:
                    member_list.append(string_member)
                string_member = split
        if string_member is not None and len(str(string_member)) > 0:
            member_list.append(string_member)
        return member_list

    def get_rerun(self):
        """
        Returns startdates list from experiment's config file

        :return: rerurn value
        :rtype: bool
        """

        return str(self.get_section(['RERUN', 'RERUN'])).lower()

    def get_platform(self):
        """
        Returns main platforms from experiment's config file

        :return: main platforms
        :rtype: str
        """
        return self.experiment_data['DEFAULT']['HPCARCH'].upper()

    def set_last_as_command(self, command):
        """
        Set the last autosubmit command used in the experiment's config file
        :param command: current autosubmit command
        :return:
        """
        misc = os.path.join(self.conf_folder_yaml, "as_misc.yml")
        try:
            content = open(misc, 'r').read()
            if re.search('AS_MISC:.*', content):
                content = content.replace(re.search('AS_MISC:.*', content).group(0), "AS_MISC: True")
            else:
                content = "AS_MISC: True\n" + content
            if re.search('AS_COMMAND:.*', content):
                content = content.replace(re.search('AS_COMMAND:.*', content).group(0),
                                          "AS_COMMAND: {0}".format(command))
            else:
                content = content + "AS_COMMAND: {0}\n".format(command)
        except Exception:
            content = "AS_MISC: True\nAS_COMMAND: {0}\n".format(command)
        open(misc, 'w').write(content)
        os.chmod(misc, 0o755)

    def set_version(self, autosubmit_version):
        """
        Sets autosubmit's version in autosubmit's config file

        :param autosubmit_version: autosubmit's version
        :type autosubmit_version: str
        """
        version_file = os.path.join(self.conf_folder_yaml, "version.yml")
        try:
            content = open(version_file, 'r').read()
            if re.search('AUTOSUBMIT_VERSION:.*', content):
                content = content.replace(re.search('AUTOSUBMIT_VERSION:.*', content).group(0),
                                          "AUTOSUBMIT_VERSION: {0}".format(autosubmit_version))
        except Exception:
            content = "CONFIG:\n  AUTOSUBMIT_VERSION: " + autosubmit_version + "\n"
        open(version_file, 'w').write(content)
        os.chmod(version_file, 0o755)

    def get_version(self) -> str:
        """
        Returns version number of the current experiment from autosubmit's config file

        :return: version
        :rtype: str
        """
        return str(self.get_section(['CONFIG', 'AUTOSUBMIT_VERSION'], ""))

    def get_total_jobs(self) -> int:
        """
        Returns max number of running jobs  from autosubmit's config file

        :return: max number of running jobs
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'TOTALJOBS'], '-1'))

    def get_output_type(self):
        """
        Returns default output type, pdf if none

        :return: output type
        :rtype: string
        """
        return self.get_section(['CONFIG', 'OUTPUT'], 'pdf')

    def get_max_wallclock(self):
        """
        Returns max wallclock

        :rtype: str
        """
        return self.get_section(['CONFIG', 'MAX_WALLCLOCK'], "")

    def get_max_processors(self):
        """
        Returns max processors from autosubmit's config file

        :rtype: str
        """
        return self.get_section(['CONFIG', 'MAX_PROCESSORS'], '-1')

    def get_max_waiting_jobs(self) -> int:
        """
        Returns max number of waiting jobs from autosubmit's config file

        :return: main platforms
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'MAXWAITINGJOBS'], '-1'))

    def get_default_job_type(self):
        """
        Returns the default job type from experiment's config file

        :return: default type such as bash, python, r...
        :rtype: str
        """
        return self.get_section(['PROJECT_FILES', 'JOB_SCRIPTS_TYPE'], 'bash')

    def get_safetysleeptime(self) -> int:
        """
        Returns safety sleep time from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'SAFETYSLEEPTIME'], '10'))

    def get_retrials(self) -> int:
        """
        Returns max number of retrials for job from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'RETRIALS'], 0))

    def get_delay_retry_time(self):
        """
        Returns delay time from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        return self.get_section(['CONFIG', 'DELAY_RETRY_TIME'], "-1")

    def get_notifications(self):
        """
        Returns if the user has enabled the notifications from autosubmit's config file

        :return: if notifications
        :rtype: string
        """
        return str(self.get_section(['MAIL', 'NOTIFICATIONS'], "false")).lower()

    # based on https://github.com/cbirajdar/properties-to-yaml-converter/blob/master/properties_to_yaml.py
    @staticmethod
    def ini_to_yaml(root_dir: Path, ini_file: str) -> None:
        # Based on http://stackoverflow.com/a/3233356
        def update_dict(original_dict: Dict, updated_dict: collections.abc.Mapping) -> Dict:
            for k, v in updated_dict.items():
                if isinstance(v, collections.abc.Mapping):
                    r = update_dict(original_dict.get(k, {}), v)
                    original_dict[k] = r
                else:
                    original_dict[k] = updated_dict[k]
            return original_dict

        ini_file = Path(ini_file)
        # Read the file name from command line argument
        input_file = str(ini_file)
        backup_path = root_dir / Path(ini_file.name + "_AS_v3_backup")
        if not backup_path.exists():
            Log.info("Backup stored at {0}".format(backup_path))
            shutil.copyfile(ini_file, backup_path)
        # Read key=value property configs in python dictionary

        content = open(input_file, 'r', encoding=locale.getlocale()[1]).read()
        regex = r"\=( )*\[[\[\]\'_0-9.\"#A-Za-z \-,]*\]"

        matches = re.finditer(regex, content, flags=re.IGNORECASE)

        for matchNum, match in enumerate(matches, start=1):
            print(match.group())
            subs_string = "= " + "\"" + match.group()[2:] + "\""
            regex_sub = match.group()
            content = re.sub(re.escape(regex_sub), subs_string, content)

        open(input_file, 'w', encoding=locale.getlocale()[1]).write(content)
        config_dict = ConfigObj(input_file, stringify=True, list_values=False, interpolation=False, unrepr=False)

        # Store the result in yaml_dict
        yaml_dict = {}

        for key, value in config_dict.items():
            config_keys = key.split(".")

            for config_key in reversed(config_keys):
                value = {config_key: value}

            yaml_dict = update_dict(yaml_dict, value)

        final_dict = {}
        if input_file.find("platform") != -1:
            final_dict["PLATFORMS"] = yaml_dict
        elif input_file.find("job") != -1:
            final_dict["JOBS"] = yaml_dict
        else:
            final_dict = yaml_dict
            # Write resultant dictionary to the yaml file
        yaml_file = open(input_file, 'w', encoding=locale.getlocale()[1])
        yaml = YAML()
        yaml.dump(final_dict, yaml_file)
        ini_file.rename(Path(root_dir, ini_file.stem + ".yml"))

    def get_remote_dependencies(self):
        """
        Returns if the user has enabled the PRESUBMISSION configuration parameter from autosubmit's config file

        :return: if remote dependencies
        :rtype: string
        """
        # Disabled, forced to "false" not working anymore in newer slurm versions.
        return "false"
        # return str(self.get_section(['CONFIG', 'PRESUBMISSION'], "false")).lower()

    def get_wrapper_type(self, wrapper=None):
        """
        Returns what kind of wrapper (VERTICAL, MIXED-VERTICAL, HORIZONTAL, HYBRID, MULTI NONE) the user has configured in the autosubmit's config

        :return: wrapper type (or none)
        :rtype: string
        """
        if wrapper is None:
            wrapper = {}
        if wrapper:
            return wrapper.get('TYPE', self.experiment_data.get("WRAPPERS", {}).get("TYPE", ""))
        return None

    def get_wrapper_policy(self, wrapper=None):
        """
        Returns what kind of policy (flexible, strict, mixed ) the user has configured in the autosubmit's config

        :return: wrapper type (or none)
        :rtype: string
        """
        if wrapper is None:
            wrapper = {}
        return wrapper.get('POLICY', self.experiment_data.get("WRAPPERS", {}).get("POLICY", 'flexible'))

    def get_wrappers(self):
        """
        Returns the jobs that should be wrapped, configured in the autosubmit's config

        :return: expression
        :rtype: dict
        """
        return self.experiment_data.get("WRAPPERS", {})

    def get_wrapper_jobs(self, wrapper=None):
        """
        Returns the jobs that should be wrapped, configured in the autosubmit's config

        :return: expression (or none)
        :rtype: string
        """
        if wrapper is None:
            return ""
        aux = wrapper.get('JOBS_IN_WRAPPER', self.experiment_data.get("WRAPPERS", {}).get("JOBS_IN_WRAPPER", ""))
        aux = aux.split()
        aux = [x.split("&") for x in aux]
        jobs_in_wrapper = []
        for section_list in aux:
            for section in section_list:
                jobs_in_wrapper.append(section)

        return jobs_in_wrapper

    def get_extensible_wallclock(self, wrapper=None):
        """
        Gets extend_wallclock for the given wrapper

        :param wrapper: wrapper
        :type wrapper: dict
        :return: extend_wallclock
        :rtype: int
        """
        if wrapper is None:
            wrapper = {}
        return int(wrapper.get('EXTEND_WALLCLOCK', 0))

    def get_wrapper_queue(self, wrapper=None):
        """
        Returns the wrapper queue if not defined, will be the one of the first job wrapped

        :return: expression (or none)
        :rtype: string
        """
        if wrapper is None:
            wrapper = {}
        return wrapper.get('QUEUE', self.experiment_data.get("WRAPPERS", {}).get("QUEUE", ""))

    def get_wrapper_partition(self, wrapper=None):
        """
        Returns the wrapper queue if not defined, will be the one of the first job wrapped

        :return: expression (or none)
        :rtype: string
        """
        if wrapper is None:
            wrapper = {}
        return wrapper.get('PARTITION', self.experiment_data.get("WRAPPERS", {}).get("PARTITION", ""))

    def get_wrapper_method(self, wrapper=None):
        """
         Returns the method of make the wrapper

         :return: method
         :rtype: string
         """
        if wrapper is None:
            wrapper = {}
        return wrapper.get('METHOD', self.experiment_data.get("WRAPPERS", {}).get("METHOD", 'ASThread'))

    def get_wrapper_check_time(self):
        """
         Returns time to check the status of jobs in the wrapper

         :return: wrapper check time
         :rtype: int
         """
        wrapper = self.experiment_data.get("WRAPPERS", {})

        return wrapper.get("CHECK_TIME_WRAPPER", self.get_safetysleeptime())

    def get_wrapper_machinefiles(self, wrapper=None):
        """
         Returns the strategy for creating the machinefiles in wrapper jobs

         :return: machinefiles function to use
         :rtype: string
         """
        if wrapper is None:
            wrapper = {}
        return wrapper.get('MACHINEFILES', self.experiment_data.get("WRAPPERS", {}).get("MACHINEFILES", ""))

    def get_copy_remote_logs(self):
        """
        Returns if the user has enabled the logs local copy from autosubmit's config file

        :return: if logs local copy
        :rtype: str
        """
        return str(self.get_section(['STORAGE', 'COPY_REMOTE_LOGS'], "true")).lower()

    def get_mails_to(self):
        """
        Returns the address where notifications will be sent from autosubmit's config file

        :return: mail address
        :rtype: [str]
        """
        return self.get_section(['MAIL', 'TO'], "")

    def get_communications_library(self):
        """
        Returns the communications library from autosubmit's config file. Paramiko by default.

        :return: communications library
        :rtype: str
        """
        return self.get_section(['COMMUNICATIONS', 'API'], 'paramiko')

    def get_storage_type(self):
        """
        Returns the storage system from autosubmit's config file. Pkl by default.

        :return: communications library
        :rtype: str
        """
        return self.get_section(['STORAGE', 'TYPE'], 'pkl')


    def is_valid_jobs_in_wrapper(self, wrapper={}):
        expression = self.get_wrapper_jobs(wrapper)
        jobs_data = self.experiment_data.get("JOBS", {}).keys()
        if expression is not None and len(str(expression)) > 0:
            for section in expression:
                if section not in jobs_data:
                    return False
        return True

    def is_valid_git_repository(self):
        origin_exists = str(self.experiment_data["GIT"].get('PROJECT_ORIGIN', ""))
        branch = self.get_git_project_branch()
        commit = self.get_git_project_commit()
        return origin_exists and (
                (branch is not None and len(str(branch)) > 0) or (commit is not None and len(str(commit)) > 0))

    def parse_githooks(self):
        """
        Parse githooks section in configuration file

        :return: dictionary with githooks configuration
        :rtype: dict
        """
        proj_dir = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, self.expid, BasicConfig.LOCAL_PROJ_DIR)
        # get project_name
        project_name = str(self.get_project_destination())

        # get githook files from proj_dir
        githook_files = [os.path.join(os.path.join(os.path.join(proj_dir, project_name), ".githooks"), f) for f in
                         os.listdir(os.path.join(os.path.join(proj_dir, project_name), ".githooks"))]
        parameters = self.load_parameters()

        # find all '%(?<!%%)\w+%(?!%%)' in githook files
        for githook_file in githook_files:
            f_name, ext = os.path.splitext(githook_file)
            if ext == ".tmpl":
                with open(githook_file, 'r') as f:
                    content = f.read()
                matches = re.findall('%(?<!%%)[a-zA-Z0-9_.-]+%(?!%%)', content, flags=re.IGNORECASE)
                for match in matches:
                    # replace all '%(?<!%%)\w+%(?!%%)' with parameters value
                    content = content.replace(match, parameters.get(match[1:-1], ""))
                with open(f_name, 'w') as f:
                    f.write(content)
                    os.chmod(f_name, 0o750)
        pass

    @staticmethod
    def get_parser(parser_factory, file_path) -> YAMLParser:
        """
        Gets parser for given file

        :param parser_factory:
        :param file_path: path to file to be parsed
        :type file_path: Path
        :return: parser
        :rtype: YAMLParser
        """
        parser = parser_factory.create_parser()
        # For testing purposes
        if file_path == Path('/dummy/local/root/dir/a000/conf/') or file_path == Path('dummy/file/path'):
            parser.data = parser.load(file_path)
            if parser.data is None:
                parser.data = {}
            return parser

            # proj file might not be present

        if file_path.match("*proj*"):
            if file_path.exists():
                parser.data = parser.load(file_path)
                if parser.data is None:
                    parser.data = {}
            else:
                parser.data = {}
            # else:
            # Log.warning( "{0} was not found. Some variables might be missing. If your experiment does not need a proj file, you can ignore this message.", file_path)
        else:
            # This block may rise an exception but all its callers handle it
            try:
                with open(file_path) as f:
                    parser.data = parser.load(f)
                    if parser.data is None:
                        parser.data = {}
            except IOError:
                parser.data = {}
                return parser
            except Exception as exp:
                raise Exception(
                    "{}\n This file and the correctness of its content are necessary.".format(str(exp)))
        return parser


def _normalize_parameters_keys(parameters: Dict[str, Any], default_parameters: Dict[str, Any] = None) -> None:
    """Modifies the given dictionary in-place, making keys all uppercase.

    :param parameters: dictionary containing the parameters
    :param default_parameters: dictionary containing the default parameters, they must remain in lower-case
    :return: upper-case parameters
    """
    if not default_parameters:
        default_parameters = {}

    parameters_copy = parameters.copy()

    for key, value in parameters_copy.items():
        if key not in default_parameters.keys():
            parameters[key.upper()] = value

    del parameters_copy


def deep_normalize(data: Dict[str, Any]) -> None:
    """
    Normalize a nested dictionary or similar mapping to uppercase.

    This function recursively iterates through a dictionary, converting all keys to uppercase.
    If a value is a dictionary, it calls itself recursively to normalize the nested dictionary.
    If a value is a list, it iterates through the list and normalizes any dictionaries keys within it.
    Other types of values are added to the normalized dictionary as is.

    :param data: The dictionary to normalize.
    :type data: Dict[str, Any]
    :return: A new dictionary with all keys normalized to uppercase.
    :rtype: Dict[str, Any]
    """
    d_copy = data.copy()
    for key, val in d_copy.items():
        normalized_key = key.upper()
        if isinstance(val, collections.abc.Mapping):
            deep_normalize(cast(Dict[str, Any], val))
        elif isinstance(val, list):
            normalized_list = []
            for item in val:
                if isinstance(item, collections.abc.Mapping):
                    normalized_list.append(deep_normalize(cast(Dict[str, Any], item)))
                else:
                    normalized_list.append(item)
            data[normalized_key] = normalized_list
        elif key != normalized_key:
            data[normalized_key] = val
    del d_copy


def _convert_list_to_string(data):
    """Convert a list to a string"""
    if type(data) is dict:
        for key, val in data.items():
            if isinstance(val, list):
                data[key] = ",".join(val)
            elif isinstance(val, dict):
                _convert_list_to_string(data[key])
    return data


def _is_valid_mail_address(mail_address):
    if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', mail_address,
                flags=re.IGNORECASE):
        return True
    else:
        return False


__all__ = ['AutosubmitConfig', 'deep_normalize']
