#!/usr/bin/env python

import re
import os
import pwd
import time
import glob
import json
import shlex
import base64
import socket
import urllib
import urllib2
import hashlib
import tempfile
import subprocess
from functools import wraps
from time import sleep, gmtime, strftime
from distutils.version import LooseVersion

from cloudify import ctx


REST_VERSION = 'v3.1'
PROCESS_POLLING_INTERVAL = 0.1
CLOUDIFY_SOURCES_PATH = '/opt/cloudify/sources'
MANAGER_RESOURCES_HOME = '/opt/manager/resources'
AGENT_ARCHIVES_PATH = '{0}/packages/agents'.format(MANAGER_RESOURCES_HOME)
MANAGER_RESOURCES_SNAPSHOT_PATHS = [
    os.path.join(MANAGER_RESOURCES_HOME, path)
    for path in (
        'blueprints',
        'deployments',
        'uploaded-blueprints',
        'snapshots',
        'plugins',
    )
]

SSL_CERTS_TARGET_DIR = '/etc/cloudify/ssl'
INTERNAL_SSL_CERT_FILENAME = 'cloudify_internal_cert.pem'
INTERNAL_SSL_KEY_FILENAME = 'cloudify_internal_key.pem'
INTERNAL_PKCS12_FILENAME = 'cloudify_internal.p12'
INTERNAL_REST_PORT = 53333

BASE_LOG_DIR = '/var/log/cloudify'

EXTERNAL_SSL_CERTS_SOURCE_DIR = 'resources/ssl'
EXTERNAL_SSL_CERT_FILENAME = 'cloudify_external_cert.pem'
EXTERNAL_SSL_KEY_FILENAME = 'cloudify_external_key.pem'

NGINX_SERVICE_NAME = 'nginx'
DEFAULT_BUFFER_SIZE = 8192
SINGLE_TAR_PREFIX = 'cloudify-manager-resources'

# Upgrade specific parameters
UPGRADE_METADATA_FILE = '/opt/cloudify/upgrade_meta/metadata.json'
AGENTS_ROLLBACK_PATH = '/opt/cloudify/manager-resources/agents_rollback'
ES_UPGRADE_DUMP_PATH = '/tmp/es_upgrade_dump/'

CLOUDIFY_USER = 'cfyuser'
CLOUDIFY_GROUP = 'cfyuser'
CLOUDIFY_HOME_DIR = '/etc/cloudify'
SUDOERS_INCLUDE_DIR = '/etc/sudoers.d'
CLOUDIFY_SUDOERS_FILE = os.path.join(SUDOERS_INCLUDE_DIR, CLOUDIFY_USER)

INTERNAL_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                  INTERNAL_SSL_CERT_FILENAME)
INTERNAL_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                 INTERNAL_SSL_KEY_FILENAME)
CERT_METADATA_FILE_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                       'certificate_metadata')
CLUSTER_DELETE_SCRIPT = '/opt/cloudify/delete_cluster.py'
CFY_EXEC_TEMPDIR_ENVVAR = 'CFY_EXEC_TEMP'


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


def escape_for_systemd(the_string):
    if '\n' in the_string:
        the_string = the_string.replace('\n', '\\\\n\\\n')
        the_string = "\"" + the_string + "\""
    return the_string


def run(command, retries=0, stdin=b'', ignore_failures=False,
        globx=False, shell=False, env=None):
    if isinstance(command, str) and not shell:
        command = shlex.split(command)
    stderr = subprocess.PIPE
    stdout = subprocess.PIPE
    if globx:
        glob_command = []
        for arg in command:
            glob_command.append(glob.glob(arg))
        command = glob_command
    ctx.logger.debug('Running: {0}'.format(command))
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout,
                            stderr=stderr, shell=shell, env=env)
    proc.aggr_stdout, proc.aggr_stderr = proc.communicate(input=stdin)
    if proc.returncode != 0:
        command_str = ' '.join(command)
        if retries:
            ctx.logger.warn('Failed running command: {0}. Retrying. '
                            '({1} left)'.format(command_str, retries))
            proc = run(command, retries - 1)
        elif not ignore_failures:
            msg = 'Failed running command: {0} ({1}).'.format(
                command_str, proc.aggr_stderr)
            raise RuntimeError(msg)
    return proc


def sudo(command, *args, **kwargs):
    if isinstance(command, str):
        command = shlex.split(command)
    if 'env' in kwargs:
        command = ['sudo', '-E'] + command
    else:
        command.insert(0, 'sudo')
    return run(command=command, *args, **kwargs)


def sudo_write_to_file(contents, destination):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(contents)
    return move(path, destination)


def add_entry_to_sudoers(entry, description):
    # Comment out the description and add a N/L after the entry for visibility
    description = '# {0}'.format(description)
    entry = '{0}\n'.format(entry)

    for line in (description, entry):
        # `visudo` handles sudoers file. Setting EDITOR to `tee -a` means that
        # whatever is piped should be appended to the file passed.
        sudo(['/sbin/visudo', '-f', CLOUDIFY_SUDOERS_FILE],
             stdin=line, env={'EDITOR': '/bin/tee -a'})

    valid = sudo(
        ['visudo', '-cf', CLOUDIFY_SUDOERS_FILE],
        ignore_failures=True,
    )
    if valid.returncode != 0:
        ctx.abort_operation(
            "Generated sudoers entry containing \"{entry}\" was "
            "invalid.".format(entry=entry)
        )


def allow_user_to_sudo_command(full_command, description, allow_as='root'):
    entry = '{user}    ALL=({allow_as}) NOPASSWD:{full_command}'.format(
        user=CLOUDIFY_USER,
        allow_as=allow_as,
        full_command=full_command
    )
    add_entry_to_sudoers(entry, description)


def deploy_sudo_command_script(script, description, component=None,
                               allow_as='root'):
    # If passed a component, then script is a relative path, that needs to
    # be downloaded from the scripts folder. Otherwise, it's an absolute path
    if component:
        config_file_temp_destination = os.path.join(tempfile.gettempdir(),
                                                    script)
        ctx.download_resource_and_render(
            os.path.join('components', component, 'scripts', script),
            config_file_temp_destination)
        script = os.path.join('/opt/cloudify/', component, script)
        move(config_file_temp_destination, script)
        chmod('550', script)
        chown('root', CLOUDIFY_GROUP, script)

    ctx.logger.info('Allowing user `{0}` to run `{1}`'
                    .format(CLOUDIFY_USER, script))
    allow_user_to_sudo_command(full_command=script, description=description,
                               allow_as=allow_as)


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
            ctx.abort_operation("Private certificate is expected to begin "
                                "with a line containing 'PRIVATE KEY'.")
    elif private_or_public == 'public':
        public_cert_ok = 'BEGIN CERTIFICATE' in cert.split('\n')[0]
        if public_cert_ok:
            permissions = '444'
        else:
            ctx.abort_operation("Public certificate is expected to begin with "
                                "a line containing 'BEGIN CERTIFICATE'.")
    else:
        ctx.abort_operation("Certificates may only be 'private' or 'public', "
                            "not {0}".format(private_or_public))
    ctx.logger.debug(
        "Deploying {0} SSL certificate in {1} for group {2}".format(
            private_or_public, destination, group))
    sudo_write_to_file(cert, destination)
    ctx.logger.debug('Setting permissions ({0}) and ownership ({1}) of '
                     'SSL certificate at {2}'.format(
                         permissions, ownership, destination))
    chmod(permissions, destination)
    sudo('chown {0} {1}'.format(ownership, destination))


