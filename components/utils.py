#!/usr/bin/env python

import os

import time
import subprocess as sub
import sys
import urllib
import tempfile
import socket

from cloudify import ctx

PROCESS_POLLING_INTERVAL = 0.1
CLOUDIFY_SOURCES_PATH = '/opt/cloudify/sources'

debug = ctx.node.properties.get('debug')


def deploy_blueprint_resource(source, destination):
    ctx.logger.info('Deploying {0} to {1}'.format(source, destination))
    tmp_file = ctx.download_resource_and_render(source)
    move(tmp_file, destination)


def run(command, retries=0):
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
        ctx.logger.info('Failed running command: {0}. Retrying. '
                        '({1} left)'.format(command, retries))
        run(command, retries - 1)
    return proc


def sudo(command):
    if isinstance(command, str):
        command = command.split(command)
    command.insert(0, 'sudo')
    run(command)


def error_exit(message):
    ctx.logger.info(message)
    sys.exit(1)


def create_dir(dir):
    if os.path.isdir(dir):
        return
    ctx.logger.info('Creating Directory: {0}'.format(dir))
    sudo(['mkdir', '-p', dir])


def install_python_package(source, venv=None):
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


def download_file(url, destination=None):
    if not destination:
        fd, destination = tempfile.mkstemp()
        os.remove(destination)
        os.close(fd)

    if not os.path.isfile(destination):
        ctx.logger.info('Downloading {0} to {1}...'.format(url, destination))
        curl_download_with_retries(url, destination)
    else:
        ctx.logger.info('File {0} already exists...'.format(destination))
    return destination

    ctx.logger.info('Downloading {0} to {1}...'.format(url, destination))
    final_url = urllib.urlopen(url).geturl()
    if final_url != url:
        ctx.logger.info('Redirected to {0}'.format(final_url))
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
    ctx.logger.info('Downloading {0}...'.format(url))
    if os.path.isfile(destf):
        ctx.logger.info('Resource already exists ({0}). Skipping...'.format(
            destf))
    else:
        tmp_path = download_file(url)
        ctx.logger.info('Saving {0} under {1}'.format(tmp_path, destf))
        create_dir(CLOUDIFY_SOURCES_PATH)
        sudo(['mv', tmp_path, destf])
    return destf


def copy_notice(service):
    destn = os.path.join('/', 'opt', service + '_NOTICE.txt')
    if os.path.isfile(destn):
        ctx.logger.info('NOTICE {0} already exists. Skipping...'.format(destn))
    else:
        source = 'components/{0}/NOTICE.txt'.format(service)
        ctx.logger.info('Copying {0} notice file to {1}...'.format(
            service, destn))
        notice_file = ctx.download_resource(source)
        sudo(['mv', notice_file, destn])


def wait_for_port(port, host='localhost'):
    counter = 1

    ctx.logger.info('Waiting for {0}:{1} to become available...'.format(
        host, port))

    for tries in xrange(24):
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
        ctx.logger.info('Checking whether .rpm {0} exists...'.format(
            archive_path))
        if not os.path.isfile(archive_path):
            tmp_path = download_file(source)
            create_dir(CLOUDIFY_SOURCES_PATH)
            ctx.logger.info('Saving {0} under {1}...'.format(
                filename, CLOUDIFY_SOURCES_PATH))
            sudo(['mv', tmp_path, archive_path])
        source_name = run(['rpm', '-qp', archive_path]).aggr_stdout

    ctx.logger.info('Checking whether {0} is already installed...'.format(
        archive_path))
    if run(['rpm', '-q', source_name]).returncode == 0:
        ctx.logger.info('Package {0} is already installed.'.format(source))
        return

    ctx.logger.info('yum installing {0}...'.format(archive_path))
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

        ctx.logger.info('Deploying systemd EnvironmentFile...')
        deploy_blueprint_resource(env_src, env_dst)
        ctx.logger.info('Deploying systemd .service file...')
        deploy_blueprint_resource(srv_src, srv_dst)

        ctx.logger.info('Enabling systemd .service...')
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


systemd = SystemD()


def move(source, destination):
    sudo(['mv', source, destination])


def replace_in_file(this, with_this, in_here):
    """Replaces all occurences of the regex in all matches
    from a file with a specific value.
    """
    ctx.logger.info('Replacing {0} with {1} in {2}...'.format(
        this, with_this, in_here))
    # TODO: use re.sub instead
    sudo(['sed', '-i', "s|{0}|{1}|g".format(this, with_this), in_here])


def get_selinux_state():
    return sub.check_output('getenforce')


def set_selinux_permissive():
    """This sets SELinux to permissive mode both for the current session
    and systemwide.
    """
    ctx.logger.info('Checking whether SELinux in enforced...')
    if get_selinux_state() == 'Enforcing':
        ctx.logger.info('SELinux is enforcing, setting permissive state...')
        sudo(['setenforce', 'permissive'])
        replace_in_file(
            'SELINUX=enforcing', 'SELINUX=permissive', '/etc/selinux/config')
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
    rabbitmq_endpoint_ip = ctx.node.properties('rabbitmq_endpoint_ip')
    if not rabbitmq_endpoint_ip:
        rabbitmq_endpoint_ip = ctx.instance.host_ip
    return rabbitmq_endpoint_ip


