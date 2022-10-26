Simple library that allows to read the data of an Autosubmit experiment. 

Usage:

#imports
from autosubmitconfigparser.config.yamlparser import YAMLParserFactory
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
from autosubmitconfigparser.config.basicconfig import BasicConfig
# Read autosubmit.rc ( if any )
BasicConfig.read()
# Init parser where
expid = "a01y"
as_conf = AutosubmitConfig("a01y", BasicConfig, YAMLParserFactory())
as_conf.reload(True)

# Obtain all data
as_conf.experiment_data
# Obtain only section data
as_conf.jobs_data
# Obtain only platforms data
as_conf.platforms_data