def mkdir(dir, use_sudo=True):
    if os.path.isdir(dir):
        return
    ctx.logger.debug('Creating Directory: {0}'.format(dir))
    cmd = ['mkdir', '-p', dir]
    if use_sudo:
        sudo(cmd)
    else:
        run(cmd)


# idempotent move operation
def move(source, destination, rename_only=False):
    if rename_only:
        sudo(['mv', '-T', source, destination])
    else:
        copy(source, destination)
        remove(source)


def copy(source, destination):
    destination_dir = os.path.dirname(destination)
    if not os.path.exists(destination_dir):
        ctx.logger.debug(
            'Path does not exist: {0}. Creating it...'.format(
                destination_dir))
        sudo(['mkdir', '-p', destination_dir])
    sudo(['cp', '-rp', source, destination])


def remove(path, ignore_failure=False):
    ctx.logger.debug('Removing {0}...'.format(path))
    sudo(['rm', '-rf', path], ignore_failures=ignore_failure)


def _generate_ssl_certificate(ips,
                              cn,
                              cert_filename,
                              key_filename,
                              pkcs12_filename=None):
    """Generate a public SSL certificate and a private SSL key

    :return: The path to the cert and key files on the manager
    """
    mkdir(SSL_CERTS_TARGET_DIR)

    # Remove duplicates from ips
    ips.append('127.0.0.1')
    ips = set(ips)
    metadata_items = ['IP:{0},DNS:{0}'.format(x) for x in ips]
    cert_metadata = '{0},DNS:localhost'.format(
        ','.join(metadata_items))

    ctx.logger.debug('Using certificate metadata: {0}'.format(cert_metadata))

    sudo_write_to_file(cert_metadata, CERT_METADATA_FILE_PATH)
    chmod('664', CERT_METADATA_FILE_PATH)

    cert_path = os.path.join(SSL_CERTS_TARGET_DIR, cert_filename)
    key_path = os.path.join(SSL_CERTS_TARGET_DIR, key_filename)

    with tempfile.NamedTemporaryFile(delete=False) as conf_file:
        conf_file.write("""
[req]
distinguished_name = req_distinguished_name
x509_extensions=SAN
[ req_distinguished_name ]
commonName={cn}
[SAN]
subjectAltName={metadata}
""".format(cn=cn, metadata=cert_metadata))

    sudo([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
        '-keyout', key_path, '-out', cert_path,
        '-days', '36500', '-batch', '-nodes', '-subj',
        '/CN={0}'.format(cn), '-config', conf_file.name
    ])
    # PKCS12 file required for riemann due to JVM
    # While we don't really want the private key in there, not having it
    # causes failures
    # The password is also a bit pointless here since it's in the same place
    # as a readable copy of the certificate and if this path can be written to
    # maliciously then all is lost already.
    if pkcs12_filename:
        pkcs12_path = os.path.join(SSL_CERTS_TARGET_DIR, pkcs12_filename)
        sudo([
            'openssl', 'pkcs12', '-export',
            '-out', pkcs12_path,
            '-in', cert_path,
            '-inkey', key_path,
            '-password', 'pass:cloudify',
        ])
    ctx.logger.info('Generated SSL certificate: {0} and key: {1}'.format(
        cert_filename, key_filename
    ))
    os.remove(conf_file.name)
    return cert_path, key_path


def generate_internal_ssl_cert(ip):
    return _generate_ssl_certificate(
        [ip],
        ip,
        INTERNAL_SSL_CERT_FILENAME,
        INTERNAL_SSL_KEY_FILENAME,
        INTERNAL_PKCS12_FILENAME,
    )


def deploy_or_generate_external_ssl_cert(ips, cn):
    user_provided_cert_path = os.path.join(
        EXTERNAL_SSL_CERTS_SOURCE_DIR,
        EXTERNAL_SSL_CERT_FILENAME
    )
    user_provided_key_path = os.path.join(
        EXTERNAL_SSL_CERTS_SOURCE_DIR,
        EXTERNAL_SSL_KEY_FILENAME
    )
    cert_target_path = os.path.join(
        SSL_CERTS_TARGET_DIR,
        EXTERNAL_SSL_CERT_FILENAME
    )
    key_target_path = os.path.join(
        SSL_CERTS_TARGET_DIR,
        EXTERNAL_SSL_KEY_FILENAME
    )

    try:
        # Try to deploy user provided certificates
        deploy_blueprint_resource(user_provided_cert_path,
                                  cert_target_path,
                                  NGINX_SERVICE_NAME,
                                  user_resource=True,
                                  load_ctx=False)
        deploy_blueprint_resource(user_provided_key_path,
                                  key_target_path,
                                  NGINX_SERVICE_NAME,
                                  user_resource=True,
                                  load_ctx=False)
        ctx.logger.info(
            'Deployed user-provided SSL certificate `{0}` and SSL private '
            'key `{1}`'.format(
                EXTERNAL_SSL_CERT_FILENAME,
                EXTERNAL_SSL_KEY_FILENAME
            )
        )
        return cert_target_path, key_target_path
    except Exception as e:
        if "No such file or directory" in e.stderr:
            ctx.logger.info(
                'Generating SSL certificate `{0}` and SSL private '
                'key `{1}`'.format(
                    EXTERNAL_SSL_CERT_FILENAME,
                    EXTERNAL_SSL_KEY_FILENAME
                )
            )

            return _generate_ssl_certificate(
                ips,
                cn,
                EXTERNAL_SSL_CERT_FILENAME,
                EXTERNAL_SSL_KEY_FILENAME,
            )
        else:
            raise


def write_to_tempfile(contents):
    fd, file_path = tempfile.mkstemp()
    os.write(fd, contents)
    os.close(fd)
    return file_path


def install_python_package(source, venv='', constraints_file=None):
    cmdline = []
    if venv:
        cmdline.append('{0}/bin/pip'.format(venv))
    else:
        cmdline.append('pip')

    cmdline.extend(['install', source, '--upgrade'])

    log_message = 'Installing {0}'.format(source)

    if venv:
        log_message += ' in virtualenv {0}'.format(venv)
    if constraints_file:
        cmdline.extend(['-c', constraints_file])
        log_message += ' using constraints file {0}'.format(constraints_file)

    ctx.logger.info(log_message)

    sudo(cmdline)


