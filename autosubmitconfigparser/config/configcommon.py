#!/usr/bin/env python3

# Copyright 2015-2022 Earth Sciences Department, BSC-CNS

# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.
import shutil
import numbers


import os
import re
import subprocess
import traceback
import json
import ruamel.yaml as yaml
from .basicconfig import BasicConfig
from .yamlparser import YAMLParserFactory
from configobj import ConfigObj
from log.log import Log,AutosubmitCritical,AutosubmitError

from pyparsing import nestedExpr

from bscearth.utils.date import parse_date

from collections import defaultdict
import collections
import datetime
import copy
from datetime import datetime, timedelta
from pathlib import Path
import locale

class AutosubmitConfig(object):
    """
    Class to handle experiment configuration coming from file or database

    :param expid: experiment identifier
    :type expid: str
    """

    def __init__(self, expid, basic_config=BasicConfig, parser_factory=YAMLParserFactory()):
        self.ignore_undefined_platforms = False
        self.expid = expid
        self.basic_config = basic_config
        self.basic_config.read()
        self.parser_factory = parser_factory
        self.experiment_data = {}
        self.data_loops = list()
        self._conf_parser = None
        self._conf_parser_file = Path(self.basic_config.LOCAL_ROOT_DIR) / expid / "conf" / ("autosubmit_" + expid + ".yml")
        self._conf_parser_file_modtime = None
        self._exp_parser = None
        self._exp_parser_file = Path(self.basic_config.LOCAL_ROOT_DIR) / expid / "conf" / ("expdef_" + expid + ".yml")
        self._exp_parser_file_modtime = None

        self._platforms_parser = None
        self._platforms_parser_file = Path(self.basic_config.LOCAL_ROOT_DIR) / expid / "conf" / ("platforms_" + expid + ".yml")
        self._platforms_parser_file_modtime = None

        self._jobs_parser = None
        self._jobs_parser_file = Path(self.basic_config.LOCAL_ROOT_DIR) / expid / "conf" / ("jobs_" + expid + ".yml")
        self._jobs_parser_file_modtime = None
        self._proj_parser = None
        self._proj_parser_file = Path(self.basic_config.LOCAL_ROOT_DIR) / expid / "conf" / ("proj_" + expid +".yml")
        self._proj_parser_file_modtime = None

        self._original_parser_files = []
        self._original_parser_files.append(self._conf_parser_file)
        self._original_parser_files.append(self._exp_parser_file)
        self._original_parser_files.append(self._platforms_parser_file)
        self._original_parser_files.append(self._jobs_parser_file)
        self._original_parser_files.append(self._proj_parser_file)
        self._original_parser_files_modtime = []
        self._original_parser_files_modtime.append(self._conf_parser_file_modtime)
        self._original_parser_files_modtime.append(self._exp_parser_file_modtime)
        self._original_parser_files_modtime.append(self._platforms_parser_file_modtime)
        self._original_parser_files_modtime.append(self._jobs_parser_file_modtime)
        self._original_parser_files_modtime.append(self._proj_parser_file_modtime)

        self._custom_parser_files = []
        self._custom_parser_files_modtime = []

        self.ignore_file_path = False
        self.wrong_config = defaultdict(list)
        self.warn_config = defaultdict(list)
        self.dynamic_variables = list()
        #todo ?? threads are loading all parameters -> reduce memory usage
    @property
    def jobs_parser(self):
        return self._jobs_parser

    @property
    def experiment_file(self):
        """
        Returns experiment's config file name
        """
        return self._exp_parser_file

    @property
    def platforms_parser(self):
        """
        Returns experiment's platforms parser object

        :return: platforms config parser object
        :rtype: SafeConfigParser
        """
        return self._platforms_parser

    @property
    def platforms_file(self):
        """
        Returns experiment's platforms config file name

        :return: platforms config file's name
        :rtype: str
        """
        return self._platforms_parser_file

    @property
    def unified_data(self):
        return self.experiment_data

    @property
    def jobs_data(self):
        return self.experiment_data["JOBS"]

    @property
    def platforms_data(self):
        return self.experiment_data["PLATFORMS"]

    @property
    def project_file(self):
        """
        Returns project's config file name
        """
        return self._proj_parser_file

    def check_proj_file(self):
        """
        Add a section header to the project's configuration file (if not exists)
        """
        if os.path.exists(self._proj_parser_file):
            with open(self._proj_parser_file, 'rb+') as f:
                first_line = f.readline()
                if not re.match('^\[[^\[\]\# \t\n]*\][ \t]*$|^[ \t]+\[[^\[\]# \t\n]*\]', first_line):
                    content = f.read()
                    f.seek(0, 0)
                    f.write('[DEFAULT]'.rstrip('\r\n') +
                            '\n' + first_line + content)
                    f.close()

    @property
    def jobs_file(self):
        """
        Returns project's jobs file name
        """
        return self._jobs_parser_file


    def get_wrapper_export(self, wrapper={}):
        """
         Returns modules variable from wrapper

         :return: string
         :rtype: string
         """
        return wrapper.get('EXPORT', self.experiment_data["WRAPPERS"].get("EXPORT",""))
    def get_project_submodules_depth(self):
        """
        Returns the max depth of submodule at the moment of cloning
        Default is -1 (no limit)
        :return: depth
        :rtype: list
        """
        git_data= self.experiment_data.get("GIT",{})
        unparsed_depth = git_data.get('PROJECT_SUBMODULES_DEPTH', "-1")
        if "[" in unparsed_depth and "]" in unparsed_depth:
            unparsed_depth = unparsed_depth.strip("[]")
            depth = [int(x) for x in unparsed_depth.split(",")]
        else:
            try:
                depth = int(unparsed_depth)
                depth = [depth]
            except:
                Log.warning("PROJECT_SUBMODULES_DEPTH is not an integer neither a int. Using default value -1")
                depth = []
        return depth
    def get_full_config_as_json(self):
        """
        Return config as json object
        """
        try:
            return json.dumps(self.experiment_data)
        except Exception as exp:
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

    def get_export(self, section):
        """
        Gets command line for being submitted with
        :param section: job type
        :type section: str
        :return: wallclock time
        :rtype: str
        """
        return self.get_section([section, 'EXPORT'], "")

    def get_x11(self, section):
        """
        Active X11 for this section
        :param section: job type
        :type section: str
        :return: false/true
        :rtype: str
        """
        return str(self.get_section([section, 'X11'], "false")).lower()

    def get_section(self, section, d_value="", must_exists = False ):
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
        # For text redeability
        section_str = str(section[0])
        for sect in section[1:]:
            section_str += "." + str(sect)
        current_level=self.experiment_data.get(section[0],"")
        for param in section[1:]:
            if current_level:
                if type(current_level) == dict:
                    current_level = current_level.get(param,d_value)
                else:
                    if must_exists:
                        raise AutosubmitCritical(
                            "[INDEX ERROR], {0} must exists. Check that {1} is an section that exists.".format(section_str,
                                                                                                               str(current_level)),
                            7014)
        if current_level is None or ( not isinstance(current_level,numbers.Number) and len(current_level) == 0) and must_exists:
           raise AutosubmitCritical(
               "{0} must exists. Check that subsection {1} exists.".format(section_str, str(current_level)), 7014)
        if current_level is None or ( not isinstance(current_level,numbers.Number) and len(current_level) == 0):
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
        return self.get_section([section, 'WCHUNKINC'], "")

    def get_synchronize(self, section):
        """
        Gets wallclock for the given job type
        :param section: job type
        :type section: str
        :return: wallclock time
        :rtype: str
        """
        return self.get_section([section, 'SYNCHRONIZE'], "")

    def get_processors(self, section):
        """
        Gets processors needed for the given job type
        :param section: job type
        :type section: str
        :return: wallclock time
        :rtype: str
        """
        return str(self.get_section([section, 'PROCESSORS'], 1))

    def get_threads(self, section):
        """
        Gets threads needed for the given job type
        :param section: job type
        :type section: str
        :return: threads needed
        :rtype: str
        """

        return str(self.get_section([section, 'THREADS'], 1))

    def get_tasks(self, section):
        """
        Gets tasks needed for the given job type
        :param section: job type
        :type section: str
        :return: tasks (processes) per host
        :rtype: str
        """
        return str(self.get_section([section, 'TASKS'], ""))

    def get_scratch_free_space(self, section):
        """
        Gets scratch free space needed for the given job type
        :param section: job type
        :type section: str
        :return: percentage of scratch free space needed
        :rtype: int
        """
        return int(self.get_section([section, 'SCRATCH_FREE_SPACE'], ""))

    def get_memory(self, section):
        """
        Gets memory needed for the given job type
        :param section: job type
        :type section: str
        :return: memory needed
        :rtype: str
        """
        return str(self.get_section([section, 'MEMORY'], ""))

    def get_memory_per_task(self, section):
        """
        Gets memory per task needed for the given job type
        :param section: job type
        :type section: str
        :return: memory per task needed
        :rtype: str
        """
        return str(self.get_section([section, 'MEMORY_PER_TASK'], ""))

    def get_migrate_user_to(self, section):
        """
        Returns the user to change to from platform config file.

        :return: migrate user to
        :rtype: str
        """
        return self.get_section([section, 'USER_TO'], "")

    def get_migrate_duplicate(self, section):
        """
        Returns the user to change to from platform config file.

        :return: migrate user to
        :rtype: str
        """
        return str(self.get_section([section, 'SAME_USER'], "false")).lower()

    def get_current_user(self, section):
        """
        Returns the user to be changed from platform config file.

        :return: migrate user to
        :rtype: str
        """
        return self.get_section([section, 'USER'], "")

    def get_current_host(self, section):
        """
        Returns the user to be changed from platform config file.

        :return: migrate user to
        :rtype: str
        """
        return self.get_section([section, 'HOST'], "")

    def get_current_project(self, section):
        """
        Returns the project to be changed from platform config file.

        :return: migrate user to
        :rtype: str
        """
        return self.get_section([section, 'PROJECT'], "")

    def set_new_user(self, section, new_user):
        """
        Sets new user for given platform
        :param new_user: 
        :param section: platform name
        :type: str
        """

        with open(self._platforms_parser_file) as p_file:
            contentLine = p_file.readline()
            contentToMod = ""
            content = ""
            mod = False
            while contentLine:
                if re.search(section, contentLine):
                    mod = True
                if mod:
                    contentToMod += contentLine
                else:
                    content += contentLine
                contentLine = p_file.readline()
        if mod:
            old_user = self.get_current_user(section)
            contentToMod = contentToMod.replace(re.search(
                'USER:.*', contentToMod).group(0)[1:], "USER: " + new_user)
            contentToMod = contentToMod.replace(re.search(
                'USER_TO:.*', contentToMod).group(0)[1:], "USER_TO: " + old_user)
        open(self._platforms_parser_file, 'w').write(content)
        open(self._platforms_parser_file, 'a').write(contentToMod)

    def set_new_host(self, section, new_host):
        """
        Sets new host for given platform
        :param new_host:
        :param section: platform name
        :type: str
        """
        with open(self._platforms_parser_file) as p_file:
            contentLine = p_file.readline()
            contentToMod = ""
            content = ""
            mod = False
            while contentLine:
                if re.search(section, contentLine):
                    mod = True
                if mod:
                    contentToMod += contentLine
                else:
                    content += contentLine
                contentLine = p_file.readline()
        if mod:
            old_host = self.get_current_host(section)
            contentToMod = contentToMod.replace(re.search(
                'HOST:.*', contentToMod).group(0)[1:], "HOST: " + new_host)
            contentToMod = contentToMod.replace(re.search(
                'HOST_TO:.*', contentToMod).group(0)[1:], "HOST_TO: " + old_host)
        open(self._platforms_parser_file, 'w').write(content)
        open(self._platforms_parser_file, 'a').write(contentToMod)

    def get_migrate_project_to(self, section):
        """
        Returns the project to change to from platform config file.

        :return: migrate project to
        :rtype: str
        """
        return self.get_section([section, 'PROJECT_TO'], "")

    def get_migrate_host_to(self, section):
        """
        Returns the host to change to from platform config file.

        :return: host_to
        :rtype: str
        """
        return self.get_section([section, 'HOST_TO'], "")

    def set_new_project(self, section, new_project):
        """
        Sets new project for given platform
        :param new_project: 
        :param section: platform name
        :type: str
        """
        with open(self._platforms_parser_file) as p_file:
            contentLine = p_file.readline()
            contentToMod = ""
            content = ""
            mod = False
            while contentLine:
                if re.search(section, contentLine):
                    mod = True
                if mod:
                    contentToMod += contentLine
                else:
                    content += contentLine
                contentLine = p_file.readline()
        if mod:
            old_project = self.get_current_project(section)
            contentToMod = contentToMod.replace(re.search(
                "PROJECT:.*", contentToMod).group(0)[1:], "PROJECT: " + new_project)
            contentToMod = contentToMod.replace(re.search(
                "PROJECT_TO:.*", contentToMod).group(0)[1:], "PROJECT_TO: " + old_project)
        open(self._platforms_parser_file, 'w').write(content)
        open(self._platforms_parser_file, 'a').write(contentToMod)

    def get_custom_directives(self, section):
        """
        Gets custom directives needed for the given job type
        :param section: job type
        :type section: str
        :return: custom directives needed
        :rtype: str
        """
        directives = self.get_section([section, 'CUSTOM_DIRECTIVES'],"")
        return directives

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

    def deep_normalize(self,data):
        """
        normalize a nested dictionary or similar mapping to uppercase.
        Modify ``source`` in place.
        """

        normalized_data =  dict()
        try:
            for key, val in data.items():
                normalized_data[str(key).upper()] = val
                if isinstance(val, collections.abc.Mapping ):
                    normalized_value = self.deep_normalize(data.get(key, {}))
                    normalized_data[str(key).upper()] = normalized_value
        except:
            pass
        return normalized_data

    def deep_update(self,unified_config, new_dict):
        """
        Update a nested dictionary or similar mapping.
        Modify ``source`` in place.
        """
        for key, val in new_dict.items():
            if isinstance(val, collections.abc.Mapping ):
                tmp = self.deep_update(unified_config.get(key, {}), val)
                unified_config[key] = tmp
            elif isinstance(val, list):
                unified_config[key] = (unified_config.get(key, []) + val)
            else:
                unified_config[key] = new_dict[key]
        return unified_config

    def normalize_variables(self,data):
        """
        Apply some memory internal variables to normalize it format. (right now only dependencies)
        """
        data_fixed = data

        for job, job_data in data.get("JOBS",{}).items():
            aux_dependencies = dict()
            dependencies = job_data.get("DEPENDENCIES",{})
            custom_directives = job_data.get("CUSTOM_DIRECTIVES","")
            if type(dependencies) == str:
                for dependency in dependencies.split(" "):
                    aux_dependencies[dependency] = {}
                dependencies = aux_dependencies
            if type(custom_directives) != str:
                data_fixed["JOBS"][job]["CUSTOM_DIRECTIVES"] = str(custom_directives)
            data_fixed["JOBS"][job]["DEPENDENCIES"] = dependencies
            files = job_data.get("FILE","")
            if ',' in files:
                files = files.split(",")
            elif ' ' in files:
                files = files.split(" ")
            else:
                files = [files]
            data_fixed["JOBS"][job]["FILE"] = files[0]
            data_fixed["JOBS"][job]["ADDITIONAL_FILES"] = []
            for file in files[1:]:
                data_fixed["JOBS"][job]["ADDITIONAL_FILES"].append(file)

        return data_fixed

    def dict_replace_value(self,d: dict, old: str, new: str) -> dict:
        x = {}
        for k, v in d.items():
            if isinstance(v, dict):
                v = self.dict_replace_value(v, old, new)
            elif isinstance(v, list):
                v = self.list_replace_value(v, old, new)
            elif isinstance(v, str):
                v = v.replace(old, new)
            x[k] = v
        return x

    def list_replace_value(self,l: list, old: str, new: str) -> list:
        x = []
        for e in l:
            if isinstance(e, list):
                e = self.list_replace_value(e, old, new)
            elif isinstance(e, dict):
                e = self.dict_replace_value(e, old, new)
            elif isinstance(e, str):
                e = e.replace(old, new)
            x.append(e)
        return x


    def unify_conf(self):
        '''
        Unifies all configuration files into a single dictionary. Custom files will be able to override the default configuration.
        '''
        if self._conf_parser.data is not None and len(self._conf_parser.data) > 0:
            self._conf_parser.data = self.normalize_variables(self._conf_parser.data)
        if self._exp_parser.data is not None and len(self._exp_parser.data) > 0:
            self._exp_parser.data = self.normalize_variables(self._exp_parser.data)
        if self._jobs_parser.data is not None and len(self._jobs_parser.data) > 0:
            self._jobs_parser.data = self.normalize_variables(self._jobs_parser.data)
        if self._platforms_parser.data is not None and len(self._platforms_parser.data) > 0:
            self._platforms_parser.data = self.normalize_variables(self._platforms_parser.data)
        if self._conf_parser.data is not None and len(self._conf_parser.data) > 0:
            self._conf_parser.data = self.deep_normalize(self._conf_parser.data)
        if self._exp_parser.data is not None and len(self._exp_parser.data) > 0:
            self._exp_parser.data = self.deep_normalize(self._exp_parser.data)
        if self._jobs_parser.data is not None and len(self._jobs_parser.data) > 0:
            self._jobs_parser.data = self.deep_normalize(self._jobs_parser.data)
        if self._platforms_parser.data is not None and len(self._platforms_parser.data) > 0:
            self._platforms_parser.data = self.deep_normalize(self._platforms_parser.data)
        self.experiment_data = dict()
        self.experiment_data = self.deep_update(self._conf_parser.data,self._exp_parser.data)
        self.experiment_data = self.deep_update(self.experiment_data,self._jobs_parser.data)
        self.experiment_data = self.deep_update(self.experiment_data,self._platforms_parser.data)
        if self._proj_parser_file.exists():
            self._proj_parser.data = self.deep_normalize(self._proj_parser.data)
            self.normalize_variables(self._proj_parser.data)
            self.experiment_data = self.deep_update(self.experiment_data,self._proj_parser.data)
        #Check if there is "FOR" clausure (Recursive search)
        self.deep_read_loops(self.experiment_data)
        #Parse loops in original config
        self.parse_data_loops(self.experiment_data,self.data_loops)

        if len(self._custom_parser) > 0:
            for c_parser in self._custom_parser:
                c_parser.data = self.deep_normalize(c_parser.data)
                self.normalize_variables(c_parser.data)
                self.experiment_data = self.deep_update(self.experiment_data,c_parser.data)
            #Parser loops in custom config
            self.deep_read_loops(self.experiment_data)
            self.parse_data_loops(self.experiment_data, self.data_loops)
        self.dynamic_variables = list(set(self.dynamic_variables))
        self.experiment_data = self.sustitute_dynamic_variables(self.experiment_data,max_deep=25)

    def parse_data_loops(self,exp_data,data_loops):
        section_data = list()
        for loops in data_loops:
            #Extract section affected
            current_data = exp_data.pop(loops[0])
            section_data.append(current_data)
            #Extract nested-section if any
            for section in loops[1:]:
                current_data = current_data.pop(section)
                section_data.append(current_data)

            section_basename = loops[-1]
            for_sections = section_data[-1].pop("FOR")
            #Delete old key
            loops.pop()
            # Delete old data
            section_data.pop()
            new_sections = dict()
            section_ending_name = for_sections.get("NAME",[])
            for_sections.pop("NAME")
            n_sections_to_create = len(for_sections[list(for_sections)[0]])
            if len(section_ending_name) == 0:
                for i in range(0,n_sections_to_create):
                    section_ending_name.append(str(i))
            full_name = []
            new_data = dict()

            for i in range(0,n_sections_to_create):
                full_name.append(section_basename + "_" + str(section_ending_name[i]))
                new_data[full_name[i]] = copy.deepcopy(current_data)

            # Last level must contain the new info
            last_data = section_data.pop(-1)
            last_level = loops.pop(-1)
            #Fill new camps

            for i in range(0, n_sections_to_create):
                for key,val_list in for_sections.items():
                    new_data[full_name[i]][key] = val_list[i]
            #update last dict level
            last_data.update(new_data)
            # backtracking
            next_section = dict()
            next_section[last_level] = last_data
            new_exp_data = next_section
            while len(loops) > 0:
                level_name = loops.pop(-1)
                level_data = section_data.pop(-1)
                level_data.update(new_exp_data)
                new_exp_data[level_name] = level_data
            else:
                new_exp_data = next_section
            self.experiment_data.update(new_exp_data)
            exp_data = self.experiment_data
            pass
        self.data_loops = []
    def get_placeholders(self,val,key):

        aux_name = val.split("/")
        full_name = []
        for aux in aux_name:
            full_name.extend(aux.split(" "))
        placeholders = []
        for posible_placeholder in full_name:
            if "%" in posible_placeholder or key:
                placeholders.append(posible_placeholder.strip("%"))
        return placeholders

    def check_dict_keys_type(self,parameters):
        '''
        Check if keys are plain into 1 dimension, checks for 33% of dict to ensure it.
        :param parameters: experiment parameters
        :return:
        '''
        amount_of_keys_to_check = int(len(parameters)/3)+1
        count_dot = 0
        count = 0
        for key in parameters.keys():
            if "." in key:
                count_dot+=1
            count+=1
            if count >= amount_of_keys_to_check:
                break
        if count_dot >= int(count/2)+1:
            dict_keys_type = "long"
        else:
            dict_keys_type = "short"
        return dict_keys_type
    def sustitute_dynamic_variables(self,parameters=None,max_deep=25,dict_keys_type=None):
        """
        Substitute dynamic variables in the experiment data
        :parameter
        :return:
        """

        if parameters is None:
            parameters = self.deep_parameters_export(self.experiment_data)
        # Check if the parameters key provided are long(%DEFAULT.EXPID%) or short(DEFAULT[EXPID]) if it is not specified.
        if dict_keys_type is None:
            dict_keys_type = self.check_dict_keys_type(parameters)
        backup_variables = self.dynamic_variables
        while len(self.dynamic_variables) > 0 and max_deep > 0:
            dynamic_variables = []
            for dynamic_var in self.dynamic_variables:
                rest_of_keys = ""
                #get value of placeholder with  name without %%
                if dict_keys_type == "long":
                    value = parameters.get(str(dynamic_var[1][1:-1]),None)
                else:
                    keys = dynamic_var[1]
                    # get substring of key between %%
                    pattern = '%[a-zA-Z0-9_.]*%'
                    match = (re.search(pattern, keys))
                    if match is not None:
                        rest_of_keys = keys[match.end():]
                        keys = keys[match.start():match.end()]

                        if "." in keys:
                            keys = keys[1:-1].split(".")
                        else:
                            keys = [keys[1:-1]]
                    aux_dict = parameters
                    for k in keys:
                        aux_dict = aux_dict.get(k,{})
                    if len(aux_dict) > 0:
                        value = str(aux_dict)+str(rest_of_keys)
                    else:
                        value = None
                if value is not None:
                    if dict_keys_type == "long":
                        dict_key = parameters.get(str(dynamic_var[0]), {})
                        if len(dict_key) > 0:
                            substituted = True
                            parameters[str(dynamic_var[0])] = value
                        else:
                            substituted = False
                    else:
                        # See input and output below todo
                        substituted = False
                        parameters = self.dict_replace_value(parameters, dynamic_var[1], value)
                else:
                    substituted = False
                if not substituted:
                    dynamic_variables.append(dynamic_var)
            self.dynamic_variables = dynamic_variables
            max_deep = max_deep - 1
        self.dynamic_variables = backup_variables
        return parameters
    def sustitute_placeholder_variables(self,key,val,parameters):
        substituted = False
        data = parameters
        placeholders=self.get_placeholders(val, False)
        new_placeholders = False
        for section in placeholders:
            get_data = data.get(section, {})
            if not isinstance(get_data, collections.abc.Mapping):
                put_data = parameters.get(key, None)
                if put_data is not None and len(str(put_data)) > 0:
                    if "%" in str(get_data):
                        new_placeholders = True
                    parameters[key] = re.sub('%(?<!%%)' + section + '%(?!%%)', str(get_data), parameters[key],flags=re.I)
                    substituted = True

                else:
                    substituted = False
        if new_placeholders:
            self.dynamic_variables.append((key,parameters[key]))

        return substituted,parameters
    def deep_read_loops(self,data,for_keys=[],long_key=""):
        """
        Update a nested dictionary or similar mapping.
        Modify ``source`` in place.
        """
        for key, val in data.items():
            # Placeholders variables
            if not isinstance(val, collections.abc.Mapping) and "%" in str(val):
                self.dynamic_variables.append((long_key+key, val))
            if key == "FOR":
                self.data_loops.append(for_keys)
            elif isinstance(val, collections.abc.Mapping ):
                self.deep_read_loops(data.get(key, {}),for_keys+[key],long_key=long_key+key+".")






    def check_mandatory_conf_files(self,refresh=False,no_log=False):
        #self.unify_conf()
        self.check_expdef_conf(refresh,no_log=no_log)
        self.check_platforms_conf(no_log=no_log)
        self.check_jobs_conf(no_log=no_log)
        self.check_autosubmit_conf(refresh,no_log=no_log)

    def check_conf_files(self, running_time=False,first_load=True,refresh=False,no_log=False):
        """
        Checks configuration files (autosubmit, experiment jobs and platforms), looking for invalid values, missing
        required options. Print results in log
        :param running_time: True if the function is called during the execution of the program
        :type running_time: bool
        :param first_load: True if the function is called during the first load of the program
        :type first_load: bool
        :param refresh: True if the function is called during the refresh of the program
        :type refresh: bool
        :param no_log: True if the function is called during describe
        :type no_log: bool

        :return: True if everything is correct, False if it finds any error
        :rtype: bool
        """
        if not no_log:
            Log.info('\nChecking configuration files...')
        self.ignore_file_path = running_time
        self.ignore_undefined_platforms = running_time

        try:
            self.reload(first_load)
        except IOError as e:
            raise AutosubmitError(
                "I/O Issues con config files", 6016, str(e))
        except (AutosubmitCritical, AutosubmitError) as e:
            raise
        except BaseException as e:
            raise AutosubmitCritical("Unknown issue while checking the configuration files (check_conf_files)",7040,str(e))
        # Annotates all errors found in the configuration files in dictionaries self.warn_config and self.wrong_config.
        self.check_mandatory_conf_files(refresh,no_log=no_log)
        try:
            if self.get_project_type():
                self.check_proj()
        except:
            pass
        # End of checkers.
        # This Try/Except is in charge of  print all the info gathered by all the checkers and stop the program if any critical error is found.
        try:
            if not no_log:
                result = self.show_messages()
                return result
        except AutosubmitCritical as e:
            # In case that there are critical errors in the configuration, Autosubmit won't continue.
            if running_time is True:
                raise AutosubmitCritical(e.message, e.code, e.trace)
            else:
                if not no_log:
                    Log.warning(e.message)
        except Exception as e:
            raise AutosubmitCritical(
                "There was an error while showing the config log messages", 7014, str(e))

    def check_autosubmit_conf(self,refresh=False,no_log=False):
        """
        Checks experiment's autosubmit configuration file.
        :param refresh: True if the function is called during the refresh of the program
        :type refresh: bool
        :param no_log: True if the function is called during describe
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        parser_data = self.experiment_data
        if parser_data.get("CONFIG","") == "":
            self.wrong_config["Autosubmit"] += [['CONFIG',"Mandatory AUTOSUBMIT section doesn't exists"]]
        else:
            if parser_data["CONFIG"].get('AUTOSUBMIT_VERSION',-1.1) == -1.1:
                self.wrong_config["Autosubmit"] += [['config',
                                                     "AUTOSUBMIT_VERSION parameter not found"]]
            if not refresh:

                if parser_data["CONFIG"].get('MAXWAITINGJOBS',-1) == -1:
                    self.wrong_config["Autosubmit"] += [['config',
                                                         "MAXWAITINGJOBS parameter not found or non-integer"]]
                if parser_data["CONFIG"].get('TOTALJOBS',-1) == -1:
                    self.wrong_config["Autosubmit"] += [['config',
                                                         "TOTALJOBS parameter not found or non-integer"]]
                #if parser_data["CONFIG"].get('SAFETYSLEEPTIME',-1) == -1:
                #    self.set_safetysleeptime(10)
                #else:
                #    self.set_safetysleeptime(int(parser_data["CONFIG"].get('SAFETYSLEEPTIME',10)))
                if type(parser_data["CONFIG"].get('RETRIALS',0)) != int:
                    parser_data["CONFIG"]['RETRIALS'] = int(parser_data["CONFIG"].get('RETRIALS',0))

        if parser_data.get("STORAGE",None) is None:
            parser_data["STORAGE"] = {}
        if parser_data["STORAGE"].get('TYPE',"pkl") not in ['pkl', 'db']:
            self.wrong_config["Autosubmit"] += [['storage',
                                                 "TYPE parameter not found"]]

        wrappers_info = parser_data.get("WRAPPERS",{})
        if wrappers_info:
            self.check_wrapper_conf(wrappers_info)
        if parser_data.get("MAIL","") != "":
            if str(parser_data["MAIL"].get("NOTIFICATIONS", "false")).lower() == "true":
                mails = parser_data["MAIL"].get("TO", "")
                if type(mails) == list:
                    pass
                elif "," in mails:
                    mails = mails.split(',')
                else:
                    mails = mails.split(' ')
                self.experiment_data["MAIL"]["TO"] = mails

                for mail in self.experiment_data["MAIL"]["TO"]:
                    if not self.is_valid_mail_address(mail):
                        self.wrong_config["Autosubmit"] += [['mail',
                                                             "invalid e-mail"]]
        if "Autosubmit" not in self.wrong_config:
            if not no_log:
                Log.result('{0} OK'.format(
                    os.path.basename(self._conf_parser_file)))
            return True
        else:
            return True
        return False

    def check_platforms_conf(self,no_log=False):
        """
        Checks experiment's platforms configuration file.

        """
        parser_data = self.experiment_data.get("PLATFORMS",{})
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
                    self.wrong_config["Platform"] += [[section,"Mandatory TYPE parameter not found"]]
                else:
                    platform_type = platform_type.lower()
                if platform_type != 'ps':
                    if not section_data.get('PROJECT', ""):
                        self.wrong_config["Platform"] += [[section,"Mandatory PROJECT parameter not found"]]
                    if not section_data.get('USER',""):
                        self.wrong_config["Platform"] += [[section,
                                                           "Mandatory USER parameter not found"]]
            if not section_data.get('HOST',""):
                self.wrong_config["Platform"] += [[section,"Mandatory HOST parameter not found"]]
            if not section_data.get('SCRATCH_DIR',""):
                self.wrong_config["Platform"] += [[section,
                                                   "Mandatory SCRATCH_DIR parameter not found"]]
        if not main_platform_found:
            self.wrong_config["Expdef"] += [["Default","Main platform is not defined! check if [HPCARCH = {0}] has any typo".format(self.hpcarch)]]
        if "Platform" not in self.wrong_config:
            if not no_log:
                Log.result('{0} OK'.format(
                    os.path.basename(self._platforms_parser_file)))
            return True
        return False

    def check_jobs_conf(self,no_log=False):
        """
        Checks experiment's jobs configuration file.
        :param no_log: if True, it doesn't print any log message
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        parser = self.experiment_data
        for section in parser.get("JOBS",{}):
            section_data=parser["JOBS"][section]
            section_file_path = section_data.get('FILE',"")
            if not section_file_path:
                self.wrong_config["Jobs"] += [[section,
                                               "Mandatory FILE parameter not found"]]
            else:
                try:
                    if self.ignore_file_path:
                        if not os.path.exists(os.path.join(self.get_project_dir(), section_file_path)):
                            check_value = str(section_data.get('CHECK',True)).lower()
                            if check_value != "false":
                                if check_value not in "on_submission":
                                    self.wrong_config["Jobs"] += [
                                        [section, "FILE {0} doesn't exist and check parameter is not set on_submission value".format(section_file_path)]]
                            else:
                                self.wrong_config["Jobs"] += [[section, "FILE {0} doesn't exist".format(
                                    os.path.join(self.get_project_dir(), section_file_path))]]
                except BaseException:
                    pass  # tests conflict quick-patch

            dependencies = section_data.get('DEPENDENCIES','')
            if dependencies != "":
                if type(dependencies) == dict:
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
                                [section, "Dependency parameter is invalid, job {0} is not configured".format(dependency)])
            rerun_dependencies = section_data.get('RERUN_DEPENDENCIES',"").upper()
            if rerun_dependencies:
                for dependency in rerun_dependencies.split(' '):
                    if '-' in dependency:
                        dependency = dependency.split('-')[0]
                    if '[' in dependency:
                        dependency = dependency[:dependency.find('[')]
                    if dependency not in parser["JOBS"].keys():
                        self.warn_config["Jobs"] += [
                            [section, "RERUN_DEPENDENCIES parameter is invalid, job {0} is not configured".format(dependency)]]
            running_type = section_data.get('RUNNING', "once").lower()
            if running_type not in ['once', 'date', 'member', 'chunk']:
                self.wrong_config["Jobs"] += [[section,
                                               "Mandatory RUNNING parameter is invalid"]]
        if "Jobs" not in self.wrong_config:
            if not no_log:
                Log.result('{0} OK'.format(os.path.basename(self._jobs_parser_file)))
            return True
        return False

    def check_expdef_conf(self,refresh=False,no_log=False):
        """
        Checks experiment's experiment configuration file.
        :param refresh: if True, it doesn't check the mandatory parameters
        :type refresh: bool
        :param no_log: if True, it doesn't print any log message
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        parser = self.experiment_data
        self.hpcarch = ""
        if parser.get('DEFAULT',"") == "":
            self.wrong_config["Expdef"] += [['DEFAULT',"Mandatory DEFAULT section doesn't exists"]]
        else:
            if not parser['DEFAULT'].get('EXPID',""):
                self.wrong_config["Expdef"] += [['DEFAULT',"Mandatory DEFAULT.EXPID parameter is invalid"]]

            self.hpcarch = parser['DEFAULT'].get('HPCARCH',"").upper()
            if not self.hpcarch:
                self.wrong_config["Expdef"] += [['DEFAULT',"Mandatory DEFAULT.HPCARCH parameter is invalid"]]
        if not refresh:

            if parser.get('EXPERIMENT',"") == "":
                self.wrong_config["Expdef"] += [['EXPERIMENT',"Mandatory EXPERIMENT section doesn't exists"]]
            else:
                if not parser['EXPERIMENT'].get('DATELIST',""):
                    self.wrong_config["Expdef"] += [['DEFAULT', "Mandatory EXPERIMENT.DATELIST parameter is invalid"]]
                if not parser['EXPERIMENT'].get('MEMBERS',""):
                    self.wrong_config["Expdef"] += [['DEFAULT',"Mandatory EXPERIMENT.MEMBERS parameter is invalid"]]
                if parser['EXPERIMENT'].get('CHUNKSIZEUNIT',"").lower() not in ['year', 'month', 'day', 'hour']:
                    self.wrong_config["Expdef"] += [['experiment',"Mandatory EXPERIMENT.CHUNKSIZEUNIT choice is invalid"]]
                if type(parser['EXPERIMENT'].get('CHUNKSIZE',"-1")) not in [int]:
                    if parser['EXPERIMENT']['CHUNKSIZE'] == "-1":
                        self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.CHUNKSIZE is not defined"]]
                    parser['EXPERIMENT']['CHUNKSIZE'] = int(parser['EXPERIMENT']['CHUNKSIZE'])
                if type(parser['EXPERIMENT'].get('NUMCHUNKS',"-1")) not in [int]:
                    if parser['EXPERIMENT']['NUMCHUNKS'] == "-1":
                        self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.NUMCHUNKS is not defined"]]
                    parser['EXPERIMENT']['NUMCHUNKS'] = int(parser['EXPERIMENT']['NUMCHUNKS'])
                if parser['EXPERIMENT'].get('CALENDAR',"").lower() not in ['standard','noleap']:
                    self.wrong_config["Expdef"] += [['experiment', "Mandatory EXPERIMENT.CALENDAR choice is invalid"]]
        if parser.get('PROJECT',"") == "":
            self.wrong_config["Expdef"] += [['PROJECT',"Mandatory PROJECT section doesn't exists"]]
            project_type = ""
        else:
            project_type = parser['PROJECT'].get('PROJECT_TYPE',"")
        if project_type.lower() not in ['none', 'git', 'svn', 'local']:
            self.wrong_config["PROJECT"] += [['PROJECT_TYPE', "Mandatory PROJECT_TYPE choice is invalid"]]
        else:
            if project_type == 'git':
                if parser.get('GIT', "") == "":
                    self.wrong_config["Expdef"] += [['GIT',"Mandatory GIT section doesn't exists"]]
                else:
                    if not parser['GIT'].get('PROJECT_ORIGIN',""):
                        self.wrong_config["Expdef"] += [['git',
                                                         "PROJECT_ORIGIN parameter is invalid"]]
                    if not parser['GIT'].get('PROJECT_BRANCH',""):
                        self.wrong_config["Expdef"] += [['git',
                                                         "PROJECT_BRANCH parameter is invalid"]]

            elif project_type == 'svn':
                if parser.get('SVN', "") == "":
                    self.wrong_config["Expdef"] += [['SVN',"Mandatory SVN section doesn't exists"]]
                else:
                    if not parser['SVN'].get('PROJECT_URL',""):
                        self.wrong_config["Expdef"] += [['svn',
                                                         "PROJECT_URL parameter is invalid"]]
                    if not parser['SVN'].get('PROJECT_REVISION',""):
                        self.wrong_config["Expdef"] += [['svn',
                                                         "PROJECT_REVISION parameter is invalid"]]
            elif project_type == 'local':
                if parser.get('LOCAL', "") == "":
                    self.wrong_config["Expdef"] += [['LOCAL',"Mandatory LOCAL section doesn't exists"]]
                else:

                    if not parser['LOCAL'].get('PROJECT_PATH',""):
                        self.wrong_config["Expdef"] += [['local',
                                                         "PROJECT_PATH parameter is invalid"]]
            elif project_type == 'none':  # debug propouses
                self.ignore_file_path = False
        if "Expdef" not in self.wrong_config:
            if not no_log:
                Log.result('{0} OK'.format(
                    os.path.basename(self._exp_parser_file)))
            return True
        return False

    def check_proj(self,no_log=False):
        """
        Checks project config file
        :no_log if True, it doesn't print any log message
        :type no_log: bool
        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        try:
            if not self._proj_parser_file:
                self._proj_parser = None
                return True
            else:
                self._proj_parser = AutosubmitConfig.get_parser(
                    self.parser_factory, self._proj_parser_file)
            return True
        except Exception as e:
            self.wrong_config["Proj"] += [['project_files',
                                           "FILE_PROJECT_CONF parameter is invalid"]]
            return False

    def check_wrapper_conf(self,wrappers=dict(),no_log=False):
        """
        Checks wrapper config file

        :param wrappers:
        :param no_log:
        :return:
        """
        for wrapper_name,wrapper_values in wrappers.items():
            #continue if it is a global option (non-dicT)
            if type(wrapper_values) is not dict:
                continue

            jobs_in_wrapper = wrapper_values.get('JOBS_IN_WRAPPER',"")
            if "&" in jobs_in_wrapper:
                jobs_in_wrapper = jobs_in_wrapper.split("&")
            else:
                jobs_in_wrapper = jobs_in_wrapper.split(" ")
            for section in jobs_in_wrapper:
                platform_name = self.jobs_data[section].get('PLATFORM',"").upper()
                if platform_name == "":
                    platform_name = self.get_platform().upper()
                if platform_name == "LOCAL":
                    continue
                if not self.is_valid_jobs_in_wrapper(wrapper_values):
                    self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                      "JOBS_IN_WRAPPER contains non-defined jobs.  parameter is invalid"]]
                if 'horizontal' in self.get_wrapper_type(wrapper_values):
                    if not self.experiment_data["PLATFORMS"][platform_name].get('PROCESSORS_PER_NODE',"1"):
                        self.wrong_config["WRAPPERS"] += [
                            [wrapper_name, "PROCESSORS_PER_NODE no exist in the horizontal-wrapper platform"]]
                    if not self.experiment_data["PLATFORMS"][platform_name].get('MAX_PROCESSORS',""):
                        self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                          "MAX_PROCESSORS no exist in the horizontal-wrapper platform"]]
                if 'vertical' in self.get_wrapper_type(wrapper_values):
                    if not self.experiment_data["PLATFORMS"][platform_name].get('MAX_WALLCLOCK',""):
                        self.wrong_config["WRAPPERS"] += [[wrapper_name,
                                                          "MAX_WALLCLOCK no exist in the vertical-wrapper platform"]]
            if "WRAPPERS" not in self.wrong_config:
                if not no_log:
                    Log.result('wrappers OK')
                return True
    def file_modified(self,file,prev_mod_time):
        '''
        Function to check if a file has been modified.
        :param file: path
        :return: bool,new_time
        '''
        modified = False
        file_mod_time = datetime.fromtimestamp(file.lstat().st_mtime)  # This is a datetime.datetime object!

        max_delay = timedelta(seconds=1)

        if prev_mod_time is None or prev_mod_time - file_mod_time > max_delay:
            modified = True
        else:
            modified = False
        return modified,file_mod_time
    def reload(self,first_load=False):
        """
        Creates parser objects for configuration files
        """
        any_file_changed = False
        modified = False
        # check if original_files has been edited
        for config_file in range(0,len(self._original_parser_files)):
            try:
                if self._original_parser_files[config_file].name != self._proj_parser_file.name and self._original_parser_files[config_file].exists():
                    modified, self._original_parser_files_modtime[config_file] = self.file_modified(self._original_parser_files[config_file], self._original_parser_files_modtime[config_file])
                else:
                    if self._proj_parser_file.exists():
                        modified, self._original_parser_files_modtime[config_file] = self.file_modified(
                            self._original_parser_files[config_file], self._original_parser_files_modtime[config_file])
                if modified:
                    any_file_changed = True
            except:
                #Doesn't exists
                pass
        # check if custom_files has been edited
        for config_file in range(0,len(self._custom_parser_files)):
            modified,self._custom_parser_files_modtime[config_file] = self.file_modified(self._custom_parser_files[config_file],self._custom_parser_files_modtime[config_file])
            if modified:
                any_file_changed = True

        if any_file_changed or first_load:
            try:
                self._conf_parser = AutosubmitConfig.get_parser(
                    self.parser_factory, self._conf_parser_file)
                self._platforms_parser = AutosubmitConfig.get_parser(
                    self.parser_factory, self._platforms_parser_file)

                self._jobs_parser = AutosubmitConfig.get_parser(
                    self.parser_factory, self._jobs_parser_file)
                self._exp_parser = AutosubmitConfig.get_parser(
                    self.parser_factory, self._exp_parser_file)
                if first_load:
                    self._custom_parser = []
                    if self._exp_parser.data is not None and len(self._exp_parser.data) > 0:
                        self._exp_parser.data = self.deep_normalize(self._exp_parser.data)
                    else:
                        self._exp_parser.data = {}
                    if self._conf_parser.data is not None and len(self._conf_parser.data) > 0:
                        self._conf_parser.data = self.deep_normalize(self._conf_parser.data)
                    else:
                        self._conf_parser.data = {}
                    if self._jobs_parser.data is not None and len(self._jobs_parser.data) > 0:
                        self._jobs_parser.data = self.deep_normalize(self._jobs_parser.data)
                    else:
                        self._jobs_parser.data = {}
                    if self._platforms_parser.data is not None and len(self._platforms_parser.data) > 0:
                        self._platforms_parser.data = self.deep_normalize(self._platforms_parser.data)
                    else:
                        self._platforms_parser.data = {}
                    default_section = self._exp_parser.data.get("DEFAULT",None)
                    default_path = Path(self.basic_config.LOCAL_ROOT_DIR) / self.expid
                    custom_folder_path = default_path / "conf" / "custom_conf"
                    if not custom_folder_path.exists():
                        try:
                            os.mkdir(custom_folder_path)
                            os.chmod(custom_folder_path, 0o770)
                        except:
                            pass
                    if default_section is not None and len(str(default_section)) > 0:
                        default_section["CUSTOM_CONFIG"] = default_section.get("CUSTOM_CONFIG",str(custom_folder_path))
                        custom_config = re.sub('%(?<!%%)' + "ROOTDIR" + '%(?!%%)', str(default_path), default_section["CUSTOM_CONFIG"], flags=re.I)
                    else:
                        custom_config = str(default_path / "conf" / "custom_conf")
                    self._custom_parser_files = []
                    self._custom_parser_files_modtime = []
                    # Parse folder. Should always exists as first item.
                    if ',' in custom_config:
                        custom_config = custom_config.split(',')
                    elif ' ' in custom_config:
                        custom_config = custom_config.split(' ')
                    else:
                        custom_config = [custom_config]
                    custom_folder_path = [x for x in Path(custom_config[0]).rglob("*.yml") ] + [x for x in Path(custom_config[0]).rglob("*.yaml") ]
                    if len(custom_config) > 1:
                        custom_folder_path.extend([Path(x) for x in custom_config[1:] ])
                    for f in custom_folder_path:
                        if not (self._proj_parser_file.exists() and f.samefile(self._proj_parser_file)) \
                                and not (self._jobs_parser_file.exists() and f.samefile(self._jobs_parser_file)) \
                                and not (self._platforms_parser_file.exists() and f.samefile(self._platforms_parser_file)) \
                                and not (self._exp_parser_file.exists() and f.samefile(self._exp_parser_file)) \
                                and not (self._conf_parser_file.exists() and f.samefile(self._conf_parser_file)):
                            self._custom_parser_files.append(f)
                            self._custom_parser_files_modtime.append(None)

                for custom_file in self._custom_parser_files:
                    self._custom_parser.append(AutosubmitConfig.get_parser(
                    self.parser_factory, custom_file))
            except IOError as e:
                raise AutosubmitError("IO issues during the parsing of configuration files",6014,str(e))
            except Exception as e:
                raise AutosubmitCritical(
                    "{0}\nCheck configuration indentation or look for repeated parameter\nCheck if you have any uncommented value that should be commented".format(str(e)), 7014)
            try:
                if not self._proj_parser_file:
                    self._proj_parser = None
                else:
                    self._proj_parser = AutosubmitConfig.get_parser(
                        self.parser_factory, self._proj_parser_file)

            except IOError as e:
                raise AutosubmitError("IO issues during the parsing of configuration files",6014,str(e))
            self.unify_conf()
    def deep_get_long_key(self,section_data,long_key):
        parameters_dict = dict()
        for key, val in section_data.items():
            if isinstance(val, collections.abc.Mapping ):
                parameters_dict.update(self.deep_get_long_key(section_data.get(key, {}),long_key+"."+key))
            else:
                parameters_dict[long_key+"."+key] = val
        return parameters_dict
    def deep_parameters_export(self,data):
        """
        Export all variables of this experiment.
        Resultant format will be Section.{subsections1...subsectionN} = Value.
        In other words, it plain the dictionary into one level
        """
        parameters_dict =  dict()
        for key in data.keys():
            parameters_dict.update(self.deep_get_long_key(data.get(key, {}),key))
        return parameters_dict

    def load_parameters(self):
        """
        Load all experiment data
        :return: a dictionary containing tuples [parameter_name, parameter_value]
        :rtype: dict
        """
        self.parameters = self.deep_parameters_export(self.experiment_data)
        return self.parameters

    def load_platform_parameters(self):
        """
        Load parameters from platform config files.

        :return: a dictionary containing tuples [parameter_name, parameter_value]
        :rtype: dict
        """
        parameters = dict()
        for section in self._platforms_parser.sections():
            for option in self._platforms_parser.options(section):
                parameters[section + "_" +
                           option] = self._platforms_parser.get(section, option)
        return parameters

    def load_section_parameters(self, job_list, as_conf, submitter):
        """
        Load parameters from job config files.

        :return: a dictionary containing tuples [parameter_name, parameter_value]
        :rtype: dict
        """
        as_conf.check_conf_files(False)

        job_list_by_section = defaultdict()
        parameters = defaultdict()
        for job in job_list.get_job_list():
            if not job.platform_name:
                job.platform_name = self.hpcarch
            if job.section not in list(job_list_by_section.keys()):
                job_list_by_section[job.section] = [job]
            else:
                job_list_by_section[job.section].append(job)
            try:
                job.platform = submitter.platforms[job.platform_name]
            except:
                job.platform = submitter.platforms["LOCAL"]

        for section in list(job_list_by_section.keys()):
            job_list_by_section[section][0].update_parameters(
                as_conf, job_list.parameters)
            section_list = list(job_list_by_section[section][0].parameters.keys())
            for section_param in section_list:
                if section_param not in list(job_list.parameters.keys()):
                    parameters[section + "_" +
                               section_param] = job_list_by_section[section][0].parameters[section_param]
        return parameters

    def set_expid(self, exp_id):
        """
        Set experiment identifier in autosubmit and experiment config files

        :param exp_id: experiment identifier to store
        :type exp_id: str
        """
        # Experiment conf
        content = open(self._exp_parser_file).read()
        if re.search('EXPID:.*', content):
            content = content.replace(
                re.search('EXPID:.*', content).group(0), "EXPID: " + exp_id)
        open(self._exp_parser_file, 'w').write(content)

        content = open(self._conf_parser_file).read()
        if re.search('EXPID:.*', content):
            content = content.replace(
                re.search('EXPID:.*', content).group(0), "EXPID: " + exp_id)
        open(self._conf_parser_file, 'w').write(content)

    def get_project_type(self):
        """
        Returns project type from experiment config file

        :return: project type
        :rtype: str
        """
        return self.get_section(["project", "project_type"],must_exists=False).lower()


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

        return self.get_section(['RERUN', 'RERUN_JOBLIST'], "")

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

    def get_submodules_list(self):
        """
        Returns submodules list from experiment's config file
        Default is --recursive
        :return: submodules to load
        :rtype: list
        """
        return self.get_section(['GIT', 'PROJECT_SUBMODULES'], "").split(" ")

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
            value = self.get_section(['PROJECT', 'PROJECT_DESTINATION'])
            if not value:
                if self.get_project_type().lower() == "local":
                    value = os.path.split(self.get_local_project_path())[1]
                elif self.get_project_type().lower() == "svn":
                    value = self.get_svn_project_url().split('/')[-1]
                elif self.get_project_type().lower() == "git":
                    value = self.experiment_data.get("GIT",{}).get("PROJECT_ORIGIN","").split('/')[-1]
                    if "." in value:
                        value=value.split('.')[-2]

            if value != "":
                return value
            else:
                return "project_files"
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
        date_value = str(self.get_section(['EXPERIMENT', 'DATELIST'],"20220401"))
        # Allows to use the old format for define a list.
        if type(date_value) is not list:
            if not date_value.startswith("["):
                string = '[{0}]'.format(date_value)
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

    def get_chunk_size(self, default=1):
        """
        Chunk Size as defined in the expdef file.

        :return: Chunksize, 1 as default.
        :rtype: int
        """
        chunk_size = self.get_section(
            ['experiment', 'CHUNKSIZE'], default)
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
        string = str(self.get_section(['EXPERIMENT', 'MEMBERS'],"") if run_only == False else self.get_section(
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
    def get_dependencies(self, section="None"):
        """
        Returns dependencies list from jobs config file

        :return: experiment's members
        :rtype: list
        """
        try:
            return self.get_section([section, "DEPENDENCIES"], "")
        except:
            return []

        if section is not None and len(str(section)) > 0:
            return member_list
        else:
            return None

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

    def set_platform(self, hpc):
        """
        Sets main platforms in experiment's config file

        :param hpc: main platforms
        :type: str
        """
        content = open(self._exp_parser_file).read()
        if re.search('HPCARCH:.*', content):
            content = content.replace(
                re.search('HPCARCH:.*', content).group(0), "HPCARCH: " + hpc)
        open(self._exp_parser_file, 'w').write(content)

    def set_version(self, autosubmit_version):
        """
        Sets autosubmit's version in autosubmit's config file

        :param autosubmit_version: autosubmit's version
        :type autosubmit_version: str
        """
        try:
            content = open(self._conf_parser_file, 'r').read()
            if re.search('AUTOSUBMIT_VERSION:.*', content):
                content = content.replace(re.search('AUTOSUBMIT_VERSION:.*', content).group(0),"AUTOSUBMIT_VERSION: {0}".format(autosubmit_version) )
        except:
            content = "CONFIG:\n  AUTOSUBMIT_VERSION: " + autosubmit_version + "\n"
        open(self._conf_parser_file, 'w').write(content)
        os.chmod(self._conf_parser_file, 0o755)

    def get_version(self):
        """
        Returns version number of the current experiment from autosubmit's config file

        :return: version
        :rtype: str
        """
        return str(self.get_section(['CONFIG', 'AUTOSUBMIT_VERSION'], ""))

    def get_total_jobs(self):
        """
        Returns max number of running jobs  from autosubmit's config file

        :return: max number of running jobs
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'TOTALJOBS'],-1))

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

    def get_disable_recovery_threads(self, section):
        """
        Returns FALSE/TRUE
        :return: recovery_threads_option
        :rtype: str
        """
        if self.platforms_data.get(section,"false") != "false":
            return self.platforms_data[section].get('DISABLE_RECOVERY_THREADS',"false").lower()
        else:
            return "false"
    def get_max_processors(self):
        """
        Returns max processors from autosubmit's config file

        :rtype: str
        """
        return self.get_section(['CONFIG', 'MAX_PROCESSORS'], -1)

    def get_max_waiting_jobs(self):
        """
        Returns max number of waiting jobs from autosubmit's config file

        :return: main platforms
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'MAXWAITINGJOBS'],-1))

    def get_default_job_type(self):
        """
        Returns the default job type from experiment's config file

        :return: default type such as bash, python, r...
        :rtype: str
        """
        return self.get_section(['PROJECT_FILES', 'JOB_SCRIPTS_TYPE'], 'bash')

    def get_safetysleeptime(self):
        """
        Returns safety sleep time from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        return int(self.get_section(['CONFIG', 'SAFETYSLEEPTIME'], 10))

    def set_safetysleeptime(self, sleep_time):
        """
        Sets autosubmit's version in autosubmit's config file

        :param sleep_time: value to set
        :type sleep_time: int
        """
        content = open(self._conf_parser_file).read()
        content = content.replace(re.search('SAFETYSLEEPTIME:.*', content).group(0),"SAFETYSLEEPTIME: %d" % sleep_time)
        open(self._conf_parser_file, 'w').write(content)

    def get_retrials(self):
        """
        Returns max number of retrials for job from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        return self.get_section(['CONFIG', 'RETRIALS'],0)

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
    def ini_to_yaml(root_dir,ini_file):
        # Based on http://stackoverflow.com/a/3233356
        def update_dict(original_dict, updated_dict):
            for k, v in updated_dict.items():
                if isinstance(v, collections.Mapping):
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

        content = open(input_file,'r',encoding=locale.getlocale()[1]).read()
        regex = r"\=( )*\[[\[\]\'_0-9.\"#A-Za-z \-,]*\]"

        matches = re.finditer(regex, content)

        for matchNum, match in enumerate(matches, start=1):
            print(match.group())
            subs_string = "= "+"\""+match.group()[2:]+"\""
            regex_sub = match.group()
            content = re.sub(re.escape(regex_sub),subs_string, content)

        open(input_file,'w',encoding=locale.getlocale()[1]).write(content)
        config_dict = ConfigObj(input_file,stringify=True,list_values=False,interpolation=False,unrepr=False )


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
        yaml_file = open(input_file, 'w',encoding=locale.getlocale()[1])
        yaml.dump(final_dict, yaml_file, Dumper=yaml.RoundTripDumper)
        ini_file.rename(Path(root_dir, ini_file.stem+".yml"))
    def get_notifications_crash(self):
        """
        Returns if the user has enabled the notifications from autosubmit's config file

        :return: if notifications
        :rtype: string
        """
        return self.get_section(['MAIL', 'NOTIFY_ON_REMOTE_FAIL'], True)
    def get_remote_dependencies(self):
        """
        Returns if the user has enabled the PRESUBMISSION configuration parameter from autosubmit's config file

        :return: if remote dependencies
        :rtype: string
        """
        # Disabled, forced to "false" not working anymore in newer slurm versions.
        return "false"
        #return str(self.get_section(['CONFIG', 'PRESUBMISSION'], "false")).lower()

    def get_wrapper_type(self, wrapper={}):
        """
        Returns what kind of wrapper (VERTICAL, MIXED-VERTICAL, HORIZONTAL, HYBRID, MULTI NONE) the user has configured in the autosubmit's config

        :return: wrapper type (or none)
        :rtype: string
        """
        if len(wrapper) > 0 :
            return wrapper.get('TYPE',self.experiment_data["WRAPPERS"].get("TYPE",""))
        else:
            return None


    def get_wrapper_retrials(self, wrapper={}):
        """
        Returns max number of retrials for job from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        #todo
        return wrapper.get('INNER_RETRIALS', self.experiment_data["WRAPPERS"].get("INNER_RETRIALS",0))

    def get_wrapper_policy(self, wrapper={}):
        """
        Returns what kind of policy (flexible, strict, mixed ) the user has configured in the autosubmit's config

        :return: wrapper type (or none)
        :rtype: string
        """
        return wrapper.get( 'POLICY', self.experiment_data["WRAPPERS"].get("POLICY",'flexible'))

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
        aux = wrapper.get('JOBS_IN_WRAPPER', self.experiment_data["WRAPPERS"].get("JOBS_IN_WRAPPER",""))
        aux = aux.split()
        aux = [x.split("&") for x in aux]
        jobs_in_wrapper = []
        for section_list in aux:
            for section in section_list:
                jobs_in_wrapper.append(section)

        return jobs_in_wrapper
    def get_extensible_wallclock(self, wrapper={}):
        """
        Gets extend_wallclock for the given wrapper

        :param wrapper: wrapper
        :type wrapper: dict
        :return: extend_wallclock
        :rtype: int
        """
        return int(wrapper.get('EXTEND_WALLCLOCK', 0))

    def get_x11_jobs(self):
        """
        Returns the jobs that should support x11, configured in the autosubmit's config

        :return: expression (or none)
        :rtype: string
        """
        return str(self.get_section(['CONFIG', 'X11_JOBS'], "false")).lower()

    def get_wrapper_queue(self, wrapper={}):
        """
        Returns the wrapper queue if not defined, will be the one of the first job wrapped

        :return: expression (or none)
        :rtype: string
        """
        return wrapper.get( 'QUEUE', self.experiment_data["WRAPPERS"].get("QUEUE",""))
    def get_wrapper_partition(self, wrapper={}):
        """
        Returns the wrapper queue if not defined, will be the one of the first job wrapped

        :return: expression (or none)
        :rtype: string
        """
        return wrapper.get( 'PARTITION', self.experiment_data["WRAPPERS"].get("PARTITION",""))
    def get_min_wrapped_jobs(self, wrapper={}):
        """
         Returns the minium number of jobs that can be wrapped together as configured in autosubmit's config file

        :return: minim number of jobs (or total jobs)
        :rtype: int
        """
        return wrapper.get('MIN_WRAPPED', 2)

    def get_max_wrapped_jobs(self, wrapper={}):
        """
         Returns the maximum number of jobs that can be wrapped together as configured in autosubmit's config file

         :return: maximum number of jobs (or total jobs)
         :rtype: int
         """
        return wrapper.get( 'MAX_WRAPPED', 999999999)

    def get_max_wrapped_jobs_vertical(self, wrapper={}):
        """
         Returns the maximum number of jobs that can be wrapped together as configured in autosubmit's config file

         :return: maximum number of jobs (or total jobs)
         :rtype: int
         """

        return int(wrapper.get('MAX_WRAPPED_V', -1))

    def get_max_wrapped_jobs_horizontal(self, wrapper={}):
        """
         Returns the maximum number of jobs that can be wrapped together as configured in autosubmit's config file

         :return: maximum number of jobs (or total jobs)
         :rtype: int
         """
        return int(self.get_section('MAX_WRAPPED_H', -1))

    def get_min_wrapped_jobs_vertical(self, wrapper={}):
        """
         Returns the maximum number of jobs that can be wrapped together as configured in autosubmit's config file

         :return: maximum number of jobs (or total jobs)
         :rtype: int
         """
        return int(self.get_section('MIN_WRAPPED_V', 1))

    def get_min_wrapped_jobs_horizontal(self, wrapper={}):
        """
         Returns the maximum number of jobs that can be wrapped together as configured in autosubmit's config file

         :return: maximum number of jobs (or total jobs)
         :rtype: int
         """
        return int(wrapper.get('MIN_WRAPPED_H', 1))

    def get_wrapper_method(self, wrapper={}):
        """
         Returns the method of make the wrapper

         :return: method
         :rtype: string
         """
        return wrapper.get('METHOD', self.experiment_data["WRAPPERS"].get("METHOD",'ASThread'))

    def get_wrapper_check_time(self):
        """
         Returns time to check the status of jobs in the wrapper

         :return: wrapper check time
         :rtype: int
         """
        wrapper = self.experiment_data.get("WRAPPERS", {})

        return wrapper.get("CHECK_TIME_WRAPPER",self.get_safetysleeptime())

    def get_wrapper_machinefiles(self, wrapper={}):
        """
         Returns the strategy for creating the machinefiles in wrapper jobs

         :return: machinefiles function to use
         :rtype: string
         """
        return wrapper.get('MACHINEFILES', self.experiment_data["WRAPPERS"].get("MACHINEFILES",""))
    def get_export(self, section):
        """
        Gets command line for being submitted with
        :param section: job type
        :type section: str
        :return: wallclock time
        :rtype: str
        """
        return self.get_section([section, 'EXPORT'], "")


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
        return  self.get_section(['MAIL', 'TO'], "")

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

    @staticmethod
    def is_valid_mail_address(mail_address):
        if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', mail_address):
            return True
        else:
            return False

    def is_valid_communications_library(self):
        library = self.get_communications_library()
        return library in ['paramiko']

    def is_valid_storage_type(self):
        storage_type = self.get_storage_type()
        return storage_type in ['pkl', 'db']

    def is_valid_jobs_in_wrapper(self,wrapper={}):
        expression = self.get_wrapper_jobs(wrapper)
        jobs_data = self.experiment_data.get("JOBS",{}).keys()
        if expression is not None and len(str(expression)) > 0:
            for section in expression:
                if section not in jobs_data:
                    return False
        return True

    def is_valid_git_repository(self):
        origin_exists = str(self.experiment_data["GIT"].get('PROJECT_ORIGIN',""))
        branch = self.get_git_project_branch()
        commit = self.get_git_project_commit()
        return origin_exists and ( (branch is not None and len(str(branch)) > 0) or ( commit is not None and len(str(commit)) > 0))

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
                matches = re.findall('%(?<!%%)\w+%(?!%%)', content)
                for match in matches:
                    # replace all '%(?<!%%)\w+%(?!%%)' with parameters value
                    content = content.replace(match, parameters.get(match[1:-1], ""))
                with open(f_name, 'w') as f:
                    f.write(content)
                    os.chmod(f_name, 0o750)
        pass
    @staticmethod
    def get_parser(parser_factory, file_path):
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
            #else:
                #Log.warning( "{0} was not found. Some variables might be missing. If your experiment does not need a proj file, you can ignore this message.", file_path)
        else:
            # This block may rise an exception but all its callers handle it
            try:
                with open(file_path) as f:
                    parser.data = parser.load(f)
                    if parser.data is None:
                        parser.data = {}
            except IOError as exp:
                parser.data = {}
                return parser
            except Exception as exp:
                raise Exception(
                    "{}\n This file and the correctness of its content are necessary.".format(str(exp)))
        return parser


    @staticmethod
    def parse_placeholders(content, parameters):
        """
        Parse placeholders in content

        :param content: content to be parsed
        :type content: str
        :param parameters: parameters to be used in parsing
        :type parameters: dict
        :return: parsed content
        :rtype: str
        """
        matches = re.findall('%(?<!%%)[a-zA-Z0-9_.]+%(?!%%)', content,flags=re.I)
        for match in matches:
            # replace all '%(?<!%%)\w+%(?!%%)' with parameters value
            content = content.replace(match, parameters.get(match[1:-1], ""))
        return content

