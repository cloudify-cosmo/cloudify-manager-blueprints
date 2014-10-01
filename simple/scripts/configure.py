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

from cloudify import ctx
from cloudify_cli.bootstrap.tasks import (
    PRIVATE_IP_RUNTIME_PROPERTY,
    PROVIDER_RUNTIME_PROPERTY
)


def configure(private_ip):

    # set private ip for manager server
    ctx.runtime_properties[PRIVATE_IP_RUNTIME_PROPERTY] = private_ip

    # set provider context
    provider = {
        'name': 'simple',
        'context': dict()
    }
    ctx.runtime_properties[PROVIDER_RUNTIME_PROPERTY] = provider