def get_file_content(file_path):
    """
    Using sudo to copy the file to a temp folder, to allow access to the file
    even if it's in a restricted directory (e.g. '/root').
    Then, chmoding the file so the current user can read it.
    :param file_path: the path to the file
    :return: the content of the file
    """
    try:
        temp_dir = tempfile.mkdtemp()
        copy(file_path, temp_dir)
        filename = os.path.basename(file_path)
        new_file_copy = os.path.join(temp_dir, filename)
        chmod('644', new_file_copy)
        with open(new_file_copy) as the_file:
            return the_file.read()
    finally:
        if os.path.exists(temp_dir):
            remove(temp_dir)


def curl_download_with_retries(source, destination):
    """Download file using the curl command.

    :param source: Source URL for the file to download
    :typ source: str
    :param destination:
        Path to the directory where the file should be downloaded
    :type destination: str

    """
    curl_cmd = [
        'curl',
        '--retry', '10',
        '--fail',
        '--silent',
        '--show-error',
        '--location', source,
        '--create-dir',
        '--output', destination,
    ]
    ctx.logger.debug('curling: {0}'.format(' '.join(curl_cmd)))
    run(curl_cmd)


def download_file(url, destination=''):
    if not destination:
        fd, destination = tempfile.mkstemp()
        os.remove(destination)
        os.close(fd)

    if not os.path.isfile(destination):
        ctx.logger.info('Downloading {0} to {1}...'.format(
            url, destination))
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
        ctx.logger.debug('File {0} already exists...'.format(destination))
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
    if is_rollback:
        # Resource will be None if only relevant for upgrade and not used
        # on rollback.
        if not resource_file:
            if os.path.isfile(destination):
                # Cleanup
                remove(destination)
            return
    copy(resource_file, dest)


def copy_notice(service):
    """Deploys a notice file to /opt/SERVICENAME_NOTICE.txt"""
    destn = os.path.join('/opt', '{0}_NOTICE.txt'.format(service))
    source = 'components/{0}/NOTICE.txt'.format(service)
    resource_file, dest = resource_factory.create(source, destn, service,
                                                  render=False)
    copy(resource_file, dest)


def remove_notice(service):
    """Remove the notice file /opt/SERVICENAME_NOTICE.txt"""
    path = os.path.join('/opt', '{0}_NOTICE.txt'.format(service))
    remove(path)


def is_port_open(port, host='localhost'):
    """Try to connect to (host, port), return if the port was listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return sock.connect_ex((host, port)) == 0


def wait_for_port(port, host='localhost'):
    """Helper function to wait for a port to open before continuing"""
    counter = 1

    ctx.logger.info('Waiting for {0}:{1} to become available...'.format(
        host, port))

    for tries in range(24):
        if not is_port_open(port, host=host):
            ctx.logger.info(
                '{0}:{1} is not available yet, retrying... '
                '({2}/24)'.format(host, port, counter))
            time.sleep(2)
            counter += 1
            continue
        ctx.logger.info('{0}:{1} is open!'.format(host, port))
        return
    ctx.abort_operation('Failed to connect to {0}:{1}...'.format(host, port))


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
    downloaded, a re-download will not take place and rather an
    installation will be attempted, which will obviously fail since
    the rpm file is incomplete.
    ALSO NOTE: you cannot provide `yum_install` with a space
    separated array of packages as you can with `yum install`. You must
    provide one package per invocation.
    """
    # source is a url
    if source.startswith(('http', 'https', 'ftp')):
        filename = get_file_name_from_url(source)
        source_name, ext = os.path.splitext(filename)
    # source is just the name of the file
    elif source.endswith('.rpm'):
        source_name, ext = os.path.splitext(source)
    # source is the name of a yum-repo based package name
    else:
        source_name, ext = source, ''
    source_path = source_name

    if ext.endswith('.rpm'):
        source_path = download_cloudify_resource(source, service_name)

        rpm_handler = RpmPackageHandler(source_path)
        ctx.logger.info(
            'Checking whether {0} is already installed...'.format(
                source_path))
        if rpm_handler.is_rpm_installed():
            ctx.logger.debug('Package {0} is already installed.'.format(
                source))
            return

        # removes any existing versions of the package that do not match
        # the provided package source version
        rpm_handler.remove_existing_rpm_package()
    else:
        installed = run(['yum', '-q', 'list', 'installed', source_path],
                        ignore_failures=True)
        if installed.returncode == 0:
            ctx.logger.debug('Package {0} is already installed.'.format(
                source))
            return
    ctx.logger.info('yum installing {0}...'.format(source_path))
    sudo(['yum', 'install', '-y', source_path])


def yum_remove(package, ignore_failures=False):
    ctx.logger.info('yum removing {0}...'.format(package))
    try:
        sudo(['yum', 'remove', '-y', package])
    except BaseException:
        msg = 'Package `{0}` may not been removed successfully!'
        if not ignore_failures:
            ctx.logger.error(msg)
            raise
        ctx.logger.warn(msg)


def get_filepath_from_pkg_name(filename, raise_if_not_found=False):
    local_filepath_list = \
        [fn for fn in glob.glob(os.path.join(CLOUDIFY_SOURCES_PATH, filename))
         if not os.path.basename(fn).startswith(SINGLE_TAR_PREFIX)]
    if not local_filepath_list:
        if raise_if_not_found:
            raise IOError('Local resource not found: {0}'.format(filename))
        ctx.abort_operation("File: {0} does not exist in sources path: {1}".
                            format(filename, CLOUDIFY_SOURCES_PATH))
    if len(local_filepath_list) > 1:
        ctx.abort_operation("More than one file: {0} found in sources path:"
                            " {1}".format(filename, CLOUDIFY_SOURCES_PATH))
    local_filepath = ''.join(local_filepath_list[0])
    ctx.logger.debug("File exists in sources path: {0}".format(local_filepath))

    return local_filepath


