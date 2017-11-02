import os
from copy import deepcopy
from unittest import TestCase

from jinja2 import (
    Environment,
    FileSystemLoader,
)


class ManagementWorkerServiceFile(TestCase):
    TEMPLATE_DIR = os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        'components',
        'mgmtworker',
        'config'
    )

    CTX_DICT = {
        'instance': {
            'runtime_properties': {
                'home_dir': '',
                'log_dir': '',
                'rest_host': '',
                'rest_port': '',
                'local_rest_cert_file': '',
                'file_server_url': '',
                'file_server_root': ''
            }
        }
    }

    NODE_DICT = {
        'properties': {
            'log_level': '',
            'extra_env': {}
        }
    }

    BASE_RESULT_DICT = {
        'MGMTWORKER_HOME': '""',
        'VIRTUALENV_DIR': '"/env"',
        'CELERY_WORK_DIR': '"/work"',
        'CELERY_LOG_DIR': '""',
        'CELERY_LOG_LEVEL': '""',
        'RIEMANN_CONFIGS_DIR': '"/opt/riemann"',
        'MANAGEMENT_USER': '"root"',
        'REST_HOST': '""',
        'REST_PORT': '""',
        'LOCAL_REST_CERT_FILE': '""',
        'BROKER_SSL_CERT_PATH': '""',
        'MANAGER_FILE_SERVER_URL': '""',
        'MANAGER_FILE_SERVER_ROOT': '""',
        'CELERY_TASK_SERIALIZER': '"json"',
        'CELERY_RESULT_SERIALIZER': '"json"',
        'CELERY_RESULT_BACKEND': '"amqp"',
        'C_FORCE_ROOT': 'true'
    }

    @classmethod
    def setUpClass(cls):
        """Get template object."""
        env = Environment(loader=FileSystemLoader(cls.TEMPLATE_DIR))
        cls.template = env.get_template('cloudify-mgmtworker')

    def _text_to_dict(self, text):
        lines = text.splitlines()
        result = {}
        for line in lines:
            if not line:
                continue
            components = line.split('=', 1)
            result[str(components[0].strip())] = str(components[1].strip())
        return result

    def test_render_no_extra_env(self):
        text = self.template.render(
            node=self.NODE_DICT,
            ctx=self.CTX_DICT
        )
        self.assertDictEqual(self._text_to_dict(text), self.BASE_RESULT_DICT)

    def test_render_extra_env(self):
        extra_env_entries = {'TEST': 'VALUE'}
        updated_node_dict = deepcopy(self.NODE_DICT)
        updated_node_dict['properties']['extra_env'].update(extra_env_entries)
        text = self.template.render(
            node=updated_node_dict,
            ctx=self.CTX_DICT
        )
        expected_result = deepcopy(self.BASE_RESULT_DICT)
        for key, value in extra_env_entries.iteritems():
            expected_result[key] = '"{0}"'.format(value)

        self.assertDictEqual(self._text_to_dict(text), expected_result)
