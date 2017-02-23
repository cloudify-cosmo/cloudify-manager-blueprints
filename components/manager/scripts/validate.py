#!/usr/bin/env python
#########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.


import os
import sys
import urllib2
import platform
import subprocess

from cloudify import ctx


def _error(message):
    return 'Validation Error: {0}'.format(message)


def _get_host_total_memory():
    """
    MemTotal:        7854400 kB
    MemFree:         1811840 kB
    MemAvailable:    3250176 kB
    Buffers:          171164 kB
    Cached:          1558216 kB
    SwapCached:       119180 kB
    """
    with open('/proc/meminfo') as memfile:
        memory = memfile.read()
    for attribute in memory.splitlines():
        if attribute.lower().startswith('memtotal'):
            return int(attribute.split(':')[1].strip().split(' ')[0]) / 1024


def _get_available_host_disk_space():
    """
    Filesystem                 Type 1G-blocks  Used Available Use% Mounted on
    /dev/mapper/my_file_system ext4      213G   63G      139G  32% /
    """
    df = subprocess.Popen(["df", "-BG", "/etc/issue"], stdout=subprocess.PIPE)
    output = df.communicate()[0]
    available_disk_space_in_gb = output.split("\n")[1].split()[3].rstrip('G')
    return int(available_disk_space_in_gb)


def _get_os_distro():
    distro, version, _ = \
        platform.linux_distribution(full_distribution_name=False)
    return distro.lower(), version.split('.')[0]


def _get_python_version():
    major_version = sys.version_info[0]
    minor_version = sys.version_info[1]
    return major_version, minor_version


def _validate_python_version(expected_major_version, expected_minor_version):
    major_version, minor_version = _get_python_version()
    ctx.logger.info('Validating Python version...')
    if not major_version == expected_major_version or \
            not minor_version == expected_minor_version:
        return _error(
            'You are currently running Python {0}.{1}. '
            'You must be running Python {0}.{1} to run '
            'Cloudify Manager.'.format(
                major_version,
                minor_version,
                expected_major_version,
                expected_minor_version))


def _validate_sufficient_memory(min_memory_required_in_mb):
    current_memory = _get_host_total_memory()
    ctx.logger.info('Validating memory requirement...')
    if int(min_memory_required_in_mb) > int(current_memory):
        return _error(
            'The provided host does not have enough memory to run '
            'Cloudify Manager (Current: {0}MB, Required: {1}MB).'.format(
                current_memory, min_memory_required_in_mb))


def _validate_sufficient_disk_space(min_disk_space_required_in_gb):
    available_disk_space_in_gb = _get_available_host_disk_space()

    ctx.logger.info('Validating disk space requirement...')
    if int(available_disk_space_in_gb) < int(min_disk_space_required_in_gb):
        return _error(
            'The provided host does not have enough disk space to run '
            'Cloudify Manager (Current: {0}GB, Required: {1}GB).'.format(
                available_disk_space_in_gb, min_disk_space_required_in_gb))


def _validate_supported_distros(supported_distros, supported_versions):
    distro, version = _get_os_distro()

    ctx.logger.info('Validating supported distributions...')
    if distro not in supported_distros or version not in supported_versions:
        one_of_string = ' or '.join(
            ['{0} {1}.x'.format(dist, ver) for dist in
             supported_distros for ver in supported_versions])
        return _error(
            'Cloudify Manager requires either {0} '
            'to run (Provided: {1} {2})'.format(
                one_of_string, distro, version))


def _validate_resources_package_url(manager_resources_package_url):
    try:
        urllib2.urlopen(manager_resources_package_url)
    except urllib2.HTTPError as ex:
        return _error(
            "The Manager's Resources Package {0} is "
            "not accessible (HTTP Error: {1})".format(
                manager_resources_package_url, ex.code))
    except urllib2.URLError as ex:
        return _error(
            "The Manager's Resources Package {0} is "
            "invalid (URL Error: {1})".format(
                manager_resources_package_url, ex.args))


def _is_bootstrap():
    status_file_path = '/opt/cloudify/_workflow_state.json'
    if os.path.isfile(status_file_path):
        return False
    return True


def validate():
    ignore_validations = ctx.node.properties['ignore_bootstrap_validations']
    resources_package_url = ctx.node.properties['manager_resources_package']
    physical_memory = \
        ctx.node.properties['minimum_required_total_physical_memory_in_mb']
    disk_space = \
        ctx.node.properties['minimum_required_available_disk_space_in_gb']

    error_summary = []

    error_summary.append(_validate_python_version(
        expected_major_version=2, expected_minor_version=7))
    error_summary.append(_validate_supported_distros(
        supported_distros=('centos', 'redhat'),
        supported_versions=('7')))
    error_summary.append(_validate_sufficient_memory(
        min_memory_required_in_mb=physical_memory))
    error_summary.append(_validate_sufficient_disk_space(
        min_disk_space_required_in_gb=disk_space))
    if resources_package_url:
        error_summary.append(_validate_resources_package_url(
            resources_package_url))

    # if no error occurred in a validation, we need to remove its reference.
    error_summary = [error for error in error_summary if error]
    if error_summary:
        printable_error_summary = '\n' + '\n\t'.join(error_summary)
        if ignore_validations:
            ctx.logger.warn('Ignoring validation errors. {0}'.format(
                printable_error_summary))
        else:
            ctx.abort_operation(printable_error_summary)


if __name__ == '__main__':
    validate()