class RpmPackageHandler(object):

    def __init__(self, source_path):
        self.source_path = source_path

    def remove_existing_rpm_package(self):
        """Removes any version that satisfies the package name of the given
        source path.
        """
        package_name = self.get_rpm_package_name()
        if self._is_package_installed(package_name):
            ctx.logger.debug(
                'Removing existing package sources for package '
                'with name: {0}'.format(package_name))
            sudo(['rpm', '--noscripts', '-e', package_name])

    @staticmethod
    def _is_package_installed(name):
        installed = run(['rpm', '-q', name], ignore_failures=True)
        if installed.returncode == 0:
            return True
        return False

    def is_rpm_installed(self):
        """Returns true if provided rpm is already installed.
        """
        src_query = run(['rpm', '-qp', self.source_path])
        source_name = src_query.aggr_stdout.rstrip('\n\r')

        return self._is_package_installed(source_name)

    def get_rpm_package_name(self):
        """Returns the package name according to the info provided in the
        source file.
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
        return sudo(systemctl_cmd, retries=retries,
                    ignore_failures=ignore_failure)

    def configure(self, service_name, render=True, tmpfiles=False):
        """This configures systemd for a specific service.

        It requires that two files are present for each service one containing
        the environment variables and one contains the systemd config.
        All env files will be named "cloudify-SERVICENAME".
        All systemd config files will be named "cloudify-SERVICENAME.service".

        If `tmpfiles` is True, the directory
        `components/{service_name}/tmpfiles.d` must exist and contain the file
        `cloudify-{service_name}.conf`. This will be deployed to
        `/usr/lib/tmpfiles.d`.
        """
        sid = 'cloudify-{0}'.format(service_name)
        env_dst = "/etc/sysconfig/{0}".format(sid)
        srv_dst = "/usr/lib/systemd/system/{0}.service".format(sid)
        env_src = "components/{0}/config/{1}".format(service_name, sid)
        srv_src = "components/{0}/config/{1}.service".format(service_name, sid)

        ctx.logger.debug('Deploying systemd EnvironmentFile...')
        deploy_blueprint_resource(env_src, env_dst, service_name,
                                  render=render)
        ctx.logger.debug('Deploying systemd .service file...')
        deploy_blueprint_resource(srv_src, srv_dst, service_name,
                                  render=render)
        ctx.logger.debug('Enabling systemd .service...')
        self.systemctl('enable', '{0}.service'.format(sid))

        if tmpfiles:
            tmp_dst = "/usr/lib/tmpfiles.d/{0}.conf".format(sid)
            tmp_src = "components/{0}/config/tmpfiles.d/{1}.conf".format(
                service_name, sid)

            ctx.logger.debug('Deploying tmpfiles.d file...')
            deploy_blueprint_resource(
                tmp_src, tmp_dst, service_name, render=render)
            sudo(['systemd-tmpfiles', '--create'])

        self.systemctl('daemon-reload')

    def remove(self, service_name):
        """Stop and disable the service, and then delete its data
        """
        self.stop(service_name, ignore_failure=True)
        self.disable(service_name, ignore_failure=True)
        remove(self.get_service_file_path(service_name))
        remove(self.get_vars_file_path(service_name))

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
        ctx.logger.debug('Enabling systemd service {0}...'.format(
            full_service_name))
        self.systemctl('enable', full_service_name, retries)

    def disable(self, service_name, retries=0, append_prefix=True,
                ignore_failure=False):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        ctx.logger.debug('Disabling systemd service {0}...'.format(
            full_service_name))
        self.systemctl('disable', full_service_name, retries,
                       ignore_failure=ignore_failure)

    def start(self, service_name, retries=0, append_prefix=True):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        ctx.logger.debug('Starting systemd service {0}...'.format(
            full_service_name))
        self.systemctl('start', full_service_name, retries)

    def stop(self, service_name, retries=0, append_prefix=True,
             ignore_failure=False):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        ctx.logger.debug('Stopping systemd service {0}...'.format(
            full_service_name))
        self.systemctl('stop', full_service_name, retries,
                       ignore_failure=ignore_failure)

    def restart(self,
                service_name,
                retries=0,
                ignore_failure=False,
                append_prefix=True):
        full_service_name = self._get_full_service_name(service_name,
                                                        append_prefix)
        self.systemctl('restart', full_service_name, retries,
                       ignore_failure=ignore_failure)

    def is_alive(self, service_name, append_prefix=True):
        service_name = self._get_full_service_name(service_name, append_prefix)
        result = self.systemctl('status', service_name, ignore_failure=True)
        return result.returncode == 0

    def verify_alive(self, service_name, append_prefix=True):
        if self.is_alive(service_name, append_prefix):
            ctx.logger.debug('{0} is running'.format(service_name))
        else:
            ctx.abort_operation('{0} is not running'.format(service_name))

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
    ctx.logger.debug('Replacing {0} with {1} in {2}...'.format(
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
        ctx.logger.debug('SELinux is enforcing, setting permissive state...')
        sudo(['setenforce', 'permissive'])
        replace_in_file(
            'SELINUX=enforcing',
            'SELINUX=permissive',
            '/etc/selinux/config')
    else:
        ctx.logger.debug('SELinux is not enforced.')


def get_rabbitmq_endpoint_ip(endpoint=None):
    """Gets the rabbitmq endpoint IP, using the manager IP if the node
    property is blank.
    """
    if endpoint:
        return endpoint
    return ctx.instance.host_ip


def create_service_user(user, group, home):
    """Creates a user.

    It will not create the home dir for it and assume that it already exists.
    This user will only be created if it didn't already exist.
    """
    ctx.logger.info('Checking whether user {0} exists...'.format(user))
    try:
        pwd.getpwnam(user)
        ctx.logger.debug('User {0} already exists...'.format(user))
    except KeyError:
        ctx.logger.info('Creating group {group} if it does not exist'.format(
            group=group,
        ))
        # --force in groupadd causes it to return true if the group exists.
        # Other behaviour changes don't affect this basic use of the command.
        sudo(['groupadd', '--force', group])

        ctx.logger.info('Creating user {0}, home: {1}...'.format(
            user, home))
        sudo([
            'useradd',
            '--shell', '/sbin/nologin',
            '--home-dir', home, '--no-create-home',
            '--system',
            '--no-user-group',
            '--gid', group,
            user,
        ])


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

    ctx.logger.debug('Deploying logrotate config...')
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


def remove_logrotate(service_name):
    ctx.logger.debug('Removing logrotate config...')
    logrotated_path = '/etc/logrotate.d'
    config_file_destination = os.path.join(logrotated_path, service_name)
    remove(config_file_destination)


def chmod(mode, path, recursive=False):
    ctx.logger.debug('chmoding {0}: {1}'.format(path, mode))
    command = ['chmod']
    if recursive:
        command.append('-R')
    command += [mode, path]
    sudo(command)


def chown(user, group, path):
    ctx.logger.debug('chowning {0} by {1}:{2}...'.format(
        path, user, group))
    sudo(['chown', '-R', '{0}:{1}'.format(user, group), path])


def ln(source, target, params=None):
    ctx.logger.debug('Linking {0} to {1} with params {2}'.format(
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


def untar(source,
          destination=None,
          skip_old_files=False,
          unique_tmp_dir=False):
    # TODO: use tarfile instead
    if not destination:
        destination = tempfile.mkdtemp() if unique_tmp_dir else '/tmp'
    ctx.logger.debug('Extracting {0} to {1}...'.format(
        source, destination))
    tar_command = ['tar', '-xzvf', source, '-C', destination, '--strip=1']
    if skip_old_files:
        tar_command.append('--skip-old-files')
    sudo(tar_command)
    return destination


def validate_md5_checksum(resource_path, md5_checksum_file_path):
    ctx.logger.info('Validating md5 checksum for {0}'.format(
        resource_path))
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


def load_manager_config_prop(prop_name):
    ctx.logger.debug('Loading {0} configuration'.format(prop_name))
    manager_props = ctx_factory.get('manager-config')
    return json.dumps(manager_props[prop_name])


def _is_upgrade():
    # This file is uploaded as part of the upgrade/rollback command.
    status_file_path = '/opt/cloudify/_workflow_state.json'
    if os.path.isfile(status_file_path):
        ctx.logger.debug('Loading workflow status file: {0}'.format(
            status_file_path))
        with open(status_file_path) as f:
            status = json.load(f)
        return status['is_upgrade']
    else:
        return None


is_upgrade = _is_upgrade()
# is_upgrade can be None or false. If is_upgrade is None,
# we are in install, else Rollback.
is_rollback = is_upgrade is False


def repetitive(condition_func,
               timeout=15,
               interval=3,
               timeout_msg='timed out',
               *args,
               **kwargs):

    deadline = time.time() + timeout
    while True:
        if time.time() > deadline:
            ctx.abort_operation(timeout_msg)
        if condition_func(*args, **kwargs):
            return
        time.sleep(interval)


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
    def create(self, service_name):
        """A Factory used to create a local copy of the node properties used
        upon deployment. This copy will allows to later reuse the properties
        for upgrade/rollback purposes. The node ctx properties will be set
        according to the node property named 'use_existing_on_upgrade'.

        :param service_name: The service name
        :return: The relevant ctx node properties dict.
        """
        if is_upgrade:
            self._archive_properties(service_name)
            ctx_props = self._load_ctx_properties(service_name)
            self._write_props_to_file(ctx_props, service_name)
        elif is_rollback:
            self._restore_properties(service_name)
            ctx_props = self.get(service_name)
        else:
            ctx_props = ctx.node.properties.get_all()
            self._write_props_to_file(ctx_props, service_name)

        return ctx_props

    def get(self, service_name):
        """Get node properties by service name.

        :param service_name: The service name.
        :return: The relevant ctx node properties dict.
        """
        return self._load_properties(service_name)

    def _write_props_to_file(self, ctx_props, service_name):
        dest_file_path = self._get_props_file_path(service_name)
        ctx.logger.debug('Saving {0} input configuration to {1}'.format(
            service_name, dest_file_path))
        write_to_json_file(ctx_props, dest_file_path)

    def _restore_properties(self, service_name):
        """Restore previously used node properties.
        """
        rollback_props_path = self._get_rollback_props_file_path(
            service_name)
        if os.path.isfile(rollback_props_path):
            ctx.logger.debug(
                'Restoring service input properties for service '
                '{0}'.format(service_name))
            rollback_dir = self.get_rollback_properties_dir(service_name)
            install_dir = self._get_properties_dir(service_name)
            if os.path.isdir(install_dir):
                remove(install_dir)
            move(rollback_dir, install_dir, rename_only=True)

    def _archive_properties(self, service_name):
        """Archive previously used node properties. These properties will be
        used for rollback purposes.
        """
        rollback_props_path = self._get_rollback_props_file_path(
            service_name)
        if not os.path.isfile(rollback_props_path):
            ctx.logger.debug('Archiving previous input properties for '
                             'service {0}'.format(service_name))
            mkdir(os.path.dirname(rollback_props_path))
            properties_file_path = self._get_props_file_path(service_name)
            move(properties_file_path, rollback_props_path)

    def _get_props_file_path(self, service_name):
        base_service_dir = self._get_properties_dir(service_name)
        dest_file_path = os.path.join(base_service_dir,
                                      self.PROPERTIES_FILE_NAME)
        return dest_file_path

    def _get_rollback_props_file_path(self, service_name):
        base_service_dir = self.get_rollback_properties_dir(service_name)
        dest_file_path = os.path.join(base_service_dir,
                                      self.PROPERTIES_FILE_NAME)
        return dest_file_path

    def _load_ctx_properties(self, service_name):
        node_props = ctx.node.properties.get_all()
        # Use existing property configuration during upgrade
        use_existing = node_props.get('use_existing_on_upgrade')
        if use_existing:
            existing_props = self.load_rollback_props(service_name)
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

    def get_rollback_properties_dir(self, service_name):
        return os.path.join(self.BASE_PROPERTIES_PATH,
                            service_name,
                            self.ROLLBACK_NODE_PROPS_DIR_NAME)

    def _load_properties(self, service_name):
        props_file = self._get_props_file_path(service_name)
        with open(props_file) as f:
            return json.load(f)

    # This function should only be used when during upgrade workflow execution
    def load_rollback_props(self, service_name):
        upgrade_props_file = self._get_rollback_props_file_path(service_name)
        if os.path.isfile(upgrade_props_file):
            with open(upgrade_props_file) as f:
                return json.load(f)
        else:
            ctx.logger.debug('Failed loading rollback properties. '
                             'Properties file does not exist.')


class BlueprintResourceFactory(object):

    BASE_RESOURCES_PATH = '/opt/cloudify'
    RESOURCES_DIR_NAME = 'resources'
    RESOURCES_ROLLBACK_DIR_NAME = 'resources_rollback'
    RESOURCES_JSON_FILE = '__resources.json'

    def create(self, source, destination, service_name, user_resource=False,
               source_resource=False, render=True, load_ctx=True):
        """A Factory used to create a local copy of a resource upon deployment.
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
        if is_upgrade:
            self._archive_resources(service_name)
        elif is_rollback:
            self._restore_resources(service_name)
            destination = self._get_dest_by_resources_json(service_name,
                                                           resource_name)
            if not destination:
                # This resource was not used prior to upgrade.
                return None, None

        # The local path is decided according to whether we are in upgrade
        local_resource_path = self._get_local_file_path(service_name,
                                                        resource_name)

        if self._is_download_required(local_resource_path, render):
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
            resources_props = self._get_resources_json(service_name)
            # update the resources.json
            if resource_name not in resources_props.keys():
                resources_props[resource_name] = destination
                self._set_resources_json(resources_props, service_name)
        return local_resource_path, destination

    @staticmethod
    def local_resource_exists(filename):
        try:
            get_filepath_from_pkg_name(filename, raise_if_not_found=True)
            return True
        except IOError:
            return False

    @staticmethod
    def _is_download_required(local_resource_path, is_render):
        result = False
        if not os.path.isfile(local_resource_path):
            result = True
        # rendered resources should be re-rendered if in upgrade.
        if is_render and is_upgrade:
            result = True
        return result

    def _get_dest_by_resources_json(self, service_name, resource_name):
        resource_mapping = self._get_resources_json(service_name)
        return resource_mapping.get(resource_name)

    def _download_user_resource(self, source, dest, resource_name,
                                service_name, render=True, load_ctx=True):
        if is_upgrade:
            install_props = self._get_rollback_resources_json(service_name)
            existing_resource_path = install_props.get(resource_name, '')
            if os.path.isfile(existing_resource_path):
                ctx.logger.debug('Using existing resource for {0}'.format(
                    resource_name))
                # update the resource file we hold that might have changed
                install_resource = self._get_local_file_path(
                    service_name, resource_name)
                copy(existing_resource_path, install_resource)
            else:
                ctx.logger.debug('User resource {0} not found on {1}'.format(
                    resource_name, dest))

        if not os.path.isfile(dest):
            if render:
                self._download_resource_and_render(source, dest, service_name,
                                                   load_ctx=load_ctx)
            else:
                self._download_resource(source, dest)

    @staticmethod
    def _download_resource(source, dest):
        resource_name = os.path.basename(dest)
        ctx.logger.info('Downloading resource {0} to {1}'.format(
            resource_name, dest))
        tmp_file = ctx.download_resource(source)
        move(tmp_file, dest)

    def _download_resource_and_render(self, source, dest, service_name,
                                      load_ctx):
        resource_name = os.path.basename(dest)
        ctx.logger.debug('Downloading resource {0} to {1}'.format(
            resource_name, dest))
        if load_ctx:
            params = self._load_node_props(service_name)
            tmp_file = ctx.download_resource_and_render(source, '', params)
        else:
            # rendering will be possible only for runtime properties
            tmp_file = ctx.download_resource_and_render(source, '')
        move(tmp_file, dest)

    @staticmethod
    def _download_source_resource(source, local_resource_path):
        is_url = source.startswith(('http://', 'https://', 'ftp://',
                                    'file://'))
        filename = get_file_name_from_url(source) if is_url else source
        is_manager_package = filename.startswith(SINGLE_TAR_PREFIX)
        if is_manager_package or is_url:
            local_filepath = os.path.join(CLOUDIFY_SOURCES_PATH, filename)
        else:
            local_filepath = get_filepath_from_pkg_name(filename)

        if is_url:
            if not os.path.isfile(local_filepath):
                tmp_path = download_file(source)
            elif os.path.isfile(local_filepath) and not is_manager_package:
                remove(local_filepath)
                tmp_path = download_file(source)
            else:
                tmp_path = local_filepath
        # source is just the name of the file, to be retrieved from
        # the manager resources package
        else:
            tmp_path = local_filepath
        ctx.logger.debug('Saving {0} under {1}'.format(
            tmp_path, local_resource_path))
        move(tmp_path, local_resource_path)

    @staticmethod
    def _load_node_props(service_name):
        node_props = ctx_factory.get(service_name)
        return {'node': {'properties': node_props}}

    def _is_cloudify_pkg(self,  filename):
        """Cloudify packages start with 'cloudify' or include '-agent_'

        and end with one of the suffix '.rpm', '.tar.gz', '.tgz', '.exe'.
        The function who calls this function wish to gel all cloudify
        packages except of single tar package.
        """

        if (filename.startswith('cloudify')
            or filename.find('-agent_') != -1) \
                and not filename.startswith(SINGLE_TAR_PREFIX) \
                and filename.endswith(('.rpm', '.tar.gz', '.tgz', '.exe')):
            return True
        else:
            return False

    def _get_local_file_path(self, service_name, resource_name):
        base_service_res_dir = self.get_resources_dir(service_name)

        if self._is_cloudify_pkg(resource_name):
            local_filepath = get_filepath_from_pkg_name(resource_name)
            dest_file_path = os.path.join(base_service_res_dir,
                                          os.path.basename(local_filepath))
        else:
            dest_file_path = os.path.join(base_service_res_dir, resource_name)

        return dest_file_path

    def _get_resources_json(self, service_name):
        resources_json = self._get_local_file_path(service_name,
                                                   self.RESOURCES_JSON_FILE)
        if os.path.isfile(resources_json):
            with open(resources_json) as f:
                return json.load(f)
        return {}

    def _set_resources_json(self, resources_dict, service_name):
        resources_json = self._get_local_file_path(service_name,
                                                   self.RESOURCES_JSON_FILE)
        write_to_json_file(resources_dict, resources_json)

    def _restore_resources(self, service_name):
        rollback_dir = self.get_rollback_resources_dir(service_name)
        if not os.path.isdir(rollback_dir):
            # node resources have already been moved.
            return
        # restore all rollback resources to their original destination
        ctx.logger.debug('Restoring service {0} configuration resources...'
                         .format(service_name))
        self._restore_service_configuration(rollback_dir, service_name)

        resources_dir = self.get_resources_dir(service_name)
        if os.path.isdir(resources_dir):
            remove(resources_dir)
        move(rollback_dir, resources_dir, rename_only=True)

    def _restore_service_configuration(self, rollback_dir, service_name):
        resources_mapping = self._get_rollback_resources_json(service_name)
        for rollback_resource, destination in resources_mapping.items():
            # Destination will match rollback resource name only if destination
            # was not provided on install/rollback
            if destination != rollback_resource:
                resource_local_path = os.path.join(rollback_dir,
                                                   rollback_resource)
                copy(resource_local_path, destination)

    def _archive_resources(self, service_name):
        rollback_dir = self.get_rollback_resources_dir(service_name)
        if os.path.isdir(rollback_dir):
            if os.listdir(rollback_dir):
                # resources have already been archived.
                return

        resources_dir = self.get_resources_dir(service_name)
        if os.path.isdir(resources_dir):
            ctx.logger.debug('Archiving service {0} node resources...'
                             .format(service_name))
            move(resources_dir, rollback_dir, rename_only=True)

    def get_resources_dir(self, service_name):
        return os.path.join(self.BASE_RESOURCES_PATH,
                            service_name,
                            self.RESOURCES_DIR_NAME)

    def get_rollback_resources_dir(self, service_name):
        return os.path.join(self.BASE_RESOURCES_PATH,
                            service_name,
                            self.RESOURCES_ROLLBACK_DIR_NAME)

    def _get_rollback_resources_json(self, service_name):
        rollback_dir = self.get_rollback_resources_dir(service_name)
        rollback_json = os.path.join(rollback_dir, self.RESOURCES_JSON_FILE)
        with open(rollback_json) as f:
            return json.load(f)


