import tarfile
import tempfile
import os
from StringIO import StringIO

import fabric
import fabric.api
import jinja2

from cloudify import ctx


def install_plugins():

    root_dir = os.path.join(ctx._endpoint.storage.resources_root,
                            os.path.dirname(__file__))
    install_plugins_script = 'install_plugins.sh'
    ctx.logger.info('Installing plugins')

    # Getting all the required plugins
    plugins = ctx.node.properties.get('plugins', {})

    # Shame to do all the work for nothing
    if plugins:

        # # Get components utils (for pip install)
        with open(os.path.normpath(
                os.path.join(ctx._endpoint.storage.resources_root,
                             'components/utils'))) as utils:
            utils_content = utils.read()

        # Put utils on the home dir
        fabric.api.put(local_path=StringIO(utils_content),
                       remote_path='~/utils')
        _run_command('sudo chmod +x ~/utils')

        # create location to place tar-gzipped plugins in
        cloudify_plugins = 'cloudify/plugins'
        _run_command('mkdir -p ~/{0}'.format(cloudify_plugins))

        # for each plugin that is included in the blueprint, tar-gzip it
        # and place it in the plugins dir on the host
        for name, plugin in plugins.items():
            source = plugin['source']
            if source.split('://')[0] in ['http', 'https']:
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
                plugin['source'] = \
                    'file://{0}/{1}.tar.gz'.format(cloudify_plugins, name)
                fabric.api.put(local_path=fileobj,
                               remote_path=plugin['source'])

        # render script template and copy it to host's home dir
        with open('{0}/{1}'.format(root_dir, install_plugins_script)) as\
                template_file:
            script_template = template_file.read()
        script = jinja2.Template(script_template).render(plugins=plugins)
        fabric.api.put(local_path=StringIO(script),
                       remote_path='~/{0}'.format(install_plugins_script))

        _run_command('sudo chmod +x ~/{0}'.format(install_plugins_script))

        # Execute the rendered script
        _run_command('~+/{0}'.format(install_plugins_script))


def _run_command(command, shell_escape=None, pty=True):
    return fabric.api.run(command, shell_escape=shell_escape, pty=pty)
