#!/usr/bin/env python3
"""Setup vircpt"""
from setuptools import setup, find_packages

setup(
    name="vircpt",
    version="0.1",
    description="Libvirt checkpoint swiss army knife.",
    url="https://github.com/abbbi/vircpt/",
    author="Michael Ablassmeier",
    author_email="abi@grinser.de",
    license="GPL",
    keywords="libnbd libvirt checkpoint backup",
    packages=find_packages(exclude=("docs", "tests", "env")),
    include_package_data=True,
    scripts=["vircpt"],
    extras_require={
        "dev": [],
        "docs": [],
        "testing": [],
    },
    classifiers=[],
)