resource_factory = BlueprintResourceFactory()
ctx_factory = CtxPropertyFactory()


def start_service(service_name, append_prefix=True, ignore_restart_fail=False):
    if is_upgrade or is_rollback:
        systemd.restart(service_name,
                        ignore_failure=ignore_restart_fail,
                        append_prefix=append_prefix)
    else:
        systemd.start(service_name, append_prefix=append_prefix)


def http_request(url,
                 data=None,
                 method='PUT',
                 headers=None,
                 timeout=None,
                 should_fail=False):
    headers = headers or {}
    request = urllib2.Request(url, data=data, headers=headers)
    request.get_method = lambda: method
    try:
        if timeout:
            return urllib2.urlopen(request, timeout=timeout)
        return urllib2.urlopen(request)
    except urllib2.URLError as e:
        if not should_fail:
            ctx.logger.error('Failed to {0} {1} (reason: {2})'.format(
                method, url, e.reason))


def wait_for_workflow(deployment_id,
                      workflow_id,
                      url_prefix='http://localhost/api/{0}'.format(
                          REST_VERSION)):
    headers = create_maintenance_headers()
    params = urllib.urlencode(dict(deployment_id=deployment_id))
    endpoint = '{0}/executions'.format(url_prefix)
    url = endpoint + '?' + params
    res = http_request(
        url,
        method='GET',
        headers=headers)
    res_content = res.readlines()
    json_res = json.loads(res_content[0])
    for execution in json_res['items']:
        if execution['workflow_id'] == workflow_id:
            execution_status = execution['status']
            if execution_status == 'terminated':
                return True
            elif execution_status == 'failed':
                ctx.abort_operation('Execution with id {0} failed'.
                                    format(execution['id']))
    return False


