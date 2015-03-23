import StringIO

import fabric.api
import fabric.context_managers

import cloudify


_HOST_POOL_REPOSITORY_LINK = 'https://codeload.github.com/cloudify-cosmo/cloudify-host-pool-service/zip/master'


def create(directory):
    _ensure_dependancies_installed()
    fabric.api.run(
        ' && '.join(['mkdir {0}'.format(directory),
                     'cd {0}'.format(directory),
                     'virtualenv .',
                     '. bin/activate',
                     'pip install {0}'.format(_HOST_POOL_REPOSITORY_LINK),
                     'pip install gunicorn']))


def configure(directory, environment = None):
    env = environment or {}
    config_filename = env.get('HOST_POOL_CONFIG', 'host-pool.yaml')
    pool_config = cloudify.ctx.get_resource(
        'resources/{0}'.format(config_filename))
    with fabric.context_managers.cd(directory):
        f = StringIO.StringIO(pool_config)
        f.name = config_filename
        fabric.api.put(f, config_filename)


def _ensure_dependancies_installed():
    if not _is_installed('python-dev', _DPKG):
        _install_with_apt_get('python-dev')
    if not _is_installed('pip', _WHICH):
        _install_with_apt_get('python-pip')
        fabric.api.sudo('pip install --upgrade pip')
    if not _is_installed('virtualenv', _WHICH):
        fabric.api.sudo('pip install virtualenv')


_DPKG = 1
_WHICH = 2


def _is_installed(what, check_method):
    if check_method == _DPKG:
        result = fabric.api.run(
            'dpkg-query --status {0} 1>/dev/null 2>&1'.format(what),
            quiet=True)
    elif check_method == _WHICH:
        result = fabric.api.run(
            'which {0} 1>/dev/null 2>&1'.format(what),
            quiet=True)
    else:
        raise Exception('bad parameter')
    return result.succeeded


_updated = False


def _install_with_apt_get(what):
    global _updated
    if not _updated:
        fabric.api.sudo('apt-get update')
        _updated = True
    fabric.api.sudo('apt-get --yes install {0}'.format(what))


def _sftp_resource_copy(resource_path, remote_target_path):
    contents = cloudify.ctx.get_resource(resource_path)
    f = StringIO.StringIO(contents)
    f.name = resource_path
    fabric.api.put(f, remote_target_path)
