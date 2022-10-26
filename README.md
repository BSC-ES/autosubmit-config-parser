Simple library that allows to read the data of an Autosubmit experiment.

### Usage: ####

```python

#import the main config library
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
# Init the configuration object where expid = experiment identifier that you want to load
expid = "a01y"
as_conf = AutosubmitConfig("a01y")
# This will load the data from the experiment
as_conf.reload(True)

#all data is store in the as_conf.experiment_data dictionary
as_conf.experiment_data
# Obtain only section data
as_conf.jobs_data
# Obtain only platforms data
as_conf.platforms_data
```
