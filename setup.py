#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    packages=find_packages(exclude=["docs", "tests*"]),
    package_data={
        "pdbstore": ["py.typed"],
    },
)
