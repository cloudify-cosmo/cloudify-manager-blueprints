########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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
import fabric.api
import os

from cloudify import ctx
from plugin import utils


GCP_DEFAULT_CONFIG_PATH = '/home/ubuntu/gcp_config.json'


def configure_manager(manager_config_path=GCP_DEFAULT_CONFIG_PATH,
                      gcp_config=None):
    auth = gcp_config.get('auth')
    if auth and os.path.isfile(auth):
        fabric.api.put(auth, manager_config_path)
    node_instances = ctx._endpoint.storage.get_node_instances()
    resources = {}
    for node_instance in node_instances:
        if node_instance.node_id in utils.SECURITY_GROUPS:
            run_props = node_instance.runtime_properties
            resources[node_instance.node_id] = {
                'id': run_props[utils.NAME],
                utils.TARGET_TAGS: run_props[utils.TARGET_TAGS],
                utils.SOURCE_TAGS: run_props[utils.SOURCE_TAGS]}
    resources[utils.GCP_CONFIG] = manager_config_path
    provider = {'resources': resources}
    ctx.instance.runtime_properties['provider_context'] = provider
