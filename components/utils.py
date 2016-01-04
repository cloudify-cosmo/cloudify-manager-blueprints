#!/usr/bin/env python

import json
import os
from threading import Thread
import time
import subprocess as sub
import sys
import urllib
import tempfile
import socket
import stat
import subprocess


PROCESS_POLLING_INTERVAL = 0.1
CLOUDIFY_SOURCES_PATH = '/opt/cloudify/sources'


class CtxLogger(object):
    def _logger(self, message, level='info'):
        cmd = ['ctx', 'logger', level, message]
        return sub.check_output(cmd)

    def info(self, message):
        return self._logger(level='info', message=message)

    def warn(self, message):
        return self._logger(level='warn', message=message)

    def error(self, message):
        return self._logger(level='error', message=message)


class CtxNode(object):
    def properties(self, property_name):
        # Retrieved and loaded as JSON to avoid empty False issue
        cmd = ['ctx', '-j', 'node', 'properties', property_name]
        return json.loads(sub.check_output(cmd))


class CtxNodeInstance(object):
    def runtime_properties(self, property_name, value=None):
        cmd = ['ctx', 'instance', 'runtime_properties', property_name]
        if value:
            cmd.append(value)
        return sub.check_output(cmd)

    def host_ip(self):
        cmd = ['ctx', 'instance', 'host_ip']
        return sub.check_output(cmd)


class CtxUtils(object):
    def download_resource_and_render(self, source, destination=None):
        cmd = ['ctx', 'download-resource', source]
        if destination:
            cmd.append(destination)
        return sub.check_output(cmd)

    def deploy_blueprint_resource(self, source, destination):
        logger.info('Deploying {0} to {1}'.format(source, destination))
        tmp_file = self.download_resource_and_render(source)
        sudo(['mv', tmp_file, destination])


def download_resource_and_render(source, destination=None):
    return CtxUtils().download_resource_and_render(source, destination)


def download_resource(source, destination=None):
    return CtxUtils().download_resource_and_render(source, destination)


def deploy_blueprint_resource(source, destination):
    return CtxUtils().deploy_blueprint_resource(source, destination)


logger = CtxLogger()
node = CtxNode()
instance = CtxNodeInstance()


class PipeReader(Thread):
    def __init__(self, fd, proc, logger, log_level):
        Thread.__init__(self)
        self.fd = fd
        self.proc = proc
        self.logger = logger
        self.log_level = log_level
        self.aggr = ''

    def run(self):
        while self.proc.poll() is None:
            output = self.fd.readline()
            if len(output) > 0:
                self.aggr += output
                self.logger.log(self.log_level, output.strip())
            else:
                time.sleep(PROCESS_POLLING_INTERVAL)


def run(command, retries=0, retry_delay=3):
    if isinstance(command, str):
        command = command.split(command)
    stderr = sub.PIPE
    stdout = sub.PIPE
    proc = sub.Popen(command, stdout=stdout, stderr=stderr)
    proc.aggr_stdout, proc.aggr_stderr = proc.communicate()
    # while proc.poll() is None:
    #     time.sleep(PROCESS_POLLING_INTERVAL)
    #     if proc.stdout:
    #         proc.aggr_stdout += proc.stdout.readline()
    #     if proc.stderr:
    #         proc.aggr_stderr += proc.stderr.readline()
    # THIS NEEDS TO BE TESTED
    if proc.returncode != 0 and retries:
        logger.info(
            'Failed running command: {command}. Retrying in {delay}.'
            '({retries} left)'.format(
                command=command,
                delay=retry_delay,
                retries=retries,
            )
        )
        time.sleep(retry_delay)
        run(command, retries - 1, retry_delay)
    return proc


def sudo(command):
    if isinstance(command, str):
        command = command.split(command)
    command.insert(0, 'sudo')
    run(command)


def error_exit(message, returncode=1):
    logger.error(message)
    sys.exit(returncode)


def create_dir(directory):
    if os.path.isdir(directory):
        return
    else:
        logger.info('Creating Directory: {0}'.format(directory))
        sudo(['mkdir', '-p', directory])


