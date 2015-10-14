# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

"""
Gluu Agent
----------

Daemon to ensure provider is reachable within cluster.
"""
import codecs
import os
import re
from setuptools import setup
from setuptools import find_packages


def find_version(*file_paths):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, *file_paths), 'r') as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="gluuagent",
    version=find_version("gluuagent", "__init__.py"),
    url="https://github.com/GluuFederation/gluu-agent",
    license="Gluu",
    author="Gluu",
    author_email="info@gluu.org",
    description="Daemon to ensure provider is reachable within cluster.",
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        "click",
        "m2crypto<=0.22.3",
        "netaddr",
        "pyyaml",
        # we're still using docker v1.6.2 (API version 1.18);
        # docker-py 1.3+ probably will break existing code
        "docker-py<1.3",
        "sh",
        "tinydb",
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": ["gluu-agent=gluuagent.cli:main"],
    },
)
