import os

from jinja2 import (
    Environment,
    FileSystemLoader,
)
from testtools import TestCase
from testtools.matchers import Contains


class TestRestServiceFile(TestCase):

    """Test service file."""

    TEMPLATE_DIR = os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        'components',
        'restservice',
        'config',
    )

    @classmethod
    def setUpClass(cls):
        """Get template object."""
        env = Environment(loader=FileSystemLoader(cls.TEMPLATE_DIR))
        cls.template = env.get_template('cloudify-restservice.service')

    def test_render_default(self):
        """Render template using 0 as the worker count."""
        text = self.template.render(node={
            'properties': {
                'gunicorn_worker_count': 0,
                'gunicorn_max_requests': 1000
            },
        })
        self.assertThat(text, Contains('-w $((${WORKER_COUNT} > ${MAX_WORKER_COUNT} ? ${MAX_WORKER_COUNT} : ${WORKER_COUNT})) \\'))  # NOQA
        self.assertThat(text, Contains('--max-requests 1000'))

    def test_render_integer(self):
        """Render template using an integer as the worker count."""
        expected_worker_count = 12345
        text = self.template.render(node={
            'properties': {
                'gunicorn_worker_count': expected_worker_count,
            },
        })
        self.assertThat(
            text,
            Contains('-w {0} \\'.format(expected_worker_count)),
        )
