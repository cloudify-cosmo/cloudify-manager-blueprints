#!/usr/bin/env python

import re
import os
import sys
import pwd
import time
import glob
import shlex
import urllib
import socket
import hashlib
import tempfile
import subprocess
from functools import wraps
import json

from cloudify import ctx


PROCESS_POLLING_INTERVAL = 0.1
CLOUDIFY_SOURCES_PATH = '/opt/cloudify/sources'
MANAGER_RESOURCES_HOME = '/opt/manager/resources'
AGENT_ARCHIVES_PATH = '{0}/packages/agents'.format(MANAGER_RESOURCES_HOME)


def retry(exception, tries=4, delay=3, backoff=2):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception as ex:
                    msg = "{0}, Retrying in {1} seconds...".format(ex, mdelay)
                    ctx.logger.warn(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry


def get_file_contents(file_path):
    with open(file_path) as f:
        data = f.read().rstrip('\n')
    return data


def run(command, retries=0, ignore_failures=False, globx=False):
    if isinstance(command, str):
        command = shlex.split(command)
    stderr = subprocess.PIPE
    stdout = subprocess.PIPE
    if globx:
        glob_command = []
        for arg in command:
            glob_command.append(glob.glob(arg))
        command = glob_command
    ctx.logger.debug('Running: {0}'.format(command))
    proc = subprocess.Popen(command, stdout=stdout, stderr=stderr)
    proc.aggr_stdout, proc.aggr_stderr = proc.communicate()
    if proc.returncode != 0:
        command_str = ' '.join(command)
        if retries:
            ctx.logger.warn('Failed running command: {0}. Retrying. '
                            '({1} left)'.format(command_str, retries))
            proc = run(command, retries - 1)
        elif not ignore_failures:
            ctx.logger.error('Failed running command: {0} ({1}).'.format(
                command_str, proc.aggr_stderr))
            sys.exit(1)
    return proc


def sudo(command, retries=0, globx=False, ignore_failures=False):
    if isinstance(command, str):
        command = shlex.split(command)
    command.insert(0, 'sudo')
    return run(command=command, globx=globx, retries=retries,
               ignore_failures=ignore_failures)


def sudo_write_to_file(contents, destination):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(contents)
    return move(path, destination)


def deploy_ssl_certificate(private_or_public, destination, group, cert):
    # Root owner, with permissions set below,
    # allow anyone to read a public cert,
    # and allow the owner to read a private cert, but not change it,
    # mitigating risk in the event of the associated service being vulnerable.
    ownership = 'root.{0}'.format(group)
    if private_or_public == 'private':
        private_cert_ok = 'PRIVATE KEY' in cert.split('\n')[0]
        if private_cert_ok:
            permissions = '440'
        else:
            error_exit("Private certificate is expected to begin with a line "
                       "containing 'PRIVATE KEY'.")
    elif private_or_public == 'public':
        public_cert_ok = 'BEGIN CERTIFICATE' in cert.split('\n')[0]
        if public_cert_ok:
            permissions = '444'
        else:
            error_exit("Public certificate is expected to begin with a line "
                       "containing 'BEGIN CERTIFICATE'.")
    else:
        error_exit("Certificates may only be 'private' or 'public', "
                   "not {0}".format(private_or_public))
    ctx.logger.info(
        "Deploying {0} SSL certificate in {1} for group {2}".format(
            private_or_public, destination, group))
    sudo_write_to_file(cert, destination)
    ctx.logger.info("Setting permissions ({0}) and ownership ({1}) of SSL "
                    "certificate at {2}".format(
                        permissions, ownership, destination))
    chmod(permissions, destination)
    sudo('chown {0} {1}'.format(ownership, destination))


def error_exit(message):
    ctx.logger.error(message)
    sys.exit(1)


def mkdir(dir):
    if os.path.isdir(dir):
        return
    ctx.logger.info('Creating Directory: {0}'.format(dir))
    sudo(['mkdir', '-p', dir])


def move(source, destination):
    sudo(['mv', source, destination])


def copy(source, destination):
    sudo(['cp', '-r', source, destination])


def remove(path, ignore_failure=False):
    if os.path.exists(path):
        ctx.logger.info('Deleting {0}'.format(path))
        sudo(['rm', '-rf', path], ignore_failures=ignore_failure)
    else:
        ctx.logger.info('Path does not exist: {0}. Skipping delete'
                        .format(path))


def install_python_package(source, venv=''):
    if venv:
        ctx.logger.info('Installing {0} in virtualenv {1}...'.format(
            source, venv))
        sudo(['{0}/bin/pip'.format(
            venv), 'install', source, '--upgrade'])
    else:
        ctx.logger.info('Installing {0}'.format(source))
        sudo(['pip', 'install', source, '--upgrade'])


def curl_download_with_retries(source, destination):
    curl_cmd = ['curl']
    curl_cmd.extend(['--retry', '10'])
    curl_cmd.append('--fail')
    curl_cmd.append('--silent')
    curl_cmd.append('--show-error')
    curl_cmd.extend(['--location', source])
    curl_cmd.append('--create-dir')
    curl_cmd.extend(['--output', destination])
    ctx.logger.info('curling: {0}'.format(' '.join(curl_cmd)))
    run(curl_cmd)


def download_file(url, destination=''):
    if not destination:
        fd, destination = tempfile.mkstemp()
        os.remove(destination)
        os.close(fd)

    if not os.path.isfile(destination):
        ctx.logger.info('Downloading {0} to {1}...'.format(url, destination))
        try:
            final_url = urllib.urlopen(url).geturl()
            if final_url != url:
                ctx.logger.debug('Redirected to {0}'.format(final_url))
            f = urllib.URLopener()
            # TODO: try except with @retry
            f.retrieve(final_url, destination)
        except:
            curl_download_with_retries(url, destination)
    else:
        ctx.logger.info('File {0} already exists...'.format(destination))
    return destination


def get_file_name_from_url(url):
    try:
        return url.split('/')[-1]
    except:
        # in case of irregular url. precaution.
        # note that urlparse is deprecated in Python 3
        from urlparse import urlparse
        disassembled = urlparse(url)
        return os.path.basename(disassembled.path)


def download_cloudify_resource(url, service_name, destination=None):
    """Downloads a resource and saves it as a cloudify resource.

    The resource will be saved under the appropriate service resource path and
    will be used in case of operation execution failure after the resource has
    already been downloaded.
    """
    if destination:
        source_res_path, _ = resource_factory.create(url,
                                                     destination,
                                                     service_name,
                                                     source_resource=True,
                                                     render=False)
        copy(source_res_path, destination)
    else:
        res_name = os.path.basename(url)
        source_res_path, _ = resource_factory.create(url, res_name,
                                                     service_name,
                                                     source_resource=True,
                                                     render=False)
    return source_res_path


def deploy_blueprint_resource(source, destination, service_name,
                              user_resource=False, render=True, load_ctx=True):
    """
    Downloads a resource from the blueprint to a destination. This expands
    `download-resource` as a `sudo mv` is required after having downloaded
    the resource.
    :param source: Resource source.
    :param destination: Resource destination.
    :param service_name: The service name that requires the resource.
    :param user_resource: Set to true for resources that should potentially
    remain identical upon upgrade such as custom security configuration files.
    :param render: Set to false if resource does not require rendering.
    :param load_ctx: Set to false if node props should not be loaded.
    NOTE: This is normally used when using this function from a preconfigure
    script where node properties are not available.
    """
    ctx.logger.info('Deploying blueprint resource {0} to {1}'.format(
        source, destination))
    resource_file, dest = resource_factory.create(source,
                                                  destination,
                                                  service_name,
                                                  user_resource=user_resource,
                                                  render=render,
                                                  load_ctx=load_ctx)
    copy(resource_file, dest)


def copy_notice(service):
    """Deploys a notice file to /opt/SERVICENAME_NOTICE.txt"""
    destn = os.path.join('/opt', '{0}_NOTICE.txt'.format(service))
    source = 'components/{0}/NOTICE.txt'.format(service)
    resource_file, dest = resource_factory.create(source, destn, service,
                                                  render=False)
    copy(resource_file, dest)


def wait_for_port(port, host='localhost'):
    """Helper function to wait for a port to open before continuing"""
    counter = 1

    ctx.logger.info('Waiting for {0}:{1} to become available...'.format(
        host, port))

    for tries in range(24):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        if not result == 0:
            ctx.logger.info('{0}:{1} is not available yet, '
                            'retrying... ({2}/24)'.format(host, port, counter))
            time.sleep(2)
            counter += 1
            continue
        ctx.logger.info('{0}:{1} is open!'.format(host, port))
        return
    error_exit('Failed to connect to {0}:{1}...'.format(host, port))


def yum_install(source, service_name):
    """Installs a package using yum.

    yum supports installing from URL, path and the default yum repo
    configured within your image.
    you can specify one of the following:
    [yum install -y] mylocalfile.rpm
    [yum install -y] mypackagename

    If the source is a package name, it will check whether it is already
    installed. If it is, it will do nothing. It not, it will install it.

    If the source is a url to an rpm and the file doesn't already exist
    in a predesignated archives file path (${CLOUDIFY_SOURCES_PATH}/),
    it will download it. It will then use that file to check if the
    package is already installed. If it is, it will do nothing. If not,
    it will install it.

    NOTE: This will currently not take into considerations situations
    in which a file was partially downloaded. If a file is partially
    downloaded, a redownload will not take place and rather an
    installation will be attempted, which will obviously fail since
    the rpm file is incomplete.
    ALSO NOTE: you cannot provide `yum_install` with a space
    separated array of packages as you can with `yum install`. You must
    provide one package per invocation.
    """
    if source.startswith(('http', 'https', 'ftp')):
        filename = get_file_name_from_url(source)
        source_name, ext = os.path.splitext(filename)
    else:
        source_name, ext = source, ''
    source_path = source_name

    if ext.endswith('rpm'):
        source_path = download_cloudify_resource(source, service_name)

    rpm_handler = RpmPackageHandler(source_path)
    ctx.logger.info('Checking whether {0} is already installed...'.format(
        source_path))
    if rpm_handler.is_rpm_installed():
        ctx.logger.info('Package {0} is already installed.'.format(source))
        return

    # removes any existing versions of the package that do not match
    # the provided package source version
    rpm_handler.remove_existing_rpm_package()

    ctx.logger.info('yum installing {0}...'.format(source_path))
    sudo(['yum', 'install', '-y', source_path])


class RpmPackageHandler(object):

    def __init__(self, source_path):
        self.source_path = source_path

    def remove_existing_rpm_package(self):
        """
        removes any version that satisfies the package name of the given
        source path.
        """
        package_name = self.get_rpm_package_name()
        if self._is_package_installed(package_name):
            ctx.logger.info('Removing existing package sources for package '
                            'with name: {0}'.format(package_name))
            sudo(['rpm', '--noscripts', '-e', package_name])

    @staticmethod
    def _is_package_installed(name):
        installed = run(['rpm', '-q', name], ignore_failures=True)
        if installed.returncode == 0:
            return True
        return False

    def is_rpm_installed(self):
        """
        returns true if provided rpm is already installed.
        """
        src_query = run(['rpm', '-qp', self.source_path])
        source_name = src_query.aggr_stdout.rstrip('\n\r')

        return self._is_package_installed(source_name)

    def get_rpm_package_name(self):
        """
        returns the package name according to the info provided in the source
        file.
        """
        split_index = ' : '
        package_details = {}
        package_details_query = run(['rpm', '-qpi', self.source_path])
        rows = package_details_query.aggr_stdout.split('\n')
        # split raw data according to the ' : ' index
        for row in rows:
            if split_index in row:
                first_columb_index = row.index(split_index)
                key = row[:first_columb_index].strip()
                value = row[first_columb_index + len(split_index):].strip()
                package_details[key] = value
        return package_details['Name']


class SystemD(object):

    def systemctl(self, action, service='', retries=0, ignore_failure=False):
        systemctl_cmd = ['systemctl', action]
        if service:
            systemctl_cmd.append(service)
        sudo(systemctl_cmd, retries=retries, ignore_failures=ignore_failure)

    def configure(self, service_name, render=True):
        """This configures systemd for a specific service.

        It requires that two files are present for each service one containing
        the environment variables and one contains the systemd config.
        All env files will be named "cloudify-SERVICENAME".
        All systemd config files will be named "cloudify-SERVICENAME.service".
        """
        sid = 'cloudify-{0}'.format(service_name)
        env_dst = "/etc/sysconfig/{0}".format(sid)
        srv_dst = "/usr/lib/systemd/system/{0}.service".format(sid)
        env_src = "components/{0}/config/{1}".format(service_name, sid)
        srv_src = "components/{0}/config/{1}.service".format(service_name, sid)

        ctx.logger.info('Deploying systemd EnvironmentFile...')
        deploy_blueprint_resource(env_src, env_dst, service_name,
                                  render=render)
        ctx.logger.info('Deploying systemd .service file...')
        deploy_blueprint_resource(srv_src, srv_dst, service_name,
                                  render=render)

        ctx.logger.info('Enabling systemd .service...')
        self.systemctl('enable', '{0}.service'.format(sid))
        self.systemctl('daemon-reload')

    @staticmethod
    def get_vars_file_path(service_name):
        """Returns the path to a systemd environment variables file
        for a given service_name. (e.g. /etc/sysconfig/cloudify-rabbitmq)
        """
        sid = 'cloudify-{0}'.format(service_name)
        return '/etc/sysconfig/{0}'.format(sid)

    @staticmethod
    def get_service_file_path(service_name):
        """Returns the path to a systemd service file
        for a given service_name.
        (e.g. /usr/lib/systemd/system/cloudify-rabbitmq.service)
        """
        sid = 'cloudify-{0}'.format(service_name)
        return "/usr/lib/systemd/system/{0}.service".format(sid)

    def enable(self, service_name, retries=0, append_prefix=True):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        ctx.logger.info('Enabling systemd service {0}...'
                        .format(full_service_name))
        self.systemctl('enable', service_name, retries)

    def start(self, service_name, retries=0, append_prefix=True):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        ctx.logger.info('Starting systemd service {0}...'
                        .format(full_service_name))
        self.systemctl('start', full_service_name, retries)

    def stop(self, service_name, retries=0, append_prefix=True,
             ignore_failure=False):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        ctx.logger.info('Stopping systemd service {0}...'
                        .format(full_service_name))
        self.systemctl('stop', full_service_name, retries,
                       ignore_failure=ignore_failure)

    def restart(self, service_name, retries=0, ignore_failure=False,
                append_prefix=True):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        self.systemctl('restart', full_service_name, retries,
                       ignore_failure=ignore_failure)

    @staticmethod
    def _get_full_service_name(service_name, append_prefix):
        if append_prefix:
            return 'cloudify-{0}'.format(service_name)
        return service_name


systemd = SystemD()


def replace_in_file(this, with_this, in_here):
    """Replaces all occurences of the regex in all matches
    from a file with a specific value.
    """
    ctx.logger.info('Replacing {0} with {1} in {2}...'.format(
        this, with_this, in_here))
    with open(in_here) as f:
        content = f.read()
    new_content = re.sub(this, with_this, content)
    fd, temp_file = tempfile.mkstemp()
    os.close(fd)
    with open(temp_file, 'w') as f:
        f.write(new_content)
    move(temp_file, in_here)


def get_selinux_state():
    return subprocess.check_output('getenforce').rstrip('\n\r')


def set_selinux_permissive():
    """This sets SELinux to permissive mode both for the current session
    and systemwide.
    """
    ctx.logger.info('Checking whether SELinux in enforced...')
    if 'Enforcing' == get_selinux_state():
        ctx.logger.info('SELinux is enforcing, setting permissive state...')
        sudo(['setenforce', 'permissive'])
        replace_in_file(
            'SELINUX=enforcing',
            'SELINUX=permissive',
            '/etc/selinux/config')
    else:
        ctx.logger.info('SELinux is not enforced.')


def get_rabbitmq_endpoint_ip(endpoint=None):
    """Gets the rabbitmq endpoint IP, using the manager IP if the node
    property is blank.
    """
    if endpoint:
        return endpoint
    return ctx.instance.host_ip


def create_service_user(user, home):
    """Creates a user.

    It will not create the home dir for it and assume that it already exists.
    This user will only be created if it didn't already exist.
    """
    ctx.logger.info('Checking whether user {0} exists...'.format(user))
    try:
        pwd.getpwnam(user)
        ctx.logger.info('User {0} already exists...'.format(user))
    except KeyError:
        ctx.logger.info('Creating user {0}, home: {1}...'.format(user, home))
        sudo(['useradd', '--shell', '/sbin/nologin', '--home-dir', home,
              '--no-create-home', '--system', user])


def logrotate(service):
    """Deploys a logrotate config for a service.

    Note that this is not idempotent in the sense that if a logrotate
    file is already copied to /etc/logrotate.d, it will copy it again
    and override it. This is done as such so that if a service deploys
    its own logrotate configuration, we will override it.
    """
    if not os.path.isfile('/etc/cron.hourly/logrotate'):
        ctx.logger.info('Deploying logrotate hourly cron job...')
        move('/etc/cron.daily/logrotate', '/etc/cron.hourly/logrotate')

    ctx.logger.info('Deploying logrotate config...')
    config_file_source = 'components/{0}/config/logrotate'.format(service)
    logrotated_path = '/etc/logrotate.d'
    config_file_destination = os.path.join(logrotated_path, service)
    if not os.path.isdir(logrotated_path):
        os.mkdir(logrotated_path)
        chown('root', 'root', logrotated_path)
    deploy_blueprint_resource(config_file_source,
                              config_file_destination,
                              service)
    chmod('644', config_file_destination)
    chown('root', 'root', config_file_destination)


def chmod(mode, path):
    ctx.logger.info('chmoding {0}: {1}'.format(path, mode))
    sudo(['chmod', mode, path])


def chown(user, group, path):
    ctx.logger.info('chowning {0} by {1}:{2}...'.format(path, user, group))
    sudo(['chown', '-R', '{0}:{1}'.format(user, group), path])


def ln(source, target, params=None):
    ctx.logger.debug('Softlinking {0} to {1} with params {2}'.format(
        source, target, params))
    command = ['ln']
    if params:
        command.append(params)
    command.append(source)
    command.append(target)
    if '*' in source or '*' in target:
        sudo(command, globx=True)
    else:
        sudo(command)


def clean_var_log_dir(service):
    pass
    # path = "/var/log/{0}".format(service)
    # if os.path.exists(path):
    #     if not os.path.exists("/var/log/cloudify"):
    #         os.mkdir("/var/log/cloudify")
    #     if not os.path.exists("/var/log/cloudify/{0}".format(service)):
    #         os.mkdir("/var/log/cloudify/{0}".format(service))
    #     logfiles = [f for f in os.listdir(path) if os.path.isfile(
    #             os.path.join(path, f))]
    #     for f in logfiles:
    #         ctx.logger.info(f)
    #         os.rename(f, "/var/log/cloudify/{0}/{1}-from_bootstrap-".format(
    #                 service, time.strftime('%Y_%m_%d_%H_%M_%S')))
    #     ctx.logger.info(
    #             "Removing unnecessary logs directory: /var/log/${0}".format(
    #                     service))
    #     sudo(['rm', '-rf', path])


def untar(source, destination='/tmp', strip=1, skip_old_files=False):
    # TODO: use tarfile instead
    ctx.logger.debug('Extracting {0} to {1}...'.format(source, destination))
    tar_command = ['tar', '-xzvf', source, '-C', destination,
                   '--strip={0}'.format(strip)]
    if skip_old_files:
        tar_command.append('--skip-old-files')
    sudo(tar_command)


def validate_md5_checksum(resource_path, md5_checksum_file_path):
    ctx.logger.info('Validating md5 checksum for {0}'.format(resource_path))
    with open(md5_checksum_file_path) as checksum_file:
        original_md5 = checksum_file.read().rstrip('\n\r').split()[0]

    with open(resource_path) as file_to_check:
        data = file_to_check.read()
        # pipe contents of the file through
        md5_returned = hashlib.md5(data).hexdigest()

    if original_md5 == md5_returned:
        return True
    else:
        ctx.logger.error(
            'md5 checksum validation failed! Original checksum: {0} '
            'Calculated checksum: {1}.'.format(original_md5, md5_returned))
        return False


def write_to_json_file(content, file_path):
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    mkdir(os.path.dirname(os.path.abspath(file_path)))
    with open(tmp_file.name, 'w') as f:
        f.write(json.dumps(content))
    move(tmp_file.name, file_path)


# this function should be invoked only by services that depend on the
# manager-config node
def load_manager_config_prop(prop_name):
    ctx.logger.info('Loading {0} configuration'.format(prop_name))
    manager_props = ctx_factory.get_install_properties('manager-config')
    return json.dumps(manager_props[prop_name])


def _is_upgrade():
    """
    Returns true if manager is in upgrade mode. This function will assume
    manager is in upgrade state according to the maintenance mode file.
    """
    status_file_path = '/opt/manager/status.txt'
    if os.path.isfile(status_file_path):
        ctx.logger.info('Loading upgrade status file: {0}'
                        .format(status_file_path))
        with open(status_file_path) as f:
            status_dict = json.load(f)
        return status_dict['status'] == 'activated'
    else:
        return False


def _is_rollback():
    """
    Returns true if manager is in rollback state.
    """
    return False


is_upgrade = _is_upgrade()
is_rollback = _is_rollback()
is_install = not is_rollback and not is_upgrade


class CtxPropertyFactory(object):
    PROPERTIES_FILE_NAME = 'properties.json'
    BASE_PROPERTIES_PATH = '/opt/cloudify'
    NODE_PROPS_DIR_NAME = 'node_properties'
    ROLLBACK_NODE_PROPS_DIR_NAME = 'node_properties_rollback'

    # A list of property suffixes to be included in the upgrade process,
    # despite having 'use_existing_on_upgrade' set to ture
    UPGRADE_PROPS_SUFFIX = ['source_url', 'cloudify_resources_url',
                            'use_existing_on_upgrade']

    # Create node properties according to the workflow context install/upgrade
    def create(self, service_name, write_to_file=True):
        """
        a Factory used to create a local copy of the node properties used
        upon deployment. This copy will allows to later reuse the properties
        for upgrade/rollback purposes. The node ctx properties will be set
        according to the node property named 'use_existing_on_upgrade'.
        :param service_name: The service name
        :param write_to_file: write props to local file path
        :return: The relevant ctx node properties dict.
        """
        ctx_props = self._load_ctx_properties(service_name)

        if is_upgrade:
            # archive path existence will determine whether rollback is even
            # necessary if these scripts run in rollback context.
            archive_path = self._get_rollback_properties_dir(service_name)
            mkdir(archive_path)

        if write_to_file:
            # write properties to a local backup path
            self._write_props_to_file(ctx_props, service_name)

        return ctx_props

    def _write_props_to_file(self, ctx_props, service_name):

        dest_file_path = self._get_props_file_path(service_name)
        ctx.logger.info('Saving {service} input configuration to {path}'
                        .format(service=service_name,
                                path=dest_file_path))
        write_to_json_file(ctx_props, dest_file_path)

    def archive_properties(self, service_name):
        """
        Archive previously used node properties. These properties will be used
        for rollback purposes. This method should be called ONLY once it's been
        determined that the node installation has ended and the service is up.
        :param service_name: The service/node name.
        """
        service_archive_path = self._get_rollback_properties_dir(service_name)
        base_service_dir = self._get_properties_dir(service_name)
        properties_file_path = os.path.join(base_service_dir,
                                            self.PROPERTIES_FILE_NAME)
        ctx.logger.info('Archiving previous inputs for service {0}'
                        .format(service_name))
        move(properties_file_path, service_archive_path)
        ctx.logger.info('Setting new properties for service {0}'
                        .format(service_name))
        move(self._get_props_file_path(service_name), properties_file_path)

    def _get_props_file_path(self, service_name):
        base_service_dir = self._get_properties_dir(service_name)
        if is_upgrade:
            dest_file_path = os.path.join(
                    base_service_dir,
                    'upgrade-{0}'.format(self.PROPERTIES_FILE_NAME))
        else:
            dest_file_path = os.path.join(base_service_dir,
                                          self.PROPERTIES_FILE_NAME)
        return dest_file_path

    def _load_ctx_properties(self, service_name):
        node_props = ctx.node.properties.get_all()
        if is_upgrade:
            # Use existing property configuration during upgrade
            use_existing = node_props.get('use_existing_on_upgrade')
            if use_existing:
                install_props_path = \
                    os.path.join(self._get_properties_dir(service_name),
                                 self.PROPERTIES_FILE_NAME)
                ctx.logger.info('Loading existing {0} input config from '
                                '{1}'.format(service_name, install_props_path))
                with open(install_props_path) as f:
                    existing_props = json.load(f)

                # Removing properties with suffix matching upgrade properties
                for key in existing_props.keys():
                    for suffix in self.UPGRADE_PROPS_SUFFIX:
                        if key.endswith(suffix):
                            del existing_props[key]

                # Update node properties with existing configuration inputs
                node_props.update(existing_props)

        node_props['service_name'] = service_name

        return node_props

    def _get_properties_dir(self, service_name):
        return os.path.join(self.BASE_PROPERTIES_PATH,
                            service_name,
                            self.NODE_PROPS_DIR_NAME)

    def _get_rollback_properties_dir(self, service_name):
        return os.path.join(self.BASE_PROPERTIES_PATH,
                            service_name,
                            self.ROLLBACK_NODE_PROPS_DIR_NAME)

    def get_install_properties(self, service_name):
        props_dir = self._get_properties_dir(service_name)
        install_props_file = os.path.join(props_dir, self.PROPERTIES_FILE_NAME)
        with open(install_props_file) as f:
            return json.load(f)


class BlueprintResourceFactory(object):

    BASE_RESOURCES_PATH = '/opt/cloudify'
    RESOURCES_DIR_NAME = 'resources'
    RESOURCES_ROLLBACK_DIR_NAME = 'resources_rollback'
    RESOURCES_JSON_FILE = '__resources.json'

    UPGRADE_RESOURCE_PREFIX = 'upgrade-'

    def create(self, source, destination, service_name, user_resource=False,
               source_resource=False, render=True, load_ctx=True):
        """
        a Factory used to create a local copy of a resource upon deployment.
        This copy allows to later reuse the resource for upgrade/rollback
        purposes.
        :param source: The resource source url
        :param destination: Resource destination path
        :param service_name: used to retrieve node properties to be rendered
        into a resource template
        :param user_resource: Resources that should potentially remain
        identical upon upgrade such as custom security configuration files.
        These file will be reused provided the ctx node property:
        use_existing_on_upgrade set to True.
        :param source_resource: Source resources are source packages that
        should be downloaded with no rendering and only archived.
        :param render: Set to false if resource does not require rendering.
        :param load_ctx: Set to false if properties are not available in the
        context of the script.
        :return: The local resource file path and destination.
        """
        resource_name = os.path.basename(destination)
        # The local path is decided according to whether we are in upgrade
        local_resource_path = self._get_resource_file_path(service_name,
                                                           resource_name,
                                                           is_upgrade)

        if not os.path.isfile(local_resource_path):
            mkdir(os.path.dirname(local_resource_path))
            if user_resource:
                self._download_user_resource(source,
                                             local_resource_path,
                                             resource_name,
                                             service_name,
                                             render=render,
                                             load_ctx=load_ctx)
            elif source_resource:
                self._download_source_resource(source,
                                               local_resource_path)
            elif render:
                self._download_resource_and_render(source,
                                                   local_resource_path,
                                                   service_name,
                                                   load_ctx)
            else:
                self._download_resource(source, local_resource_path)
            resources_props = self._get_resources_json(service_name,
                                                       is_upgrade)
            # update the resources.json
            if resource_name not in resources_props.keys():
                resources_props[resource_name] = destination
                self._set_resources_json(resources_props, service_name,
                                         is_upgrade)
        return local_resource_path, destination

    def _download_user_resource(self, source, dest, resource_name,
                                service_name, render=True, load_ctx=True):
        if is_upgrade:
            install_props = self._get_install_resources_json(service_name)
            existing_resource_path = install_props.get(resource_name, '')
            if os.path.isfile(existing_resource_path):
                ctx.logger.info('Using existing resource for {0}'
                                .format(resource_name))
                # update the resource file we hold that might have changed
                install_resource = self._get_resource_file_path(
                        service_name, resource_name, upgrade=False)
                copy(existing_resource_path, install_resource)
                # copy it to upgrade-resource_name
                copy(existing_resource_path, dest)
            else:
                ctx.logger.info('User resource {0} not found on {1}'
                                .format(resource_name, path=dest))

        if not os.path.isfile(dest):
            if render:
                self._download_resource_and_render(source, dest, service_name,
                                                   load_ctx=load_ctx)
            else:
                self._download_resource(source, dest)

    @staticmethod
    def _download_resource(source, dest):
        resource_name = os.path.basename(dest)
        ctx.logger.info('Downloading resource {0} to {1}'
                        .format(resource_name, dest))
        tmp_file = ctx.download_resource(source)
        move(tmp_file, dest)

    def _download_resource_and_render(self, source, dest, service_name,
                                      load_ctx):
        resource_name = os.path.basename(dest)
        ctx.logger.info('Downloading resource {0} to {1}'
                        .format(resource_name, dest))
        if load_ctx:
            params = self._load_node_props(service_name)
            tmp_file = ctx.download_resource_and_render(source, '', params)
        else:
            # rendering will be possible only for runtime properties
            tmp_file = ctx.download_resource_and_render(source, '')
        move(tmp_file, dest)

    @staticmethod
    def _download_source_resource(source, local_resource_path):
        filename = get_file_name_from_url(source)
        if filename in os.listdir(CLOUDIFY_SOURCES_PATH):
            tmp_path = os.path.join(CLOUDIFY_SOURCES_PATH, filename)
            ctx.logger.info(
                'Source found at: {0}, will use it instead.'.format(tmp_path))
        else:
            tmp_path = download_file(source)
        ctx.logger.debug('Saving {0} under {1}'
                         .format(tmp_path, local_resource_path))
        move(tmp_path, local_resource_path)

    @staticmethod
    def _load_node_props(service_name):
        node_props = ctx_factory.create(service_name, write_to_file=False)
        return {'node': {'properties': node_props}}

    def _get_resource_file_path(self, service_name, resource_name, upgrade):
        base_service_res_dir = self._get_resources_dir(service_name)
        if upgrade:
            upgrade_resource_name = self.UPGRADE_RESOURCE_PREFIX + \
                                    resource_name

            dest_file_path = os.path.join(base_service_res_dir,
                                          upgrade_resource_name)
        else:
            dest_file_path = os.path.join(base_service_res_dir, resource_name)
        return dest_file_path

    def _get_upgrade_resources_json(self, service_name):
        return self._get_resources_json(service_name, True)

    def _get_install_resources_json(self, service_name):
        return self._get_resources_json(service_name, False)

    def _get_resources_json(self, service_name, upgrade):
        resources_json = self._get_resource_file_path(service_name,
                                                      self.RESOURCES_JSON_FILE,
                                                      upgrade=upgrade)
        if os.path.isfile(resources_json):
            with open(resources_json) as f:
                return json.load(f)
        return {}

    def _set_resources_json(self, resources_dict, service_name, upgrade):
        resources_json = self._get_resource_file_path(service_name,
                                                      self.RESOURCES_JSON_FILE,
                                                      upgrade=upgrade)
        write_to_json_file(resources_dict, resources_json)

    def archive_resources(self, service_name):
        rollback_dir = self._get_rollback_resources_dir(service_name)
        mkdir(rollback_dir)

        service_archive_path = self._get_resources_dir(service_name)
        # nodes will not always use blueprint resources i.e. java/python
        if is_upgrade and os.path.isdir(service_archive_path):
            ctx.logger.info('Archiving node {0} resources'
                            .format(service_name))
            resource_files = os.listdir(service_archive_path)
            for filename in resource_files:
                if not filename.startswith(self.UPGRADE_RESOURCE_PREFIX):
                    move(os.path.join(service_archive_path, filename),
                         rollback_dir)

            prefix_len = len(self.UPGRADE_RESOURCE_PREFIX)
            for filename in resource_files:
                if filename.startswith(self.UPGRADE_RESOURCE_PREFIX):
                    move(os.path.join(service_archive_path, filename),
                         os.path.join(service_archive_path,
                                      filename[prefix_len:]))

    def _get_resources_dir(self, service_name):
        return os.path.join(self.BASE_RESOURCES_PATH,
                            service_name,
                            self.RESOURCES_DIR_NAME)

    def _get_rollback_resources_dir(self, service_name):
        return os.path.join(self.BASE_RESOURCES_PATH,
                            service_name,
                            self.RESOURCES_ROLLBACK_DIR_NAME)


resource_factory = BlueprintResourceFactory()
ctx_factory = CtxPropertyFactory()


def start_service_and_archive_properties(service_name,
                                         append_prefix=True,
                                         ignore_restart_fail=False):

    if is_upgrade:
        systemd.restart(service_name,
                        ignore_failure=ignore_restart_fail,
                        append_prefix=append_prefix)
        ctx_factory.archive_properties(service_name)
        resource_factory.archive_resources(service_name)
    else:
        systemd.start(service_name, append_prefix=append_prefix)
