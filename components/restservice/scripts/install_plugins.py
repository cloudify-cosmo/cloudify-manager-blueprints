import tarfile
import tempfile
import os
from StringIO import StringIO
import json

import fabric
import fabric.api
from fabric.contrib.files import exists as remote_file_exists
import jinja2

from cloudify import ctx


def install_plugins():

    install_plugins_script = 'install_plugins.sh'
    ctx.logger.info('Installing plugins')

    # Getting all the required plugins
    plugins = _get_plugins_ctx_properties()

    # Shame to do all the work for nothing
    if plugins:

        # create location to place tar-gzipped plugins in
        cloudify_plugins = 'cloudify/plugins'
        _run_command('mkdir -p ~/{0}'.format(cloudify_plugins))

        # for each plugin that is included in the blueprint, tar-gzip it
        # and place it in the plugins dir on the host
        for plugin in plugins.values():
            source = plugin['source']
            if source.split('://')[0] in ['http', 'https']:
                continue

            name = os.path.basename(source)
            tar_remote_path = '{0}/{1}.tar.gz' \
                .format(cloudify_plugins, name)
            plugin['source'] = 'file://$HOME/{0}'.format(tar_remote_path)
            if remote_file_exists(tar_remote_path):
                continue

            # temporary workaround to resolve absolute file path
            # to installed plugin using internal local workflows storage
            # information
            plugin_path = os.path.join(ctx._endpoint.storage.resources_root,
                                       source)
            with tempfile.TemporaryFile() as fileobj:
                with tarfile.open(fileobj=fileobj, mode='w:gz') as tar:
                    tar.add(plugin_path, arcname=name)
                fileobj.seek(0)
                fabric.api.put(fileobj, '~/{0}'.format(tar_remote_path))

        # render script template and copy it to host's home dir
        script_template = ctx.get_resource('components/restservice/'
                                           'scripts/install_plugins.sh')
        script = jinja2.Template(script_template).render(plugins=plugins)
        fabric.api.put(local_path=StringIO(script),
                       remote_path='~/cloudify/{0}'
                       .format(install_plugins_script))

        # Execute the rendered script
        _run_command('chmod +x ~/cloudify/{0} && ~/cloudify/{0}'
                     .format(install_plugins_script))


def _read_remote_file(remote_file_path):
    if remote_file_exists(remote_file_path, use_sudo=True):
        fd = StringIO()
        fabric.api.get(remote_file_path, fd)
        return json.loads(fd.getvalue())
    return None


def _get_plugins_ctx_properties():
    if _is_upgrade():
        if ctx.node.properties.get('use_existing_on_upgrade'):
            props_path = '/opt/cloudify/node_properties/' \
                         'cloudify-restservice/properties.json'
            remote_props = _read_remote_file(props_path)
            ctx.logger.info('using existing properties from remote path {0}'
                            .format(props_path))
            return remote_props.get('plugins', {})

    return ctx.node.properties.get('plugins', {})


def _is_upgrade():
    remote_status_file_path = '/opt/manager/status.txt'
    mngr_status = _read_remote_file(remote_status_file_path)
    if mngr_status:
        ctx.logger.info('loading upgrade status file: {0}'
                        .format(remote_status_file_path))
        return mngr_status['status'] == 'activated'
    return False


def _run_command(command, shell_escape=None, pty=True):
    return fabric.api.run(command, shell_escape=shell_escape, pty=pty)
