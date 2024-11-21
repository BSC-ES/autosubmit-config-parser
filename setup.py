from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    'ruamel.yaml==0.18.6',
    'mock',
    'bscearth.utils',
    'configobj',
    'pyparsing',
    'configparser'
]

# Test dependencies
test_requires = [
    'pytest',
    'pytest-cov',
    'pytest-mock',
    'ruff'
]

extras_require = {
    'test': test_requires,
    'all': install_requires + test_requires
}

setup(
    name="autosubmitconfigparser",
    version="1.0.74",
    author="Daniel Beltran Mora",
    author_email="daniel.beltran@bsc.es",
    description="An utility library that allows to read an Autosubmit 4 experiment configuration.",
    keywords=['climate', 'weather', 'workflow', 'HPC'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://earth.bsc.es/gitlab/ces/autosubmit4-config-parser.git",
    include_package_data=True,
    package_data={'files': ['autosubmitconfigparser/conf/files/*']},
    packages=find_packages(),
    install_requires=install_requires,
    extras_require=extras_require,
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: POSIX :: Linux"
    ],
)
