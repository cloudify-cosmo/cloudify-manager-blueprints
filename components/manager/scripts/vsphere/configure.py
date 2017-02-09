########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import json
from os.path import split
from StringIO import StringIO
from warnings import warn

from fabric.api import put, sudo

import vsphere_plugin_common


def configure(vsphere_config):
    _copy_vsphere_configuration_to_manager(vsphere_config)


def _copy_vsphere_configuration_to_manager(vsphere_config):
    conf_path = vsphere_plugin_common.Config.CONNECTION_CONFIG_PATH_DEFAULT
    conf_dir, conf_name = split(conf_path)
    conf_file = StringIO(json.dumps(vsphere_config))
    sudo('mkdir -p "{}"'.format(conf_dir))
    if '/etc/cloudify/vsphere_plugin' in conf_path:
        sudo('chmod 750 /etc/cloudify')
        sudo('chmod 750 /etc/cloudify/vsphere_plugin')
    else:
        warn(
            "this script expects the connection_config to be located in "
            "/etc/cloudify/vsphere_plugin and it isn't. You may need to "
            "fix the file permissions manually.",
            RuntimeWarning)
    put(conf_file,
        conf_path,
        mode=0o640,
        use_sudo=True,
        )