def _wait_for_execution(execution_id, headers):
    poll_interval = 2
    while True:
        res = _list_executions_with_retries(headers, execution_id)
        content = json.loads(res.readlines()[0])
        execution_item = content['items'][0]
        execution_status = execution_item['status']
        if execution_status == 'terminated':
            return True
        elif execution_status == 'failed':
            ctx.abort_operation('Execution with id {0} failed'.
                                format(execution_id))
        sleep(poll_interval)


def _list_executions_with_retries(headers, execution_id, retries=6):
    count = 0
    err = 'Failed listing existing executions.'
    url = 'http://localhost/api/{0}/executions?' \
          '_include_system_workflows=true&id={1}'.format(REST_VERSION,
                                                         execution_id)
    while count != retries:
        res = http_request(url, method='GET', headers=headers)
        if res.code != 200:
            err = 'Failed listing existing executions. Message: {0}' \
                .format(res.readlines())
            ctx.logger.error(err)
            sleep(2)
        else:
            return res
    ctx.abort_operation(err)


def create_maintenance_headers(upgrade_props=True):
    headers = {'X-BYPASS-MAINTENANCE': 'True',
               'tenant': 'default_tenant'}
    auth_props = get_auth_headers(upgrade_props)
    headers.update(auth_props)
    return headers


