#!/usr/bin/env python
from setuptools import setup

setup(
    name="yolink-api",
    version="0.4.1",
    author="YoSmart",
    description="A library to authenticate with yolink device",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/YoSmart-Inc/yolink-api",
    project_urls={
        "Bug Tracker": "https://github.com/YoSmart-Inc/yolink-api/issues",
    },
    license="MIT",
    keywords="yolink api",
    packages=["yolink"],
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "aiohttp>=3.8.1",
        "aiomqtt>=2.0.0,<3.0.0",
        "pydantic>=1.9.0",
        "tenacity>=8.1.0",
    ],
)
