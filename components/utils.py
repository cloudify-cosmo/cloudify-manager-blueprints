#!/usr/bin/env python

import sys
import os
import time
import subprocess
import urllib
import tempfile
import socket
import shlex
import pwd
import glob
from functools import wraps
import re

from cloudify import ctx

PROCESS_POLLING_INTERVAL = 0.1
CLOUDIFY_SOURCES_PATH = '/opt/cloudify/sources'


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


def sudo(command, retries=0, globx=False):
    if isinstance(command, str):
        command = shlex.split(command)
    command.insert(0, 'sudo')
    return run(command=command, globx=globx, retries=retries)


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


def download_cloudify_resource(url):
    """Downloads a resource and saves it as a cloudify resource.

    The resource will be saved under `CLOUDIFY_SOURCES_PATH` and will be
    used in case of operation execution failure after the resource has
    already been downloaded.
    """
    destf = os.path.join(CLOUDIFY_SOURCES_PATH, get_file_name_from_url(url))
    if os.path.isfile(destf):
        ctx.logger.info('Resource already exists ({0}). Skipping...'.format(
            destf))
    else:
        tmp_path = download_file(url)
        ctx.logger.debug('Saving {0} under {1}'.format(tmp_path, destf))
        mkdir(CLOUDIFY_SOURCES_PATH)
        move(tmp_path, destf)
    return destf


def deploy_blueprint_resource(source, destination):
    """Downloads a resource from the blueprint to a destination.

    This expands `download-resource` as a `sudo mv` is required after
    having downloaded the resource.
    """
    ctx.logger.info('Deploying blueprint resource {0} to {1}'.format(
        source, destination))
    tmp_file = ctx.download_resource_and_render(source)
    move(tmp_file, destination)


def copy_notice(service):
    """Deploys a notice file to /opt/SERVICENAME_NOTICE.txt"""
    destn = os.path.join('/opt', service + '_NOTICE.txt')
    if os.path.isfile(destn):
        ctx.logger.info('NOTICE {0} already exists. Skipping...'.format(destn))
    else:
        source = 'components/{0}/NOTICE.txt'.format(service)
        ctx.logger.info('Copying {0} notice file to {1}...'.format(
            service, destn))
        notice_file = ctx.download_resource(source)
        move(notice_file, destn)


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


def yum_install(source):
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
        source_path = os.path.join(CLOUDIFY_SOURCES_PATH, filename)
        ctx.logger.info('Checking whether .rpm {0} exists...'.format(
            source_path))
        if not os.path.isfile(source_path):
            tmp_path = download_file(source)
            mkdir(CLOUDIFY_SOURCES_PATH)
            ctx.logger.info('Saving {0} under {1}...'.format(
                filename, CLOUDIFY_SOURCES_PATH))
            move(tmp_path, source_path)
        source_name = subprocess.check_output(
            ['rpm', '-qp', source_path]).strip()

    ctx.logger.info('Checking whether {0} is already installed...'.format(
        source_path.rstrip('\n\r')))
    installed = run(['rpm', '-q', source_name], ignore_failures=True)
    if installed.returncode == 0:
        ctx.logger.info('Package {0} is already installed.'.format(source))
        return

    ctx.logger.info('yum installing {0}...'.format(source_path))
    sudo(['yum', 'install', '-y', source_path])


class SystemD(object):

    def systemctl(self, action, service='', retries=0):
        systemctl_cmd = ['systemctl', action]
        if service:
            systemctl_cmd.append(service)
        sudo(systemctl_cmd, retries=retries)

    def configure(self, service_name):
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
        deploy_blueprint_resource(env_src, env_dst)
        ctx.logger.info('Deploying systemd .service file...')
        deploy_blueprint_resource(srv_src, srv_dst)

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

    def enable(self, service_name, retries=0):
        ctx.logger.info('Enabling systemd service {0}...'.format(service_name))
        self.systemctl('enable', service_name, retries)

    def start(self, service_name, retries=0):
        ctx.logger.info('Starting systemd service {0}...'.format(service_name))
        self.systemctl('start', service_name, retries)

    def stop(self, service_name, retries=0):
        ctx.logger.info('Stopping systemd service {0}...'.format(service_name))
        self.systemctl('stop', service_name, retries)


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


def set_rabbitmq_policy(name, q_regex, p_type, value):
    ctx.logger.info('Setting policy {0} on queues {1} of type {2} to '
                    '{3}'.format(name, q_regex, p_type, value))
    sudo('rabbitmqctl set_policy {0} {1} "{"\"{2}"\":{3}}" '
         '--apply-to-queues'.format(name, q_regex, p_type, value))


def get_rabbitmq_endpoint_ip():
    """Gets the rabbitmq endpoint IP, using the manager IP if the node
    property is blank.
    """
    try:
        return ctx.node.properties['rabbitmq_endpoint_ip']
    # why?
    except:
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
    ctx.logger.info('Deploying logrotate config...')
    config_file_source = 'components/{0}/config/logrotate'.format(service)
    config_file_destination = '/etc/logrotate.d/{0}'.format(service)
    # if not os.path.exists(config_file_destination):
    #     os.mkdir(config_file_destination)
    deploy_blueprint_resource(config_file_source, config_file_destination)
    # TODO: check if can use os.chmod with elevated privileges
    chmod('644', config_file_destination)


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


def untar(source, destination='/tmp', strip=1):
    # TODO: use tarfile instead
    ctx.logger.debug('Extracting {0} to {1}...'.format(source, destination))
    sudo(['tar', '-xzvf', source, '-C', destination,
          '--strip={0}'.format(strip)])
