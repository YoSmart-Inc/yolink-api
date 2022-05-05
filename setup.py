#!/usr/bin/env python
from setuptools import setup

setup(
    name="yolink-api",
    version="0.0.3",
    author="YoSmart",
    description="A library to authenticate with yolink device",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/YoSmart-Inc/yolink-api.git"
    license="GPL",
    keywords="yolink api",
    packages=["yolink"],
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    install_requires=[
        "aiohttp",
        "paho-mqtt==1.6.1",
        "pydantic==1.9.0",
    ]
)
