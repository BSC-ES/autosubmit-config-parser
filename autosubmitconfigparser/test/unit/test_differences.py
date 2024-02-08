from autosubmitconfigparser.config.configcommon import AutosubmitConfig, BasicConfig, YAMLParserFactory
from mock import Mock, MagicMock
from mock import patch
from unittest import TestCase
import inspect
from pathlib import Path


class FakeBasicConfig:
    def __init__(self):
        pass

    def props(self):
        pr = {}
        for name in dir(self):
            value = getattr(self, name)
            if not name.startswith('__') and not inspect.ismethod(value) and not inspect.isfunction(value):
                pr[name] = value
        return pr

    DB_DIR = '/dummy/db/dir'
    DB_FILE = '/dummy/db/file'
    DB_PATH = '/dummy/db/path'
    LOCAL_ROOT_DIR = '/dummy/local/root/dir'
    LOCAL_TMP_DIR = '/dummy/local/temp/dir'
    LOCAL_PROJ_DIR = '/dummy/local/proj/dir'
    DEFAULT_PLATFORMS_CONF = ''
    DEFAULT_JOBS_CONF = ''


class TestConfig(TestCase):

    def setUp(self):
        self.as_conf_small = None
        self.as_conf_complete = None
        self.experiment_id = 'random-id'
        self._wrapper_factory = MagicMock()
        self.config = FakeBasicConfig
        self.config.read = MagicMock()
        with patch.object(Path, 'exists') as mock_exists:
            mock_exists.return_value = True
            self.as_conf_complete = AutosubmitConfig(self.experiment_id, self.config, YAMLParserFactory())
            self.as_conf_small = AutosubmitConfig(self.experiment_id, self.config, YAMLParserFactory())
        self.as_conf_complete.experiment_data = {'CONFIG': {'AUTOSUBMIT_VERSION': '4.1.0', 'MAXWAITINGJOBS': 2, 'TOTALJOBS': 2, 'SAFETYSLEEPTIME': 10,
                    'RETRIALS': 0}, 'MAIL': {'NOTIFICATIONS': False, 'TO': None},
         'STORAGE': {'TYPE': 'pkl', 'COPY_REMOTE_LOGS': True}, 'DEFAULT': {'EXPID': 'a02j', 'HPCARCH': 'marenostrum4'},
         'EXPERIMENT': {'DATELIST': '20000101', 'MEMBERS': 'fc0', 'CHUNKSIZEUNIT': 'month', 'CHUNKSIZE': '4',
                        'NUMCHUNKS': '2', 'CHUNKINI': '', 'CALENDAR': 'standard'},
         'PROJECT': {'PROJECT_TYPE': 'none', 'PROJECT_DESTINATION': ''},
         'GIT': {'PROJECT_ORIGIN': '', 'PROJECT_BRANCH': '', 'PROJECT_COMMIT': '', 'PROJECT_SUBMODULES': '',
                 'FETCH_SINGLE_BRANCH': True}, 'SVN': {'PROJECT_URL': '', 'PROJECT_REVISION': ''},
         'LOCAL': {'PROJECT_PATH': ''},
         'PROJECT_FILES': {'FILE_PROJECT_CONF': '', 'FILE_JOBS_CONF': '', 'JOB_SCRIPTS_TYPE': ''},
         'RERUN': {'RERUN': False, 'RERUN_JOBLIST': ''}, 'JOBS': {'DN': {
            'DEPENDENCIES': {'DN': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': 'previous'}}}, 'SIM': {'STATUS': 'RUNNING'}},
            'FILE': 'templates/dn.sh', 'PLATFORM': 'marenostrum4-login', 'RUNNING': 'chunk', 'SPLITS': 31,
            'WALLCLOCK': '00:15', 'ADDITIONAL_FILES': ['conf/mother_request.yml']},
                                                                  'INI': {'DEPENDENCIES': {'REMOTE_SETUP': {}},
                                                                          'FILE': 'templates/ini.sh',
                                                                          'PLATFORM': 'marenostrum4-login',
                                                                          'RUNNING': 'member', 'WALLCLOCK': '00:30',
                                                                          'ADDITIONAL_FILES': []},
                                                                  'LOCAL_SETUP': {'FILE': 'templates/local_setup.sh',
                                                                                  'PLATFORM': 'LOCAL',
                                                                                  'RUNNING': 'once', 'DEPENDENCIES': {},
                                                                                  'ADDITIONAL_FILES': []},
                                                                  'REMOTE_SETUP': {'DEPENDENCIES': {'SYNCHRONIZE': {}},
                                                                                   'FILE': 'templates/remote_setup.sh',
                                                                                   'PLATFORM': 'marenostrum4-login',
                                                                                   'RUNNING': 'once',
                                                                                   'WALLCLOCK': '02:00',
                                                                                   'ADDITIONAL_FILES': [
                                                                                       'templates/fdb/confignative.yaml',
                                                                                       'templates/fdb/configregularll.yaml',
                                                                                       'templates/fdb/confighealpix.yaml']},
                                                                  'SIM': {'DEPENDENCIES': {'INI': {}, 'SIM-1': {}},
                                                                          'FILE': '<to-be-replaced-by-user-conf>',
                                                                          'PLATFORM': 'marenostrum4',
                                                                          'WALLCLOCK': '00:30', 'RUNNING': 'chunk',
                                                                          'ADDITIONAL_FILES': []},
                                                                  'SYNCHRONIZE': {'DEPENDENCIES': {'LOCAL_SETUP': {}},
                                                                                  'FILE': 'templates/synchronize.sh',
                                                                                  'PLATFORM': 'LOCAL',
                                                                                  'RUNNING': 'once',
                                                                                  'ADDITIONAL_FILES': []}, 'APP_MHM': {
                'DEPENDENCIES': {'OPA_MHM_1': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': '[1:31]*\\1'}}},
                                 'OPA_MHM_2': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': '[1:31]*\\1'}}}},
                'FILE': 'templates/application.sh', 'PLATFORM': 'marenostrum4', 'RUNNING': 'chunk',
                'WALLCLOCK': '00:05', 'SPLITS': '31', 'ADDITIONAL_FILES': ['templates/only_lra.yaml']}, 'APP_URBAN': {
                'DEPENDENCIES': {'OPA_URBAN_1': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': '[1:31]*\\1'}}}},
                'FILE': 'templates/application.sh', 'PLATFORM': 'marenostrum4', 'RUNNING': 'chunk',
                'WALLCLOCK': '00:05', 'SPLITS': '31', 'ADDITIONAL_FILES': ['templates/only_lra.yaml']}, 'OPA_MHM_1': {
                'DEPENDENCIES': {'DN': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': '[1:31]*\\1'}}},
                                 'OPA_MHM_1': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': 'previous'}}}},
                'FILE': 'templates/opa.sh', 'PLATFORM': 'marenostrum4', 'RUNNING': 'chunk', 'SPLITS': '31',
                'ADDITIONAL_FILES': []}, 'OPA_MHM_2': {
                'DEPENDENCIES': {'DN': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': '[1:31]*\\1'}}},
                                 'OPA_MHM_2': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': 'previous'}}}},
                'FILE': 'templates/opa.sh', 'PLATFORM': 'marenostrum4', 'RUNNING': 'chunk', 'SPLITS': '31',
                'ADDITIONAL_FILES': []}, 'OPA_URBAN_1': {
                'DEPENDENCIES': {'DN': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': '[1:31]*\\1'}}},
                                 'OPA_URBAN_1': {'SPLITS_FROM': {'ALL': {'SPLITS_TO': 'previous'}}}},
                'FILE': 'templates/opa.sh', 'PLATFORM': 'marenostrum4', 'RUNNING': 'chunk', 'SPLITS': '31',
                'ADDITIONAL_FILES': []}},
         'RUN': {'APP_NAMES': ['MHM', 'URBAN'], 'OPA_NAMES': ['mhm_1', 'mhm_2', 'urban_1']},
         'WRAPPERS': {'POLICY': 'mixed', 'MIN_WRAPPED': 6, 'MAX_WRAPPED': 6,
                      'WRAPPER': {'TYPE': 'horizontal', 'JOBS_IN_WRAPPER': 'OPA_URBAN_1 OPA_MHM_1 OPA_MHM_2'}},
         'RUN_NAMES_LIST': ['OPA_URBAN_1', 'OPA_MHM_1', 'OPA_MHM_2'], 'PLATFORMS': {
            'MARENOSTRUM4-LOGIN': {'TYPE': 'slurm', 'HOST': 'mn1.bsc.es', 'PROJECT': 'bsc32', 'USER': 'dbeltran',
                                   'QUEUE': 'debug', 'SCRATCH_DIR': '/gpfs/scratch', 'ADD_PROJECT_TO_HOST': False,
                                   'MAX_WALLCLOCK': '48:00', 'MAX_PROCESSORS': 99999},
            'MARENOSTRUM4': {'ADD_PROJECT_TO_HOST': False, 'BUDGET': 'project_465000454',
                             'CUSTOM_DIRECTIVES': "['#SBATCH --gpus-per-node=8', '#SBATCH --hint=nomultithread', '#SBATCH --exclusive', '#SBATCH --mem=0']",
                             'EXECUTABLE': '/bin/bash --login', 'FDB_DIR': '/scratch/project_465000454/experiments',
                             'HOST': 'lumi-cluster', 'HPC_PROJECT_DIR': '/projappl/project_465000454',
                             'MAX_PROCESSORS': 99999, 'MAX_WALLCLOCK': '48:00', 'NODES': 2, 'PARTITION': 'dev-g',
                             'PROCESSORS_PER_NODE': 64, 'PROJECT': 'project_465000454', 'SCRATCH_DIR': '/scratch',
                             'TASKS': 8, 'TEMP_DIR': '', 'THREADS': 7, 'TYPE': 'slurm', 'USER': 'francerou'},
            'MARENOSTRUM_ARCHIVE': {'TYPE': 'ps', 'HOST': 'dt02.bsc.es', 'PROJECT': 'bsc32', 'USER': None,
                                    'SCRATCH_DIR': '/gpfs/scratch', 'ADD_PROJECT_TO_HOST': False, 'TEST_SUITE': False},
            'TRANSFER_NODE': {'TYPE': 'ps', 'HOST': 'dt01.bsc.es', 'PROJECT': 'bsc32', 'USER': None,
                              'ADD_PROJECT_TO_HOST': False, 'SCRATCH_DIR': '/gpfs/scratch'},
            'TRANSFER_NODE_BSCEARTH000': {'TYPE': 'ps', 'HOST': 'bscearth000', 'USER': None, 'PROJECT': 'Earth',
                                          'ADD_PROJECT_TO_HOST': False, 'QUEUE': 'serial',
                                          'SCRATCH_DIR': '/esarchive/scratch'},
            'BSCEARTH000': {'TYPE': 'ps', 'HOST': 'bscearth000', 'USER': None, 'PROJECT': 'Earth',
                            'ADD_PROJECT_TO_HOST': False, 'QUEUE': 'serial', 'SCRATCH_DIR': '/esarchive/scratch'},
            'NORD3': {'TYPE': 'SLURM', 'HOST': 'nord1.bsc.es', 'PROJECT': 'bsc32', 'USER': None, 'QUEUE': 'debug',
                      'SCRATCH_DIR': '/gpfs/scratch', 'MAX_WALLCLOCK': '48:00'},
            'ECMWF-XC40': {'TYPE': 'ecaccess', 'VERSION': 'pbs', 'HOST': 'cca', 'USER': None, 'PROJECT': 'spesiccf',
                           'ADD_PROJECT_TO_HOST': False, 'SCRATCH_DIR': '/scratch/ms', 'QUEUE': 'np',
                           'SERIAL_QUEUE': 'ns', 'MAX_WALLCLOCK': '48:00'}},
         'ROOTDIR': '/home/dbeltran/new_autosubmit/a02j', 'PROJDIR': '/home/dbeltran/new_autosubmit/a02j/proj/'}

        self.as_conf_small.experiment_data = {'CONFIG': {'AUTOSUBMIT_VERSION': '4.1.0', 'MAXWAITINGJOBS': 2, 'TOTALJOBS': 2, 'SAFETYSLEEPTIME': 10, 'TEST': {'test_value': 1}} }

    def test_detailed_deep_diff(self):

        new_data = {'CONFIG': {'AUTOSUBMIT_VERSION': '4.1.0', 'MAXWAITINGJOBS': 2, 'TOTALJOBS': 2, 'SAFETYSLEEPTIME': 10, 'TEST': 1}}
        differences = self.as_conf_small.detailed_deep_diff(new_data, self.as_conf_small.experiment_data, {})
        self.assertEqual(differences, {'TEST': {'test_value': 1}} )