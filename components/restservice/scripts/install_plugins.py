import tarfile
import tempfile
import os

import jinja2

from cloudify import ctx


def install_plugins(client):

    install_plugins_script = 'install_plugins.sh'
    ctx.logger.info('Installing plugins')

    # Getting all the required plugins
    plugins = ctx.source.node.properties.get('plugins', {})

    # Shame to do all the work for nothing
    if plugins:
        sftp = client.open_sftp()
        # create location to place tar-gzipped plugins in
        cloudify_plugins = 'cloudify/plugins'
        client.exec_command('mkdir -p ~/{0}'.format(cloudify_plugins))

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
                tar_remote_path = '{0}/{1}.tar.gz' \
                    .format(cloudify_plugins, name)
                sftp.putfo(fileobj, '~/{0}'.format(tar_remote_path))
                plugin['source'] = 'file://$HOME/{0}'.format(tar_remote_path)

        # render script template and copy it to host's home dir
        script_template = ctx.get_resource('components/restservice/'
                                           'scripts/install_plugins.sh')
        script = jinja2.Template(script_template).render(plugins=plugins)
        script_path = '~/cloudify/{0}'.format(install_plugins_script)
        with sftp.open(script_path, 'w') as f:
            f.write(script)

        # Execute the rendered script
        client.exec_command('chmod +x ~/cloudify/{0} && ~/cloudify/{0}'
                            .format(install_plugins_script))
        sftp.close()
