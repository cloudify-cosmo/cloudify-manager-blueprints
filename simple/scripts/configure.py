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

import tempfile

import fabric
import fabric.api

from cloudify import ctx


def configure(private_ip):

    # configure local
    key_path = fabric.api.env.key_filename
    ctx.runtime_properties['local_agent_key_path'] = key_path

    # set private ip for manager server
    ctx.runtime_properties['private_ip'] = private_ip

    # set provider context
    ctx.runtime_properties['provider_context'] = {
        'provider_prop1': 'provider_value1',
        'provider_prop2': [1, 2, 3, 34]
    }

    tmp = tempfile.mktemp()

    with open(tmp, 'w') as f:
        f.write('some content')
    fabric.api.put(tmp, '/tmp/tmp_file')
