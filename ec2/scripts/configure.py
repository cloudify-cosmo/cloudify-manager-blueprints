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

import os
import json
import tempfile
import fabric.api
from ec2 import configure
from ec2 import constants

def configure_manager(config_path, agents_security_group, agents_keypair):
    _upload_credentials(config_path)
    _set_provider_config(agents_security_group, agents_keypair)

def _upload_credentials(config_path):
    temp = configure.BotoConfig().get_temp_file()
    fabric.api.put(temp, config_path)

def _set_provider_config(agents_security_group, agents_keypair):

    temp_config = tempfile.mktemp()

    provider_context_json = {
        "agents_keypair": agents_keypair,
        "agents_security_group": agents_security_group
    }

    with open(temp_config, 'w') as provider_context_file:
        json.dump(provider_context_json, provider_context_file)

    fabric.api.put(temp_config, constants.AWS_DEFAULT_CONFIG_PATH)
