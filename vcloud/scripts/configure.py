import tempfile
import json

import fabric

import vcloud_plugin_common
from cloudify import ctx

PROVIDER_CONTEXT_RUNTIME_PROPERTY = 'provider_context'


def configure(vcloud_config):
    _copy_vsphere_configuration_to_manager(vcloud_config)
    _install_docker()
    _save_context()


def _copy_vsphere_configuration_to_manager(vcloud_config):
    tmp = tempfile.mktemp()
    with open(tmp, 'w') as f:
        json.dump(vcloud_config, f)
    fabric.api.put(tmp,
                   vcloud_plugin_common.Config.VCLOUD_CONFIG_PATH_DEFAULT)


def _install_docker():
    distro = fabric.api.run(
        'python -c "import platform; print platform.dist()[0]"')
    kernel_version = fabric.api.run(
        'python -c "import platform; print platform.release()"')
    if kernel_version.startswith("3.13") and 'Ubuntu' in distro:
        fabric.api.run("wget -qO- https://get.docker.com/ | sudo sh")


def _save_context():

    resources = dict()

    node_instances = ctx._endpoint.storage.get_node_instances()
    nodes_by_id = \
        {node.id: node for node in ctx._endpoint.storage.get_nodes()}

    for node_instance in node_instances:
        run_props = node_instance.runtime_properties
        props = nodes_by_id[node_instance.node_id].properties

        if "management_network" == node_instance.node_id:
            resources['int_network'] = {
                "name": props.get('resource_id')
            }

    provider = {
        'resources': resources
    }

    ctx.instance.runtime_properties[PROVIDER_CONTEXT_RUNTIME_PROPERTY] = \
        provider
