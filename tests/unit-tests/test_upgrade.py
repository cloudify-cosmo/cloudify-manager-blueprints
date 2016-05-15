import os
import sys
import unittest
import tempfile
import json
from mock import patch
from cloudify.mocks import MockCloudifyContext
sys.path.append(os.path.join(os.path.dirname(__file__),
                             '../../components'))
import utils  # NOQA


TEST_SERVICE_NAME = 'es'
TEST_RESOURCE_NAME = 'test_resource'


class MockNodeProperties(dict):

    def __init__(self, properties):
        self.update(properties)

    def get_all(self):
        return self


def mock_resource_download():
    def download(source):
        resource_base_dir = utils.resource_factory._get_resources_dir(
                TEST_SERVICE_NAME)
        resource_path = os.path.join(resource_base_dir, 'tmp-res-name')
        utils.mkdir(resource_base_dir)
        utils.write_to_json_file('port: 8080', resource_path)
        return resource_path
    return download


def mock_install_ctx():
    install_node_props = {'es_rpm_source_url': 'http://www.mock.com/es.tar.gz',
                          'test_property': 'test'}
    return _create_mock_context(install_node_props)


def _create_mock_context(install_node_props,
                         node_id='es_node',
                         service=TEST_SERVICE_NAME):
    mock_node_props = MockNodeProperties(properties=install_node_props)
    return MockCloudifyContext(node_id=node_id,
                               node_name=service,
                               properties=mock_node_props)


def mock_upgrade_ctx(use_existing_on_upgrade=False):
    upgrade_node_props = \
        {'es_rpm_source_url': 'http://www.mock.com/new-es.tar.gz',
         'use_existing_on_upgrade': use_existing_on_upgrade,
         'test_property': 'new_value',
         'new_property': 'value'}
    return _create_mock_context(upgrade_node_props)


@patch('utils.ctx.download_resource', mock_resource_download())
@patch('utils.ctx', mock_install_ctx())
def _create_resource_file(resource_dest):
    utils.resource_factory.create(resource_dest,
                                  resource_dest,
                                  TEST_SERVICE_NAME,
                                  user_resource=False,
                                  render=False)


@patch('utils.is_upgrade', False)
def _create_install_resource_file(dest):
    _create_resource_file(dest)


@patch('utils.is_upgrade', True)
def _create_upgrade_resource_file(dest):
    _create_resource_file(dest)


@patch('utils.ctx', mock_install_ctx())
@patch('utils.is_upgrade', False)
def create_install_props_file(service_name):
    return _create_ctx_props_file(service_name)


@patch('utils.is_upgrade', True)
def create_upgrade_props_file(service_name):
    create_install_props_file(service_name)
    return _create_ctx_props_file(service_name)


def _create_ctx_props_file(service_name):
    props_file_path = utils.ctx_factory._get_props_file_path(service_name)
    ctx_properties = utils.ctx_factory.create(service_name)
    return ctx_properties, props_file_path