def install_python_package(source, venv=None):
    if venv:
        logger.info('Installing {0} in virtualenv {1}...'.format(
            source, venv))
        sudo(['{0}/bin/pip'.format(
            venv), 'install', source, '--upgrade'])
    else:
        logger.info('Installing {0}'.format(source))
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
    logger.info('curling: {0}'.format(' '.join(curl_cmd)))
    run(curl_cmd)


def download_file(url, destination=None):
    if not destination:
        fd, destination = tempfile.mkstemp()
        os.remove(destination)
        os.close(fd)

    if not os.path.isfile(destination):
        logger.info('Downloading {0} to {1}...'.format(url, destination))
        curl_download_with_retries(url, destination)
    else:
        logger.info('File {0} already exists...'.format(destination))
    return destination

    logger.info('Downloading {0} to {1}...'.format(url, destination))
    final_url = urllib.urlopen(url).geturl()
    if final_url != url:
        logger.info('Redirected to {0}'.format(final_url))
    f = urllib.URLopener()
    f.retrieve(final_url, destination)
    return destination


def get_file_name_from_url(url):
    try:
        return url.split('/')[-1]
    except:
        from urlparse import urlparse

        url = "http://github.com/x.y"
        disassembled = urlparse(url)
        return os.pathself.basename(disassembled.path)


def download_cloudify_resource(url):
    destf = os.path.join(CLOUDIFY_SOURCES_PATH, get_file_name_from_url(url))
    logger.info('Downloading {0}...'.format(url))
    if os.path.isfile(destf):
        logger.info('Resource already exists ({0}). Skipping...'.format(destf))
    else:
        tmp_path = download_file(url)
        logger.info('Saving {0} under {1}'.format(tmp_path, destf))
        create_dir(CLOUDIFY_SOURCES_PATH)
        sudo(['mv', tmp_path, destf])
    return destf


def copy_notice(service):
    destn = os.path.join('/', 'opt', service + '_NOTICE.txt')
    if os.path.isfile(destn):
        logger.info('NOTICE {0} already exists. Skipping...'.format(destn))
    else:
        source = 'components/{0}/NOTICE.txt'.format(service)
        logger.info('Copying {0} notice file to {1}...'.format(service, destn))
        notice_file = download_resource(source)
        sudo(['mv', notice_file, destn])


def wait_for_port(port, host='localhost'):
    counter = 1

    logger.info('Waiting for {0}:{1} to become available...'.format(
        host, port))

    for tries in xrange(24):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        if not result == 0:
            logger.info('{0}:{1} is not available yet, '
                        'retrying... ({2}/24)'.format(host, port, counter))
            time.sleep(2)
            continue
        logger.info('{0}:{1} is open!'.format(host, port))
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
    installed.
    If it is, it will do nothing. It not, it will install it.
    If the source is a url to an rpm and the file doesn't already exist
    in a predesignated archives file path (${CLOUDIFY_SOURCES_PATH}/),
    it will download it. It will then use that file to check if the
    package is already installed.
    If it is, it will do nothing. It not, it will install it.
    NOTE: This will currently not take into considerations situations
    in which a file was downloaded partially. If a file is partially
    downloaded, a redownload will not take place and rather an
    installation will be attempted, which will obviously fail since
    the rpm file is incomplete.
    ALSO NOTE: you cannot run yum_install and provide it with a space
    separated array of packages as you can with yum install. You must
    provide one package per invocation.
    """
    if source.startswith(('http', 'https', 'ftp')):
        filename = get_file_name_from_url(source)
    source_name, ext = os.path.splitext(filename)
    archive_path = source_name

    if ext.endswith('rpm'):
        archive_path = os.path.join(CLOUDIFY_SOURCES_PATH, filename)
        logger.info('Checking whether .rpm {0} exists...'.format(archive_path))
        if not os.path.isfile(archive_path):
            tmp_path = download_file(source)
            create_dir(CLOUDIFY_SOURCES_PATH)
            logger.info('Saving {0} under {1}...'.format(
                filename, CLOUDIFY_SOURCES_PATH))
            sudo(['mv', tmp_path, archive_path])
        source_name = run(['rpm', '-qp', archive_path]).aggr_stdout

    logger.info('Checking whether {0} is already installed...'.format(
        archive_path))
    if run(['rpm', '-q', source_name]).returncode == 0:
        logger.info('Package {0} is already installed.'.format(source))
        return

    logger.info('yum installing {0}...'.format(archive_path))
    sudo(['yum', 'install', '-y', archive_path])


class SystemD(object):
    @staticmethod
    def configure(service_name):
        """This configure systemd for a specific service.
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

        logger.info('Deploying systemd EnvironmentFile...')
        deploy_blueprint_resource(env_src, env_dst)
        logger.info('Deploying systemd .service file...')
        deploy_blueprint_resource(srv_src, srv_dst)

        logger.info('Enabling systemd .service...')
        sudo(['systemctl', 'enable', '{0}.service'.format(sid)])
        sudo(['systemctl', 'daemon-reload'])

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

    @staticmethod
    def enable(service_name):
        sudo(['systemctl', 'enable', service_name])

    @staticmethod
    def start(service_name):
        sudo(['systemctl', 'start', service_name])

    @staticmethod
    def stop(service_name):
        sudo(['systemctl', 'stop', service_name])

    @staticmethod
    def daemon_reload():
        """
            This will reload all systemd service configurations when you have
            changed them on disk.
        """
        sudo(['systemctl', 'daemon-reload'])