def get_auth_headers(upgrade_props):
    headers = {}
    if upgrade_props:
        manager_config = ctx_factory.get('manager-config')
    else:
        manager_config = ctx_factory.load_rollback_props('manager-config')

    username = manager_config['security'].get('admin_username')
    password = manager_config['security'].get('admin_password')
    headers.update({'Authorization':
                    'Basic ' + base64.b64encode('{0}:{1}'.format(
                        username, password))})
    return headers


def create_upgrade_snapshot():
    if _get_upgrade_data().get('snapshot_id'):
        ctx.logger.debug('Upgrade snapshot already created.')
        return
    snapshot_id = _generate_upgrade_snapshot_id()
    url = 'http://localhost/api/{0}/snapshots/{1}'.format(REST_VERSION,
                                                          snapshot_id)
    data = json.dumps({'include_metrics': 'true',
                       'include_credentials': 'true'})
    headers = create_maintenance_headers(upgrade_props=False)
    req_headers = headers.copy()
    req_headers.update({'Content-Type': 'application/json'})
    ctx.logger.debug('Creating snapshot with ID {0}'.format(snapshot_id))
    res = http_request(url, data=data, method='PUT', headers=req_headers)
    if res.code != 201:
        err = 'Failed creating snapshot {0}. Message: {1}'\
            .format(snapshot_id, res.readlines())
        ctx.logger.error(err)
        ctx.abort_operation(err)
    execution_id = json.loads(res.readlines()[0])['id']
    _wait_for_execution(execution_id, headers)
    ctx.logger.debug('Snapshot with ID {0} created successfully'
                     .format(snapshot_id))
    ctx.logger.debug('Setting snapshot info to upgrade metadata in {0}'
                     .format(UPGRADE_METADATA_FILE))
    _set_upgrade_data(snapshot_id=snapshot_id)


def restore_upgrade_snapshot():
    snapshot_id = _get_upgrade_data()['snapshot_id']
    url = 'http://localhost/api/{0}/snapshots/{1}/restore'.format(REST_VERSION,
                                                                  snapshot_id)
    data = json.dumps({'recreate_deployments_envs': 'false',
                       'force': 'true'})
    headers = create_maintenance_headers(upgrade_props=True)
    req_headers = headers.copy()
    req_headers.update({'Content-Type': 'application/json'})
    ctx.logger.debug('Restoring snapshot with ID {0}'.format(snapshot_id))
    res = http_request(url, data=data, method='POST', headers=req_headers)
    if res.code != 200:
        err = 'Failed restoring snapshot {0}. Message: {1}' \
            .format(snapshot_id, res.readlines())
        ctx.logger.error(err)
        ctx.abort_operation(err)
    execution_id = json.loads(res.readlines()[0])['id']
    _wait_for_execution(execution_id, headers)
    ctx.logger.info('Snapshot with ID {0} restored successfully'
                    .format(snapshot_id))


def _generate_upgrade_snapshot_id():
    url = 'http://localhost/api/{0}/version'.format(REST_VERSION)
    auth_headers = get_auth_headers(upgrade_props=False)
    res = http_request(url, method='GET', headers=auth_headers)
    if res.code != 200:
        err = 'Failed extracting current manager version. Message: {0}' \
            .format(res.readlines())
        ctx.abort_operation(err)
    curr_time = strftime("%Y-%m-%d_%H:%M:%S", gmtime())
    version_data = json.loads(res.read())
    snapshot_upgrade_name = 'upgrade_snapshot_{0}_build_{1}_{2}'.format(
        version_data['version'], version_data['build'], curr_time)

    return snapshot_upgrade_name


def _set_upgrade_data(**kwargs):
    mkdir(os.path.dirname(UPGRADE_METADATA_FILE))
    upgrade_data = {}
    if os.path.isfile(UPGRADE_METADATA_FILE):
        upgrade_data = _get_upgrade_data()
    upgrade_data.update(**kwargs)
    write_to_json_file(upgrade_data, UPGRADE_METADATA_FILE)


# upgrade data contains info related to the upgrade process e.g  'snapshot_id'
def _get_upgrade_data():
    if os.path.exists(UPGRADE_METADATA_FILE):
        with open(UPGRADE_METADATA_FILE) as f:
            return json.load(f)
    return {}


