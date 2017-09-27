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
from contextlib import contextmanager

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
INTERNAL_SSL_CA_CERT_FILENAME = 'cloudify_internal_ca_cert.pem'
INTERNAL_SSL_CA_KEY_FILENAME = 'cloudify_internal_ca_key.pem'
INTERNAL_PKCS12_FILENAME = 'cloudify_internal.p12'
EXTERNAL_SSL_CERT_FILENAME = 'cloudify_external_cert.pem'
EXTERNAL_SSL_KEY_FILENAME = 'cloudify_external_key.pem'

INTERNAL_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                  INTERNAL_SSL_CERT_FILENAME)
INTERNAL_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                 INTERNAL_SSL_KEY_FILENAME)
INTERNAL_CA_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                     INTERNAL_SSL_CA_CERT_FILENAME)
INTERNAL_CA_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                    INTERNAL_SSL_CA_KEY_FILENAME)
EXTERNAL_CERT_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                  EXTERNAL_SSL_CERT_FILENAME)
EXTERNAL_KEY_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                 EXTERNAL_SSL_KEY_FILENAME)
CERT_METADATA_FILE_PATH = os.path.join(SSL_CERTS_TARGET_DIR,
                                       'certificate_metadata')


BASE_LOG_DIR = '/var/log/cloudify'


NGINX_SERVICE_NAME = 'nginx'
DEFAULT_BUFFER_SIZE = 8192
SINGLE_TAR_PREFIX = 'cloudify-manager-resources'

CLOUDIFY_USER = 'cfyuser'
CLOUDIFY_GROUP = 'cfyuser'
CLOUDIFY_HOME_DIR = '/etc/cloudify'
SUDOERS_INCLUDE_DIR = '/etc/sudoers.d'
CLOUDIFY_SUDOERS_FILE = os.path.join(SUDOERS_INCLUDE_DIR, CLOUDIFY_USER)

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


def generate_ca_cert():
    sudo([
        'openssl', 'req',
        '-x509',
        '-nodes',
        '-newkey', 'rsa:2048',
        '-days', '3650',
        '-batch',
        '-out', INTERNAL_CA_CERT_PATH,
        '-keyout', INTERNAL_CA_KEY_PATH
    ])
    # PKCS12 file required for riemann due to JVM
    # While we don't really want the private key in there, not having it
    # causes failures
    # The password is also a bit pointless here since it's in the same place
    # as a readable copy of the certificate and if this path can be written to
    # maliciously then all is lost already.
    pkcs12_path = os.path.join(SSL_CERTS_TARGET_DIR, INTERNAL_PKCS12_FILENAME)
    sudo([
        'openssl', 'pkcs12', '-export',
        '-out', pkcs12_path,
        '-in', INTERNAL_CA_CERT_PATH,
        '-inkey', INTERNAL_CA_KEY_PATH,
        '-password', 'pass:cloudify',
    ])


def _format_ips(ips):
    altnames = set(ips)

    # Ensure we trust localhost
    altnames.add('127.0.0.1')
    altnames.add('localhost')

    subject_altdns = [
        'DNS:{name}'.format(name=name)
        for name in altnames
    ]
    subject_altips = []
    for name in altnames:
        ip_address = False
        try:
            socket.inet_pton(socket.AF_INET, name)
            ip_address = True
        except socket.error:
            # Not IPv4
            pass
        try:
            socket.inet_pton(socket.AF_INET6, name)
            ip_address = True
        except socket.error:
            # Not IPv6
            pass
        if ip_address:
            subject_altips.append('IP:{name}'.format(name=name))

    cert_metadata = ','.join([
        ','.join(subject_altdns),
        ','.join(subject_altips),
    ])
    return cert_metadata


def store_cert_metadata(internal_rest_host, networks=None,
                        filename=CERT_METADATA_FILE_PATH):
    metadata = load_cert_metadata()
    metadata['internal_rest_host'] = internal_rest_host
    if networks is not None:
        metadata['networks'] = networks
    contents = json.dumps(metadata)
    sudo_write_to_file(contents, filename)
    chown(CLOUDIFY_USER, CLOUDIFY_GROUP, filename)


def load_cert_metadata(filename=CERT_METADATA_FILE_PATH):
    try:
        with open(filename) as f:
            return json.load(f)
    except IOError:
        return {}


CSR_CONFIG_TEMPLATE = """
[req]
distinguished_name = req_distinguished_name
req_extensions = server_req_extensions
[ server_req_extensions ]
subjectAltName={metadata}
[ req_distinguished_name ]
commonName = _common_name # ignored, _default is used instead
commonName_default = {cn}
"""


@contextmanager
def _csr_config(cn, metadata):
    """Prepare a config file for creating a ssl CSR.

    :param cn: the subject commonName
    :param metadata: string to use as the subjectAltName, should be formatted
                     like "IP:1.2.3.4,DNS:www.com"
    """
    with tempfile.NamedTemporaryFile(delete=False) as conf_file:
        conf_file.write(CSR_CONFIG_TEMPLATE.format(cn=cn, metadata=metadata))

    try:
        yield conf_file.name
    finally:
        remove(conf_file.name)


