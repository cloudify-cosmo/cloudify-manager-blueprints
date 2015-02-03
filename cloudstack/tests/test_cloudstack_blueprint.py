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

from cloudstack_plugin.cloudstack_common import Config
from test_utils.utils import get_task


class TestCloudstackManagerBlueprint(unittest.TestCase):

    def test_cloudstack_configuration_copy_to_manager(self):
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'scripts',
            'configure.py')
        task = get_task(script_path,
                        '_copy_cloudstack_configuration_to_manager')

        config_output_file_path = tempfile.mkstemp()[1]

        def mock_put(file_path, *args, **kwargs):
            shutil.copyfile(file_path, config_output_file_path)

        task.func_globals['fabric'].api.put = mock_put

        inputs_config = {
            'cs_api_key': 'inputs-api-key'
        }

        file_config = {
            'cs_api_key': 'file-api-key',
            'cs_api_secret': 'file-api-secret'
        }
        conf_file_path = tempfile.mkstemp()[1]
        os.environ[Config.CLOUDSTACK_CONFIG_PATH_ENV_VAR] = conf_file_path
        with open(conf_file_path, 'w') as f:
            json.dump(file_config, f)

        os.environ['CS_API_KEY'] = 'envar-api-key'
        os.environ['CS_API_SECRET'] = 'envar-api-secret'
        os.environ['CS_API_URL'] = 'envar-api-url'

        task(inputs_config)

        with open(config_output_file_path) as f:
            config = json.load(f)
        self.assertEquals('inputs-api-key', config.get('cs_api_key'))
        self.assertEquals('file-api-secret', config.get('cs_api_secret'))
        self.assertEquals('envar-api-url', config.get('cs_api_url'))