@retry((IOError, ValueError))
def check_http_response(url, predicate=None, **request_kwargs):
    req = urllib2.Request(url, **request_kwargs)
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError as e:
        # HTTPError can also be used as a non-200 response. Pass this
        # through to the predicate function, so it can decide if a
        # non-200 response is fine or not.
        response = e

    if predicate is not None and not predicate(response):
        raise ValueError('Failed opening url {0} ({1})'.format(url, response))
    return response


def verify_service_http(service_name, url, *args, **kwargs):
    try:
        return check_http_response(url, *args, **kwargs)
    except (IOError, ValueError) as e:
        ctx.abort_operation('{0} error: {1}: {2}'.format(service_name, url, e))


def validate_upgrade_directories(service_name):
    try:
        ctx_factory.get(service_name)
    except IOError:
        ctx.abort_operation('Service {0} has no properties file'.format(
            service_name))

    if not os.path.exists(resource_factory.get_resources_dir(service_name)):
        ctx.abort_operation('Resources directory does not exist for '
                            'service {0}'.format(service_name))


def parse_jvm_heap_size(heap_size):
    if heap_size.endswith('g'):
        multiplier = 10**3
    elif heap_size.endswith('m'):
        multiplier = 1
    else:
        raise ValueError(heap_size)
    return int(heap_size[:-1]) * multiplier


def changed_upgrade_properties(service_name):
    """Delta of the service's upgrade and install properties.

    Look up the upgrade and install properties for the service, return a dict
    of {property_name: (original_value, upgrade_value)}
    """
    install_properties = ctx_factory.get(service_name)
    upgrade_properties = ctx.node.properties.get_all()
    if upgrade_properties.get('use_existing_on_upgrade'):
        return {}
    changed = {}
    for property_name, original_value in install_properties.items():
        changed_value = upgrade_properties.get(property_name)
        if original_value != changed_value:
            changed[property_name] = (original_value, changed_value)
    return changed


def verify_immutable_properties(service_name, properties):
    """Check that the given properties didn't change in service upgrade.

    Some properties must not change during a manager upgrade. Verify that
    properties named by the given list didn't change between the install
    and upgrade inputs.
    """
    all_changed_properties = changed_upgrade_properties(service_name)
    changed_properties = set(properties) & set(all_changed_properties)

    if changed_properties:
        # format the error: include the changed property name, the value before
        # and the value after
        descr_parts = []
        for changed_property_name in changed_properties:
            part = '{0} (original: {1}, changed: {2})'.format(
                changed_property_name,
                *all_changed_properties[changed_property_name])
            descr_parts.append(part)

        ctx.abort_operation('{0} properties must not change during a manager '
                            'upgrade! Changed properties: {1}'.format(
                                service_name, ','.join(descr_parts)))


def _is_version_greater_than_curr(new_version):
    version_url = 'http://localhost/api/{0}/version'.format(REST_VERSION)
    version_res = http_request(version_url, method='GET')
    if version_res.code != 200:
        ctx.abort_operation('Failed retrieving manager version')
    curr_version = json.loads(version_res.readlines()[0])['version']
    ctx.logger.debug('Current manager version is {0}.'.format(curr_version))
    return LooseVersion(new_version) > LooseVersion(curr_version)


# rollback resources will be removed only if the last upgrade passed
# successfully and the 'upgrade to' version is greater than the current version
# This function MUST be invoked by the first node and before upgrade snapshot
# is created.
def clean_rollback_resources_if_necessary():
    if not is_upgrade:
        return

    new_version = ctx.node.properties['manager_version']
    is_upgrade_version = _is_version_greater_than_curr(new_version)
    # The 'upgrade_success' flag will only be set if the previous upgrade
    # execution ended successfully
    latest_workflow_result = _get_upgrade_data().get('upgrade_success')
    if latest_workflow_result and is_upgrade_version:
        ctx.logger.debug('Preparing manager for upgrade...')
        # Clean manager rollback resources to make room for the new upgrade.
        _clean_rollback_data()


def clean_upgrade_resources_if_necessary():
    if is_upgrade:
        if os.path.isdir(ES_UPGRADE_DUMP_PATH):
            ctx.logger.debug('Removing ES provider context dump...')
            remove(ES_UPGRADE_DUMP_PATH)


def _clean_rollback_data():
    walk_dir_info = os.walk('/opt/cloudify')
    ctx.logger.debug('Removing any existing rollback resources...')
    for details in walk_dir_info:
        dir_path = details[0]
        dir_name = os.path.basename(dir_path)
        if dir_name in ('node_properties_rollback', 'resources_rollback'):
            ctx.logger.debug(
                'Removing existing rollback resources from {0}...'.format(
                    dir_path))
            remove(dir_path)
    if os.path.isdir(AGENTS_ROLLBACK_PATH):
        ctx.logger.debug('Removing rollback agents...')
        remove(AGENTS_ROLLBACK_PATH)
    if os.path.isfile(UPGRADE_METADATA_FILE):
        ctx.logger.debug('Removing upgrade metadata...')
        remove(UPGRADE_METADATA_FILE)


def set_upgrade_success_in_upgrade_meta():
    _set_upgrade_data(upgrade_success=True)


def remove_component(runtime_props):
    service_name = runtime_props['service_name']
    ctx.logger.info('Uninstalling {0}'.format(service_name))

    systemd.remove(service_name)
    remove_notice(service_name)
    remove_logrotate(service_name)

    packages_to_remove = runtime_props.get('packages_to_remove', [])
    for package in packages_to_remove:
        yum_remove(package, ignore_failures=True)

    files_to_remove = runtime_props.get('files_to_remove', [])
    for f in files_to_remove:
        remove(f)

    user = runtime_props.get('service_user')
    if user:
        sudo(['userdel', '--force', user], ignore_failures=True)

    group = runtime_props.get('service_group')
    if group:
        sudo(['groupdel', group], ignore_failures=True)


def extend_runtime_properties_list(runtime_props, key_name, new_list):
    """Extend a list in the runtime properties
    list.extend doesn't call __setitem__, so we need to do it explicitly
    """
    list_to_extend = runtime_props.get(key_name, [])
    list_to_extend.extend(new_list)
    runtime_props[key_name] = list_to_extend


def set_service_as_cloudify_service(runtime_props):
    """Set the cloudify user and group as the user/group of a service"""

    runtime_props['service_user'] = CLOUDIFY_USER
    runtime_props['service_group'] = CLOUDIFY_GROUP


def delete_cluster_component(component):
    """If the given cluster component exists, teardown it."""
    if os.path.exists(CLUSTER_DELETE_SCRIPT):
        sudo(['/usr/bin/env', 'python', CLUSTER_DELETE_SCRIPT,
              '--component', component])


def get_exec_tempdir():
    return os.environ.get(CFY_EXEC_TEMPDIR_ENVVAR) or tempfile.gettempdir()
