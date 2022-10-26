Simple library that allows to read the data of an Autosubmit experiment. 

## How to 

#.. code_block: python

from autosubmitconfigparser.config.yamlparser import YAMLParserFactory
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
from autosubmitconfigparser.config.basicconfig import BasicConfig

BasicConfig.read()
as_conf = AutosubmitConfig("a01y", BasicConfig, YAMLParserFactory())
as_conf.reload(True)

# Obtain all data
as_conf.experiment_data
# Obtain only section data
as_conf.jobs_data
# Obtain only platforms data
as_conf.platforms_data