systemd = SystemD()


def move(source, destination):
    sudo(['mv', source, destination])


def set_permissions_owner_execute_only(path):
    os.chmod(
        path,
        # Set read and execute for owner
        stat.S_IRUSR | stat.S_IXUSR,
    )


def replace_in_file(this, with_this, in_here):
    """Replaces all occurences of the regex in all matches
    from a file with a specific value.
    """
    logger.info('Replacing {0} with {1} in {2}...'.format(
        this, with_this, in_here))
    # TODO: use re.sub instead
    sudo(['sed', '-i', "s|{0}|{1}|g".format(this, with_this), in_here])


def get_selinux_state():
    return sub.check_output('getenforce')


def set_selinux_permissive():
    """This sets SELinux to permissive mode both for the current session
    and systemwide.
    """
    logger.info('Checking whether SELinux in enforced...')
    if get_selinux_state() == 'Enforcing':
        logger.info('SELinux is enforcing, setting permissive state...')
        sudo(['setenforce', 'permissive'])
        replace_in_file(
            'SELINUX=enforcing', 'SELINUX=permissive', '/etc/selinux/config')
    else:
        logger.info('SELinux is not enforced.')


def set_rabbitmq_policy(name, q_regex, p_type, value):
    logger.info('Setting policy {0} on queues {1} of type {2} to {3}'.format(
        name, q_regex, p_type, value))
    sudo('rabbitmqctl set_policy {0} {1} "{"\"{2}"\":{3}}" '
         '--apply-to-queues'.format(name, q_regex, p_type, value))


def create_service_user(user, home):
    """Creates a user.
    It will not create the home dir for it
    and assume that it already exists.
    This user will only be created if it didn't already exist.
    """
    logger.info('Checking whether {0} exists...'.format(user))
    user_exists = run('getend passwd {0}'.format(user)).returncode
    if user_exists:
        logger.info('User {0} already exists...'.format(user))
    else:
        logger.info('Creating user {0}, home: {2}...'.format(user, home))
        sudo(['useradd', '--shell', '/sbin/nologin', '--home-dir',
              "{0}".format(home), '--no-create-home', '--system',
              '"{0}"'.format(user)])


def deploy_logrotate_config(service):
    logger.info('Deploying logrotate config...')
    config_file_source = 'components/{0}/config/logrotate'.format(service)
    config_file_destination = '/etc/logrotate.d/{0}'.format(service)
    deploy_blueprint_resource(config_file_source, config_file_destination)
    sudo(['chmod', '644', config_file_destination])


def chown(user, group, path):
    logger.info('chowning {0} by {1}:{2}...'.format(path, user, group))
    sudo(['chown', '-R', '{0}:{1}'.format(user, group), path])


def chmod(path, mode, recursive=False):
    logger.info('chmodding {path} to {mode}{recursively}...'.format(
        path=path,
        mode=mode,
        recursively=' recursively' if recursive else '',
    ))

    command = ['chmod']
    if recursive:
        command.append('-R')
    command.append(mode)
    command.append(path)

    sudo(command)


