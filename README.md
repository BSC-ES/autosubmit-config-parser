Simple library that allows to read the data of an Autosubmit experiment.

### Usage: ####

```python
#import the main config library
from autosubmitconfigparser.config.configcommon import AutosubmitConfig
import os
# Init the configuration object where expid = experiment identifier that you want to load
expid = "a01y"
as_conf = AutosubmitConfig("a01y")
# This will load the data from the experiment
as_conf.reload(True)

#all data is stored in the as_conf.experiment_data dictionary
as_conf.experiment_data
# Obtain only section data
as_conf.jobs_data
# Obtain only platforms data
as_conf.platforms_data
# Obtain all data in parameter format( %SECTION%.%SUBSECTION%.%SUBSECTION% )
parameters = as_conf.deep_parameters_export(as_conf.experiment_data)
# To parse the placeholders from a file use the following function
#write sample text
with open("as_sample.txt", "w") as f:
    f.write("This is a sample text with a placeholder %DEFAULT.EXPID%")

#write the parsed text
with open("as_sample_parsed.txt", "w") as f:
    f.write(as_conf.parse_placeholders(open("as_sample.txt","r").read(), parameters))


# print the file content
with open("as_sample.txt", "r") as f:
    print(f.read())
# print the file content
with open("as_sample_parsed.txt", "r") as f:
    print(f.read())
    
# Result must be:
# This is a sample text with a placeholder %DEFAULT.EXPID%
# This is a sample text with a placeholder expid

# delete samples
os.remove("as_sample.txt")
os.remove("as_sample_parsed.txt")
```