def create_service_user(user, home):
    """Creates a user.
    It will not create the home dir for it
    and assume that it already exists.
    This user will only be created if it didn't already exist.
    """
    ctx.logger.info('Checking whether {0} exists...'.format(user))
    user_exists = run('getend passwd {0}'.format(user)).returncode
    if user_exists:
        ctx.logger.info('User {0} already exists...'.format(user))
    else:
        ctx.logger.info('Creating user {0}, home: {2}...'.format(user, home))
        sudo(['useradd', '--shell', '/sbin/nologin', '--home-dir',
              "{0}".format(home), '--no-create-home', '--system',
              '"{0}"'.format(user)])


def deploy_logrotate_config(service):
    ctx.logger.info('Deploying logrotate config...')
    config_file_source = 'components/{0}/config/logrotate'.format(service)
    config_file_destination = '/etc/logrotate.d/{0}'.format(service)
    deploy_blueprint_resource(config_file_source, config_file_destination)
    sudo(['chmod', '644', config_file_destination])


def chown(user, group, path):
    ctx.logger.info('chowning {0} by {1}:{2}...'.format(path, user, group))
    sudo(['chown', '-R', '{0}:{1}'.format(user, group), path])


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
    #         sudo mv ${log} /var/log/cloudify/${service}/${log##/var/log/${service}/}-from_bootstrap-$(date +%Y-%m-%eT%T%z)
    #     done
    #     # Remove the directory if it's empty, ignoring failures due to lack of directory
    #     # This won't remove /var/log if ${service} is empty, unless /var/log is empty.
    #     # It will, however, error if its target dir is non-empty

    #     ctx logger info "Removing unnecessary logs directory: /var/log/${service}"
    #     sudo rm -df /var/log/${service}
    # }

# function run_command_with_retries() {
#     # Logging should be improved with consideration given to possible command injection accidents or attacks
#     ctx logger info "Attempting to run ${1} with up to 5 retries"
#     max_retries=5
#     retried=0
#     while ! ${*}; do
#         # Better logging would be good
#         ctx logger info "Command ${1} failed, retrying in 1 second."
#         retried=$(( ${retried} + 1 ))
#         sleep 1
#         if [[ ${retried} -eq ${max_retries} ]]; then
#             # Better logging would be good
#             ctx logger info "Max retries for command ${1} exceeded, aborting."
#             break
#         fi
#     done
# }

# function run_noglob_command_with_retries() {
#     # Logging should be improved with consideration given to possible command injection accidents or attacks
#     ctx logger info "Attempting to run ${1} with up to 5 retries"
#     max_retries=5
#     retried=0
#     while ! sh -c -f "${*}"; do
#         # Better logging would be good
#         ctx logger info "Command ${1} failed, retrying in 1 second."
#         retried=$(( ${retried} + 1 ))
#         sleep 1
#         if [[ ${retried} -eq ${max_retries} ]]; then
#             # Better logging would be good
#             ctx logger info "Max retries for command ${1} exceeded, aborting."
#             break
#         fi
#     done
# }

# function extract_github_archive_to_tmp () {
#     repo=${1}
#     if [[ "$(file ${repo})" =~ 'Zip archive data' ]]; then
#         # This is a zip, unzip it, assuming it is a github style zip
#         unzip ${repo} -d /tmp/github-archive-tmp > /dev/null
#         # Performing a strip-components equivalent, but the github style zips have
#         # an extra leading directory
#         # Using copy+delete to avoid errors when mv finds a target dir exists
#         cp -r /tmp/github-archive-tmp/*/* /tmp
#         rm -rf /tmp/github-archive-tmp
#     else
#         # We are expecting a tar.gz, untar it
#         tar -xzf ${repo} --strip-components=1 -C "/tmp"
#     fi
# }

# function deploy_ssl_certificate () {
#   private_or_public=${1}
#   destination=${2}
#   group=${3}
#   cert=${4}

#   # Root owner, with permissions set below, allow anyone to read a public cert, and allow the owner to read a private cert, but not change it, mitigating risk in the event of the associated service being vulnerable.
#   ownership=root.${group}

#   if [[ ${private_or_public} == "private" ]]; then
#     # This check should probably be done using an openssl command
#     if [[ "${cert}" =~ "BEGIN RSA PRIVATE KEY" ]]; then
#       # Owner read, Group read, Others no access
#       permissions=440
#     else
#       error_exit "Private certificate is expected to begin with a line containing 'BEGIN RSA PRIVATE KEY'."
#     fi
#   elif [[ ${private_or_public} == "public" ]]; then
#     # This check should probably be done using an openssl command
#     if [[ "${cert}" =~ "BEGIN CERTIFICATE" ]]; then
#       # Owner read, Group read, Others read
#       permissions=444
#     else
#       # This should probably be done using an openssl command
#       error_exit "Public certificate is expected to begin with a line containing 'BEGIN CERTIFICATE'."
#     fi
#   else
#     error_exit "Certificates may only be 'private' or 'public', not '${private_or_public}'"
#   fi

#   ctx logger info "Deploying ${private_or_public} SSL certificate in ${destination} for group ${group}"
#   echo "${cert}" | sudo tee ${destination} >/dev/null

#   ctx logger info "Setting permissions (${permissions}) and ownership (${ownership}) of SSL certificate at ${ddestination}"
#   # Set permissions first as the tee with sudo should mean its owner and group are root, leaving a negligible window for it to be accessed by an unauthorised user
#   sudo chmod ${permissions} ${destination}
#   sudo chown ${ownership} ${destination}
# }

# CLOUDIFY_SOURCES_PATH="/opt/cloudify/sources"