def clean_var_log_dir(service):
    pass

# function clean_var_log_dir() {
#     ###
#     # Cleans up unused /var/log directory for named application.
#     # Directory must be empty or this will fail.
#     ###
#     service=$1

#     for log in $(find /var/log/${service} -type f 2> /dev/null); do
#         # Copy to timestamped file in case this is run again
#         if [ ! -f ${log} ]; then
#             break
#         fi
#         sudo mv ${log} /var/log/cloudify/${service}/${log##/var/log/${service}/}-from_bootstrap-$(date +%Y-%m-%eT%T%z)  # noqa
#     done
#     # Remove the directory if it's empty, ignoring failures due to lack of directory  # noqa
#     # This won't remove /var/log if ${service} is empty, unless /var/log is empty.  # noqa
#     # It will, however, error if its target dir is non-empty

#     ctx logger info "Removing unnecessary logs directory: /var/log/${service}"  # noqa
#     sudo rm -df /var/log/${service}
# }

# function extract_github_archive_to_tmp () {
#     repo=${1}
#     if [[ "$(file ${repo})" =~ 'Zip archive data' ]]; then
#         # This is a zip, unzip it, assuming it is a github style zip
#         unzip ${repo} -d /tmp/github-archive-tmp > /dev/null
#         # Performing a strip-components equivalent, but the github style zips have  # noqa
#         # an extra leading directory
#         # Using copy+delete to avoid errors when mv finds a target dir exists
#         cp -r /tmp/github-archive-tmp/*/* /tmp
#         rm -rf /tmp/github-archive-tmp
#     else
#         # We are expecting a tar.gz, untar it
#         tar -xzf ${repo} --strip-components=1 -C "/tmp"
#     fi
# }


def is_ssl_public_cert(cert):
    validation = subprocess.Popen(
        [
            'openssl',
            'x509',
            '-text',
            '-noout',
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    validation.communicate(input=cert)
    if validation.returncode == 0:
        return True
    else:
        return False


def is_ssl_private_cert(cert):
    validation = subprocess.Popen(
        [
            'openssl',
            'rsa',
            '-text',
            '-noout',
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    validation.communicate(input=cert)
    if validation.returncode == 0:
        return True
    else:
        return False


def deploy_ssl_certificate(destination,
                           cert,
                           group='',
                           private=False):
    # Owner will be set as root, but with appropriate permissions such that
    # the necessary group can read the certificate.
    # This is to mitigate some risk where a service might be compromised such
    # that the certificates can only be changed by the attacker then gaining
    # root.
    owner = 'root'

    error_output = (
        'Certificate to be deployed in {location} is not a valid '
        '{pub_or_priv} certificate. Certificate provided was: {cert}'
    )
    public_or_private = 'private' if private else 'public'

    if private:
        if not is_ssl_private_cert(cert):
            error_exit(error_output.format(
                cert=cert,
                pub_or_priv=public_or_private,
                location=destination,
            ))
        # Private certs should only be readable by root and the appropriate
        # group
        permissions = "440"
    else:
        if not is_ssl_public_cert(cert):
            error_exit(error_output.format(
                cert=cert,
                pub_or_priv=public_or_private,
                location=destination,
            ))
        # Public certs can be safely read by anyone
        permissions = "444"

    logger.info(
        'Deploying {pub_or_priv} SSL certificate in {location} for group '
        '{group}'.format(
            pub_or_priv=public_or_private,
            location=destination,
            group=group,
        ),
    )

    write_to_file(
        data=cert,
        destination=destination,
    )

    logger.info(
        'Setting permissions ({permissions}) and group ({group}) of '
        'SSL certificate at {destination}'.format(
            permissions=permissions,
            group=group or 'root',
            destination=destination,
        )
    )
    # Set permissions first as it should have been written with owner and
    # group are root, leaving a negligible window for it to be accessed by an
    #  unauthorised user
    chmod(
        mode=permissions,
        path=destination,
    )
    chown(
        user=owner,
        group=group,
        path=destination,
    )


def write_to_file(data, destination):
    # This should result in a file owned by root
    writer = subprocess.Popen(
        ['sudo', 'tee', destination],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    writer.communicate(input=data)