class TestUpgrade(unittest.TestCase):

    @patch('utils.ctx_factory.BASE_PROPERTIES_PATH', tempfile.mkdtemp())
    def test_ctx_prop_install_file_create(self):
        ctx_props, props_file_path = create_install_props_file(
                TEST_SERVICE_NAME)
        self.assertTrue(os.path.isfile(props_file_path))
        with open(props_file_path, 'r') as f:
            file_props = json.load(f)
        self.assertDictEqual(file_props, ctx_props)

    @patch('utils.ctx', mock_upgrade_ctx())
    @patch('utils.ctx_factory.BASE_PROPERTIES_PATH', tempfile.mkdtemp())
    def test_ctx_prop_upgrade_file_create(self):
        ctx_props, upgrade_props_path = create_upgrade_props_file(
                TEST_SERVICE_NAME)
        self.assertTrue(os.path.isfile(upgrade_props_path))
        with open(upgrade_props_path, 'r') as f:
            file_props = json.load(f)
        self.assertDictEqual(file_props, ctx_props)

    @patch('utils.ctx', mock_upgrade_ctx(use_existing_on_upgrade=True))
    @patch('utils.ctx_factory.BASE_PROPERTIES_PATH', tempfile.mkdtemp())
    def test_use_existing_on_upgrade(self):
        ctx_props, _ = create_upgrade_props_file(TEST_SERVICE_NAME)
        # Assert same value used for upgrade
        self.assertEqual(ctx_props['test_property'], 'test')
        # Assert new property merged with old properties
        self.assertEqual(ctx_props['new_property'], 'value')
        self.assert_rpm_url_overridden(ctx_props)

    @patch('utils.ctx', mock_upgrade_ctx())
    @patch('utils.ctx_factory.BASE_PROPERTIES_PATH', tempfile.mkdtemp())
    def test_new_props_on_upgrade(self):
        ctx_props, _ = create_upgrade_props_file(TEST_SERVICE_NAME)
        self.assertEqual(ctx_props['test_property'], 'new_value')
        self.assert_rpm_url_overridden(ctx_props)

    def assert_rpm_url_overridden(self, ctx_properties):
        self.assertEqual(ctx_properties['es_rpm_source_url'],
                         'http://www.mock.com/new-es.tar.gz')

    @patch('utils.ctx', mock_upgrade_ctx())
    @patch('utils.is_upgrade', True)
    @patch('utils.ctx_factory.BASE_PROPERTIES_PATH', tempfile.mkdtemp())
    def test_archive_properties(self):
        _, install_path = create_install_props_file(TEST_SERVICE_NAME)
        _, upgrade_path = create_upgrade_props_file(TEST_SERVICE_NAME)

        utils.ctx_factory.BASE_PROPERTIES_PATH = os.path.join(
                os.path.dirname(install_path), '../../')

        archived_properties_path = \
            utils.ctx_factory._get_rollback_props_file_path(TEST_SERVICE_NAME)
        # assert props file was archived
        self.assertTrue(os.path.isfile(archived_properties_path))

        install_props = utils.ctx_factory.get(TEST_SERVICE_NAME,
                                              upgrade_props=False)
        upgrade_props = utils.ctx_factory.get(TEST_SERVICE_NAME,
                                              upgrade_props=True)
        self.assertNotEqual(upgrade_props['es_rpm_source_url'],
                            install_props['es_rpm_source_url'])

    @patch('utils.BlueprintResourceFactory.BASE_RESOURCES_PATH',
           tempfile.mkdtemp())
    @patch('utils.is_upgrade', False)
    def test_resource_file_create_on_install(self):
        resource_file_dest = '/opt/manager/{0}'.format(TEST_RESOURCE_NAME)
        _create_install_resource_file(resource_file_dest)
        resource_json = utils.resource_factory._get_resources_json(
                TEST_SERVICE_NAME)

        # assert resource json contains mapping to the new resource dest
        self.assertEqual(resource_json.get(TEST_RESOURCE_NAME),
                         resource_file_dest)
        resource_local_path = os.path.join(
                utils.resource_factory.BASE_RESOURCES_PATH, TEST_SERVICE_NAME,
                utils.resource_factory.RESOURCES_DIR_NAME, TEST_RESOURCE_NAME)
        self.assertTrue(os.path.isfile(resource_local_path))

    @patch('utils.BlueprintResourceFactory.BASE_RESOURCES_PATH',
           tempfile.mkdtemp())
    def test_resource_file_create_on_update(self):
        resource_file_dest = '/opt/manager/{0}'.format(TEST_RESOURCE_NAME)
        _create_upgrade_resource_file(resource_file_dest)
        resource_json = utils.resource_factory._get_resources_json(
                TEST_SERVICE_NAME)

        # assert the upgrade json contains the new resource and its dest
        self.assertEqual(resource_json.get(TEST_RESOURCE_NAME),
                         resource_file_dest)

    @patch('utils.is_upgrade', True)
    @patch('utils.ctx', mock_upgrade_ctx())
    @patch('utils.BlueprintResourceFactory.BASE_RESOURCES_PATH',
           tempfile.mkdtemp())
    def test_archive_resources(self):
        install_resource_dest = '/opt/manager/{0}'.format('install.conf')
        _create_install_resource_file(install_resource_dest)
        upgrade_resource_dest = '/opt/manager/{0}'.format('upgrade.conf')
        _create_upgrade_resource_file(upgrade_resource_dest)
        archived_resource_file = os.path.join(
                utils.resource_factory._get_rollback_resources_dir(
                        TEST_SERVICE_NAME), 'install.conf')
        archived_resources_json = os.path.join(
                utils.resource_factory._get_rollback_resources_dir(
                        TEST_SERVICE_NAME),
                utils.resource_factory.RESOURCES_JSON_FILE)

        # assert resource file and resource json were archived
        self.assertTrue(os.path.isfile(archived_resource_file))
        self.assertTrue(os.path.isfile(archived_resources_json))

        curr_resource_file = os.path.join(
                utils.resource_factory._get_resources_dir(TEST_SERVICE_NAME),
                'upgrade.conf')
        curr_resources_json = os.path.join(
                utils.resource_factory._get_resources_dir(TEST_SERVICE_NAME),
                utils.resource_factory.RESOURCES_JSON_FILE)

        # assert resource file and resource json were replaced
        self.assertTrue(os.path.isfile(curr_resource_file))
        self.assertTrue(os.path.isfile(curr_resources_json))
