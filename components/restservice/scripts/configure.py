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
from os.path import join, dirname

import tempfile

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


# TODO: change to /opt/cloudify-rest-service
REST_SERVICE_HOME = '/opt/manager'
REST_SERVICE_NAME = 'restservice'


def _deploy_security_configuration():
    ctx.logger.info('Deploying REST Security configuration file...')
    security_configuration = \
        ctx.instance.runtime_properties['security_configuration']
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(security_configuration)
    utils.move(path, join(REST_SERVICE_HOME, 'rest-security.conf'))


def configure_restservice():
    _deploy_security_configuration()
    utils.systemd.configure(REST_SERVICE_NAME, render=False)


configure_restservice()
