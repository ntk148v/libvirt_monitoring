#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "oslo.config",
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='libvirt_monitoring',
    version='1.2.0',
    description="Libvirt Monitoring with Zabbix",
    long_description=readme + '\n\n' + history,
    author="Kien Nguyen",
    author_email='ntk148v@gmail.com',
    url='https://github.com/ntk148v/libvirt_monitoring',
    packages=[
        'libvirt_monitoring',
    ],
    package_dir={'libvirt_monitoring':
                 'libvirt_monitoring'},
    entry_points={
        'console_scripts': [
            'libvirt_monitoring=libvirt_monitoring.main:main'
        ]
    },
    data_files=[
        ('/etc/libvirt_monitoring/', ['etc/config.ini', 'etc/logging.ini']),
    ],
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    keywords='libvirt_monitoring',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
