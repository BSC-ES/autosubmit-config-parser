#!/usr/bin/env python3

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="autosubmitconfigparser",
    version="1.0.55",
    author="Daniel Beltran Mora",
    author_email="daniel.beltran@bsc.es",
    description="An utility library that allows to read an Autosubmit 4 experiment configuration.",
    keywords=['climate', 'weather', 'workflow', 'HPC'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://earth.bsc.es/gitlab/ces/autosubmit4-config-parser.git",
    include_package_data=True,
    package_data={'files': ['autosubmitconfigparser/conf/files/*']},
    packages=setuptools.find_packages(),
    install_requires=['argparse>=1.4.0', 'bscearth.utils>=0.5.2', 'configobj>=5.0.8', 'configparser>=6.0.0', 'mock>=5.1.0', 'pathlib>=1.0.1', 'pyparsing>=3.1.1', 'python-dateutil>=2.8.2', 'ruamel.yaml==0.17.21', 'six>=1.16.0'],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: POSIX :: Linux"
    ],
)
