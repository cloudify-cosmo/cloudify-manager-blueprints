import tempfile
import json

import fabric

import vcloud_plugin_common


def configure(vcloud_config):
    _copy_vsphere_configuration_to_manager(vcloud_config)


def _copy_vsphere_configuration_to_manager(vcloud_config):
    tmp = tempfile.mktemp()
    with open(tmp, 'w') as f:
        json.dump(vcloud_config, f)
    fabric.api.put(tmp,
                   vcloud_plugin_common.Config.VCLOUD_CONFIG_PATH_DEFAULT)