def _generate_ssl_certificate(ips,
                              cn,
                              cert_path,
                              key_path,
                              sign_cert=INTERNAL_CA_CERT_PATH,
                              sign_key=INTERNAL_CA_KEY_PATH):
    """Generate a public SSL certificate and a private SSL key

    :param ips: the ips (or names) to be used for subjectAltNames
    :type ips: List[str]
    :param cn: the subject commonName for the new certificate
    :type cn: str
    :param cert_path: path to save the new certificate to
    :type cert_path: str
    :param key_path: path to save the key for the new certificate to
    :type key_path: str
    :param sign_cert: path to the signing cert (internal CA by default)
    :type sign_cert: str
    :param sign_key: path to the signing cert's key (internal CA by default)
    :type sign_key: str
    :return: The path to the cert and key files on the manager
    """
    # Remove duplicates from ips
    cert_metadata = _format_ips(ips)
    ctx.logger.debug('Using certificate metadata: {0}'.format(cert_metadata))

    csr_path = '{0}.csr'.format(cert_path)

    with _csr_config(cn, cert_metadata) as conf_path:
        sudo([
            'openssl', 'req',
            '-newkey', 'rsa:2048',
            '-nodes',
            '-batch',
            '-config', conf_path,
            '-out', csr_path,
            '-keyout', key_path,
        ])
        x509_command = [
            'openssl', 'x509',
            '-days', '3650',
            '-req', '-in', csr_path,
            '-extfile', conf_path,
            '-out', cert_path,
            '-extensions', 'server_req_extensions',
        ]
        if sign_cert and sign_key:
            x509_command += [
                '-CA', sign_cert,
                '-CAkey', sign_key,
                '-CAcreateserial'
            ]
        else:
            x509_command += [
                '-signkey', key_path
            ]
        sudo(x509_command)
        remove(csr_path)

    ctx.logger.info('Generated SSL certificate: {0} and key: {1}'.format(
        cert_path, key_path
    ))
    return cert_path, key_path


def generate_internal_ssl_cert(ips, name):
    return _generate_ssl_certificate(
        ips,
        name,
        INTERNAL_CERT_PATH,
        INTERNAL_KEY_PATH
    )


def deploy_or_generate_external_ssl_cert(ips, cn, cert_source, key_source):
    try:
        # Try to deploy user provided certificates
        deploy_blueprint_resource(cert_source,
                                  EXTERNAL_CERT_PATH,
                                  NGINX_SERVICE_NAME,
                                  user_resource=True,
                                  load_ctx=False)
        deploy_blueprint_resource(key_source,
                                  EXTERNAL_KEY_PATH,
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
        return EXTERNAL_CERT_PATH, EXTERNAL_KEY_PATH
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
                EXTERNAL_CERT_PATH,
                EXTERNAL_KEY_PATH,
                sign_cert=None,
                sign_key=None

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


class BlueprintResourceFactory(object):

    BASE_RESOURCES_PATH = '/opt/cloudify'
    RESOURCES_DIR_NAME = 'resources'

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

        # The local path is decided according to whether we are in upgrade
        local_resource_path = self._get_local_file_path(service_name,
                                                        resource_name)

        if not os.path.isfile(local_resource_path):
            mkdir(os.path.dirname(local_resource_path))
            if user_resource:
                self._download_user_resource(source,
                                             local_resource_path,
                                             render=render,
                                             load_ctx=load_ctx)
            elif source_resource:
                self._download_source_resource(source,
                                               local_resource_path)
            elif render:
                self._download_resource_and_render(source,
                                                   local_resource_path,
                                                   load_ctx)
            else:
                self._download_resource(source, local_resource_path)
        return local_resource_path, destination

    @staticmethod
    def local_resource_exists(filename):
        try:
            get_filepath_from_pkg_name(filename, raise_if_not_found=True)
            return True
        except IOError:
            return False

    def _download_user_resource(self, source, dest,
                                render=True, load_ctx=True):
        if not os.path.isfile(dest):
            if render:
                self._download_resource_and_render(source, dest, load_ctx)
            else:
                self._download_resource(source, dest)

    @staticmethod
    def _download_resource(source, dest):
        resource_name = os.path.basename(dest)
        ctx.logger.info('Downloading resource {0} to {1}'.format(
            resource_name, dest))
        tmp_file = ctx.download_resource(source)
        move(tmp_file, dest)

    def _download_resource_and_render(self, source, dest, load_ctx):
        resource_name = os.path.basename(dest)
        ctx.logger.debug('Downloading resource {0} to {1}'.format(
            resource_name, dest))
        if load_ctx:
            params = self._get_node_props()
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
    def _get_node_props():
        node_props = ctx.node.properties.get_all()
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

    def get_resources_dir(self, service_name):
        return os.path.join(self.BASE_RESOURCES_PATH,
                            service_name,
                            self.RESOURCES_DIR_NAME)


resource_factory = BlueprintResourceFactory()


def start_service(service_name, append_prefix=True):
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


def get_auth_headers(username, password):
    return {
        'Authorization': 'Basic ' + base64.b64encode('{0}:{1}'.format(
            username, password)
        ),
        'tenant': 'default_tenant'
    }


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
