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
import tempfile
import json
import unittest
import shutil

import mock

from softlayer_plugin import constants
from test_utils.utils import get_task


class TestSoftlayerManagerBlueprint(unittest.TestCase):

    def test_softlayer_configuration_copy_to_manager(self):
        task = get_task('../scripts/configure.py',
                        '_copy_softlayer_configuration_to_manager')

        config_output_file_path = tempfile.mkstemp()[1]

        def mock_put(file_path, *args, **kwargs):
            shutil.copyfile(file_path, config_output_file_path)

        task.func_globals['fabric'].api.put = mock_put

        with mock.patch('softlayer_plugin.ctx'):  # mocking ctx (used for log)
            inputs_config = {
                constants.API_CONFIG_USERNAME: 'inputs-username'
            }

            os.environ[constants.SL_USERNAME] = 'envar-username'
            os.environ[constants.SL_API_KEY] = 'envar-api-key'

            task(inputs_config)

            with open(config_output_file_path) as f:
                config = json.load(f)
            self.assertEquals('inputs-username',
                              config.get(constants.API_CONFIG_USERNAME))
            self.assertEquals('envar-api-key',
                              config.get(constants.API_CONFIG_API_KEY))
